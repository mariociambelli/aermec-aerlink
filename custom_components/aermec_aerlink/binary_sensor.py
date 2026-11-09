"""Demand sensors: per zone and for the whole plant."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AerLinkConfigEntry
from .coordinator import AerLinkCoordinator
from .entity import AerLinkZoneEntity, gateway_device


async def async_setup_entry(
    hass: HomeAssistant, entry: AerLinkConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = entry.runtime_data
    ents: list[BinarySensorEntity] = [
        PlantDemand(data.coordinator, entry.entry_id, entry.data[CONF_HOST])
    ]
    ents += [
        ZoneDemand(data.coordinator, entry.entry_id, i, zone, "demand")
        for i, zone in enumerate(data.zones)
    ]
    async_add_entities(ents)


class ZoneDemand(AerLinkZoneEntity, BinarySensorEntity):
    _attr_translation_key = "zone_demand"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self):
        return self._v("demand")


class PlantDemand(CoordinatorEntity[AerLinkCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "plant_demand"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: AerLinkCoordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_plant_demand"
        self._attr_device_info = gateway_device(entry_id, host)

    @property
    def is_on(self):
        d = self.coordinator.data
        if not d:
            return None
        return d["plant"] > 0 or any(d["demand"])

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data
        return {"zones_calling": d["plant"]} if d else None
