"""Config flow for Pixoo Canvas."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import yaml

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .api import PixooApiError, PixooClient
from .const import CONF_PAGES_YAML, DOMAIN

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
    """Handle Pixoo Canvas options: a raw YAML editor for configured pages."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit the pages YAML, validating it before saving."""
        errors: dict[str, str] = {}

        if user_input is not None:
            pages_yaml = user_input[CONF_PAGES_YAML]
            try:
                pages = yaml.safe_load(pages_yaml) or []
            except yaml.YAMLError:
                errors["base"] = "invalid_yaml"
            else:
                if not _is_valid_pages(pages):
                    errors["base"] = "invalid_schema"
                else:
                    return self.async_create_entry(data={CONF_PAGES_YAML: pages_yaml})

        current = (
            user_input[CONF_PAGES_YAML]
            if user_input is not None
            else self.config_entry.options.get(CONF_PAGES_YAML, "")
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_PAGES_YAML, default=current): TextSelector(
                    TextSelectorConfig(multiline=True)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
