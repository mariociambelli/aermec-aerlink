"""Base entities: one device per zone, plus one device for the gateway."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AerLinkCoordinator


def gateway_device(entry_id: str, host: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="AerLink",
        manufacturer="Aermec",
        model=f"AerLink ({host})",
    )


class AerLinkZoneEntity(CoordinatorEntity[AerLinkCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AerLinkCoordinator, entry_id: str, idx: int, zone: str, key: str) -> None:
        super().__init__(coordinator)
        self._i = idx
        self._attr_unique_id = f"{entry_id}_zone{idx}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_zone{idx}")},
            name=zone,
            manufacturer="Aermec",
            model="Zone thermostat",
            suggested_area=zone,
            via_device=(DOMAIN, entry_id),
        )

    def _v(self, key: str) -> Any:
        d = self.coordinator.data
        return d[key][self._i] if d else None
