"""One climate entity per zone.

The wall thermostat has a knob that adds an offset to the base setpoint:
    effective = base + offset
The entity shows and sets the EFFECTIVE setpoint: when you ask for T it
writes base = T - offset, so the plant really aims at T.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AerLinkConfigEntry
from .const import (
    COIL_ZONE_ON,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    FAN_CODES,
    FAN_MODES_TO_CODE,
    REG_BASE_SP,
    REG_EFFECTIVE_SP,
    REG_FAN_COMMAND,
    SETTLE_SECONDS,
)
from .entity import AerLinkZoneEntity
from .modbus import AerLinkError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: AerLinkConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data
    tmin = entry.options.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
    tmax = entry.options.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
    async_add_entities(
        AerLinkClimate(data.coordinator, entry.entry_id, i, zone, tmin, tmax)
        for i, zone in enumerate(data.zones)
    )


class AerLinkClimate(AerLinkZoneEntity, ClimateEntity):
    _attr_name = None
    _attr_translation_key = "zone"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_precision = 0.1
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.OFF]
    _attr_fan_modes = list(FAN_CODES.values())
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator, entry_id: str, idx: int, zone: str, tmin: float, tmax: float) -> None:
        super().__init__(coordinator, entry_id, idx, zone, "climate")
        self._attr_min_temp, self._attr_max_temp = tmin, tmax
        self._offset: int | None = None  # knob offset, tenths of °C
        self._wrote_at = 0.0
        self._wrote_base: int | None = None
        self._fan_cmd: tuple[float, str] | None = None

    @property
    def _client(self):
        return self.coordinator.client

    def _settling(self) -> bool:
        return time.monotonic() - self._wrote_at < SETTLE_SECONDS

    @property
    def current_temperature(self) -> float | None:
        v = self._v("temp")
        return None if v is None else v / 10

    @property
    def target_temperature(self) -> float | None:
        if self._settling() and self._wrote_base is not None and self._offset is not None:
            return (self._wrote_base + self._offset) / 10
        v = self._v("eff")
        return None if v is None else v / 10

    @property
    def hvac_mode(self) -> HVACMode | None:
        on = self._v("on")
        if on is None:
            return None
        return HVACMode.AUTO if on else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if self._v("on") is False:
            return HVACAction.OFF
        demand = self._v("demand")
        if demand is None:
            return None
        return HVACAction.HEATING if demand else HVACAction.IDLE

    @property
    def fan_mode(self) -> str | None:
        # A fan command takes ~15-20 s to show up: show the requested mode meanwhile.
        if self._fan_cmd and time.monotonic() - self._fan_cmd[0] < SETTLE_SECONDS:
            if FAN_CODES.get(self._v("fan_state")) != self._fan_cmd[1]:
                return self._fan_cmd[1]
        return FAN_CODES.get(self._v("fan_state"))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        base, eff = self._v("base"), self._v("eff")
        if base is None or eff is None:
            return None
        return {
            "base_setpoint": base / 10,
            "knob_offset": round((eff - base) / 10, 1),
            "fan_code": self._v("fan_state"),
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        target = kwargs.get(ATTR_TEMPERATURE)
        if target is None:
            return
        try:
            if self._settling() and self._offset is not None:
                offset = self._offset
            else:
                # Read the knob offset now, to follow the current knob position.
                base = (await self._client.read_holding(REG_BASE_SP + self._i, 1))[0]
                eff = (await self._client.read_holding(REG_EFFECTIVE_SP + self._i, 1))[0]
                offset = eff - base
            new_base = max(50, min(350, round(target * 10) - offset))
            await self._client.write_register(REG_BASE_SP + self._i, new_base)
        except AerLinkError as err:
            raise HomeAssistantError(f"AerLink: {err}") from err
        _LOGGER.debug("%s: target %.1f °C (offset %+.1f) -> base %.1f",
                      self.device_entry and self.device_entry.name, target, offset / 10, new_base / 10)
        self._offset, self._wrote_base, self._wrote_at = offset, new_base, time.monotonic()
        if self.coordinator.data:
            self.coordinator.data["base"][self._i] = new_base
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        code = FAN_MODES_TO_CODE.get(fan_mode)
        if code is None:
            raise HomeAssistantError(f"Unknown fan mode {fan_mode}")
        try:
            await self._client.write_register(REG_FAN_COMMAND + self._i, code)
        except AerLinkError as err:
            raise HomeAssistantError(f"AerLink: {err}") from err
        self._fan_cmd = (time.monotonic(), fan_mode)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        on = hvac_mode != HVACMode.OFF
        try:
            await self._client.write_coil(COIL_ZONE_ON + self._i, on)
        except AerLinkError as err:
            raise HomeAssistantError(f"AerLink: {err}") from err
        if self.coordinator.data:
            self.coordinator.data["on"][self._i] = on
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
