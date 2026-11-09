"""Per-zone sensors: coil water temperature, fan output and fan speed."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AerLinkConfigEntry
from .const import FAN_CODE_OFF, FAN_CODES
from .entity import AerLinkZoneEntity

FAN_SPEED_OPTIONS = ["off", *FAN_CODES.values(), "unknown"]


async def async_setup_entry(
    hass: HomeAssistant, entry: AerLinkConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data
    ents: list[SensorEntity] = []
    for i, zone in enumerate(data.zones):
        ents.append(WaterTemperature(data.coordinator, entry.entry_id, i, zone, "water_temperature"))
        ents.append(FanOutput(data.coordinator, entry.entry_id, i, zone, "fan_output"))
        ents.append(FanSpeed(data.coordinator, entry.entry_id, i, zone, "fan_speed"))
    async_add_entities(ents)


class WaterTemperature(AerLinkZoneEntity, SensorEntity):
    _attr_translation_key = "water_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 1

    @property
    def native_value(self):
        v = self._v("water")
        return None if v is None else v / 10


class FanOutput(AerLinkZoneEntity, SensorEntity):
    _attr_translation_key = "fan_output"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self):
        return self._v("fan_output")


class FanSpeed(AerLinkZoneEntity, SensorEntity):
    _attr_translation_key = "fan_speed"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = FAN_SPEED_OPTIONS

    @property
    def native_value(self):
        v = self._v("fan_state")
        if v is None:
            return None
        if v == FAN_CODE_OFF:
            return "off"
        return FAN_CODES.get(v, "unknown")
