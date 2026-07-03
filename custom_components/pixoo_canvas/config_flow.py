"""Config flow for Pixoo Canvas."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .api import PixooApiError, PixooClient
from .const import CONF_DEFAULT_PAGE_DURATION, CONF_PAGES_YAML, DEFAULT_PAGE_DURATION, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Divoom's cloud service, used to look up devices it has seen on the same LAN
# as whoever calls it (this is the same endpoint other Pixoo HA integrations,
# e.g. gickowtf/pixoo-homeassistant, use for discovery — Divoom devices don't
# support local mDNS/SSDP). Discovery is best-effort: any failure here just
# falls back to manual IP entry, same as if it had never been attempted.
DISCOVERY_URL = "https://app.divoom-gz.com/Device/ReturnSameLANDevice"
MANUAL_ENTRY_VALUE = "__manual__"


class PixooCanvasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pixoo Canvas."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Try to discover a device on the LAN; fall back to manual IP entry."""
        self._discovered = await self._async_discover_devices()
        if self._discovered:
            return await self.async_step_pick_device()
        return await self.async_step_manual()

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick a discovered device, or fall back to manual entry."""
        if user_input is not None:
            selected = user_input[CONF_HOST]
            if selected == MANUAL_ENTRY_VALUE:
                return await self.async_step_manual()
            return await self.async_step_manual({CONF_HOST: selected})

        options = [*self._discovered, {"value": MANUAL_ENTRY_VALUE, "label": "Enter IP manually"}]
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(step_id="pick_device", data_schema=schema)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual IP entry (or a pre-filled, discovered IP) + connection test."""
        errors: dict[str, str] = {}

        if user_input is not None and CONF_HOST in user_input:
            host = user_input[CONF_HOST]
            self._async_abort_entries_match({CONF_HOST: host})

            session = async_get_clientsession(self.hass)
            client = PixooClient(session, host)
            try:
                await client.get_all_conf()
            except PixooApiError:
                _LOGGER.debug("Connection test failed for host %s", host, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=host, data={CONF_HOST: host})

        schema = vol.Schema(
            {vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str}
        )
        return self.async_show_form(step_id="manual", data_schema=schema, errors=errors)

    async def _async_discover_devices(self) -> list[dict[str, str]]:
        """Look up Pixoo devices Divoom's cloud has seen on the same LAN, best-effort."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                DISCOVERY_URL, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                data = await resp.json(content_type=None)
        except Exception:  # noqa: BLE001 - discovery is optional, never blocks setup
            _LOGGER.debug("Pixoo LAN discovery failed, falling back to manual IP", exc_info=True)
            return []

        configured_hosts = {
            entry.data.get(CONF_HOST) for entry in self._async_current_entries()
        }
        options = []
        for device in data.get("DeviceList", []) if isinstance(data, dict) else []:
            ip = device.get("DevicePrivateIP")
            if not ip or ip in configured_hosts:
                continue
            name = device.get("DeviceName") or "Pixoo"
            options.append({"value": ip, "label": f"{name} ({ip})"})
        return options

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PixooCanvasOptionsFlowHandler:
        """Create the options flow (raw YAML editor for pages)."""
        return PixooCanvasOptionsFlowHandler()


def _is_valid_pages(pages: Any) -> bool:
    """Validate the parsed pages YAML: a list of {name, components: [...]}."""
    if not isinstance(pages, list):
        return False
    return all(
        isinstance(page, dict)
        and isinstance(page.get("name"), str)
        and isinstance(page.get("components"), list)
        for page in pages
    )


class PixooCanvasOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Pixoo Canvas options: device IP, default page duration, and the pages YAML."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the device IP/default page duration/pages, validating before saving."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            default_page_duration = user_input[CONF_DEFAULT_PAGE_DURATION]
            pages_yaml = user_input[CONF_PAGES_YAML]

            try:
                pages = yaml.safe_load(pages_yaml) or []
            except yaml.YAMLError:
                errors["base"] = "invalid_yaml"
            else:
                if not _is_valid_pages(pages):
                    errors["base"] = "invalid_schema"
                else:
                    session = async_get_clientsession(self.hass)
                    try:
                        await PixooClient(session, host).get_all_conf()
                    except PixooApiError:
                        _LOGGER.debug(
                            "Connection test failed for host %s", host, exc_info=True
                        )
                        errors["base"] = "cannot_connect"
                    else:
                        if host != self.config_entry.data.get(CONF_HOST):
                            self.hass.config_entries.async_update_entry(
                                self.config_entry,
                                data={**self.config_entry.data, CONF_HOST: host},
                            )
                        return self.async_create_entry(
                            data={
                                CONF_DEFAULT_PAGE_DURATION: default_page_duration,
                                CONF_PAGES_YAML: pages_yaml,
                            }
                        )

        current = user_input or {
            CONF_HOST: self.config_entry.data.get(CONF_HOST, ""),
            CONF_DEFAULT_PAGE_DURATION: self.config_entry.options.get(
                CONF_DEFAULT_PAGE_DURATION, DEFAULT_PAGE_DURATION
            ),
            CONF_PAGES_YAML: self.config_entry.options.get(CONF_PAGES_YAML, ""),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current[CONF_HOST]): TextSelector(),
                vol.Required(
                    CONF_DEFAULT_PAGE_DURATION, default=current[CONF_DEFAULT_PAGE_DURATION]
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=3600, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_PAGES_YAML, default=current[CONF_PAGES_YAML]
                ): TextSelector(TextSelectorConfig(multiline=True)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
