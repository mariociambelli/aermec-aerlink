"""Data update coordinator: one polling cycle reads every zone."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COIL_DEMAND,
    COIL_ZONE_ON,
    DOMAIN,
    FAN_RELEASE_SECONDS,
    REG_BASE_SP,
    REG_EFFECTIVE_SP,
    REG_FAN_COMMAND,
    REG_FAN_OUTPUT,
    REG_FAN_STATE,
    REG_PLANT_DEMAND,
    REG_ROOM_TEMP,
    REG_WATER_TEMP,
)
from .modbus import AerLinkClient, AerLinkError

_LOGGER = logging.getLogger(__name__)


@dataclass
class AerLinkData:
    client: AerLinkClient
    coordinator: "AerLinkCoordinator"
    zones: list[str]


class AerLinkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the AerLink."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AerLinkClient,
        zones: list[str],
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.zone_count = len(zones)
        # zone index -> monotonic time a pending fan command was first seen
        self._fan_cmd_seen: dict[int, float] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        c, n = self.client, self.zone_count
        try:
            data = {
                "temp": await c.read_holding(REG_ROOM_TEMP, n),
                "eff": await c.read_holding(REG_EFFECTIVE_SP, n),
                "base": await c.read_holding(REG_BASE_SP, n),
                "fan_state": await c.read_holding(REG_FAN_STATE, n),
                "fan_cmd": await c.read_holding(REG_FAN_COMMAND, n),
                "fan_output": await c.read_holding(REG_FAN_OUTPUT, n),
                "water": await c.read_holding(REG_WATER_TEMP, n),
                "on": await c.read_coils(COIL_ZONE_ON, n),
                "demand": await c.read_coils(COIL_DEMAND, n),
                "plant": (await c.read_holding(REG_PLANT_DEMAND, 1))[0],
            }
        except AerLinkError as err:
            raise UpdateFailed(str(err)) from err
        await self._release_fan_commands(data)
        return data

    async def _release_fan_commands(self, data: dict[str, Any]) -> None:
        """Clear fan commands the gateway left pending.

        The AerLink should reset 606+i to 0 after applying a fan command, but
        sometimes (e.g. after a power cut) it does not. While the register is
        not 0 the gateway keeps forcing the speed: the thermostat shows a lock,
        cannot be switched off by hand and ignores its own V1/V2/V3 settings.
        Writing 0 releases it without changing the current speed.
        """
        now = time.monotonic()
        for i, code in enumerate(data["fan_cmd"]):
            if not code:
                self._fan_cmd_seen.pop(i, None)
                continue
            seen = self._fan_cmd_seen.setdefault(i, now)
            if data["fan_state"][i] != code and now - seen < FAN_RELEASE_SECONDS:
                continue  # not applied yet: give the gateway time
            try:
                await self.client.write_register(REG_FAN_COMMAND + i, 0)
            except AerLinkError as err:
                _LOGGER.warning("Zone %d: cannot release fan command %d: %s", i, code, err)
                continue
            _LOGGER.info("Zone %d: released pending fan command %d", i, code)
            data["fan_cmd"][i] = 0
            self._fan_cmd_seen.pop(i, None)
