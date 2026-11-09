"""Data update coordinator: one polling cycle reads every zone."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    COIL_DEMAND,
    COIL_ZONE_ON,
    DOMAIN,
    REG_BASE_SP,
    REG_EFFECTIVE_SP,
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

    async def _async_update_data(self) -> dict[str, Any]:
        c, n = self.client, self.zone_count
        try:
            return {
                "temp": await c.read_holding(REG_ROOM_TEMP, n),
                "eff": await c.read_holding(REG_EFFECTIVE_SP, n),
                "base": await c.read_holding(REG_BASE_SP, n),
                "fan_state": await c.read_holding(REG_FAN_STATE, n),
                "fan_output": await c.read_holding(REG_FAN_OUTPUT, n),
                "water": await c.read_holding(REG_WATER_TEMP, n),
                "on": await c.read_coils(COIL_ZONE_ON, n),
                "demand": await c.read_coils(COIL_DEMAND, n),
                "plant": (await c.read_holding(REG_PLANT_DEMAND, 1))[0],
            }
        except AerLinkError as err:
            raise UpdateFailed(str(err)) from err
