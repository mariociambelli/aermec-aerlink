"""Config flow: host, port and zone names; options for polling and limits."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_ZONES,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_ZONES,
    REG_ROOM_TEMP,
)
from .modbus import AerLinkClient, AerLinkError


def _parse_zones(raw: str) -> list[str]:
    return [z.strip() for z in raw.replace("\n", ",").split(",") if z.strip()]


class AerLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            zones = _parse_zones(user_input[CONF_ZONES])
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()
            if not 1 <= len(zones) <= MAX_ZONES:
                errors[CONF_ZONES] = "invalid_zones"
            else:
                client = AerLinkClient(host, user_input[CONF_PORT])
                try:
                    await client.read_holding(REG_ROOM_TEMP, len(zones))
                except AerLinkError:
                    errors["base"] = "cannot_connect"
                finally:
                    await client.close()
            if not errors:
                return self.async_create_entry(
                    title=f"AerLink {host}",
                    data={CONF_HOST: host, CONF_PORT: user_input[CONF_PORT], CONF_ZONES: zones},
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_ZONES): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AerLinkOptionsFlow()


class AerLinkOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=o.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=600)),
                vol.Required(
                    CONF_MIN_TEMP, default=o.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
                ): vol.Coerce(float),
                vol.Required(
                    CONF_MAX_TEMP, default=o.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
                ): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
