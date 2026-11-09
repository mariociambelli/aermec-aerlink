"""Aermec AerLink integration (local Modbus TCP)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_ZONES, DEFAULT_SCAN_INTERVAL
from .coordinator import AerLinkCoordinator, AerLinkData
from .entity import gateway_device
from .modbus import AerLinkClient

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR]

type AerLinkConfigEntry = ConfigEntry[AerLinkData]


async def async_setup_entry(hass: HomeAssistant, entry: AerLinkConfigEntry) -> bool:
    zones: list[str] = entry.data[CONF_ZONES]
    client = AerLinkClient(entry.data[CONF_HOST], entry.data[CONF_PORT])
    scan = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    coordinator = AerLinkCoordinator(hass, entry, client, zones, scan)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = AerLinkData(client, coordinator, zones)
    # The gateway device must exist before zone devices point to it (via_device).
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **gateway_device(entry.entry_id, entry.data[CONF_HOST])
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: AerLinkConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AerLinkConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.client.close()
    return ok
