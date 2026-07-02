"""Config flow for Pixoo Canvas."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .api import PixooApiError, PixooClient
from .const import CONF_PAGES_YAML, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class PixooCanvasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pixoo Canvas."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: manual IP entry + connection test."""
        errors: dict[str, str] = {}

        if user_input is not None:
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

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

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
    """Handle Pixoo Canvas options: device IP, poll interval, and the pages YAML editor."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the device IP/scan interval/pages, validating everything before saving."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            scan_interval = user_input[CONF_SCAN_INTERVAL]
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
                                CONF_SCAN_INTERVAL: scan_interval,
                                CONF_PAGES_YAML: pages_yaml,
                            }
                        )

        current = user_input or {
            CONF_HOST: self.config_entry.data.get(CONF_HOST, ""),
            CONF_SCAN_INTERVAL: self.config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            ),
            CONF_PAGES_YAML: self.config_entry.options.get(CONF_PAGES_YAML, ""),
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=current[CONF_HOST]): TextSelector(),
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current[CONF_SCAN_INTERVAL]
                ): NumberSelector(
                    NumberSelectorConfig(min=5, max=3600, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_PAGES_YAML, default=current[CONF_PAGES_YAML]
                ): TextSelector(TextSelectorConfig(multiline=True)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
