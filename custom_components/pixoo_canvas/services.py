"""Home Assistant service handlers for Pixoo Canvas."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import DOMAIN, SERVICE_RENDER_PAGE
from .coordinator import PixooCoordinator
from .page_render import render_configured_page
from .pages import PagesYamlError, get_page
from .render.engine import render_page

_LOGGER = logging.getLogger(__name__)

SERVICE_RENDER_PAGE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional("page"): cv.string,
        vol.Optional("components"): [dict],
        vol.Optional("variables"): dict,
    }
)


def _get_coordinator(hass: HomeAssistant, device_id: str) -> PixooCoordinator:
    """Resolve a device_id to the Pixoo Canvas coordinator managing it."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise HomeAssistantError(f"Unknown device_id {device_id}")

    for entry_id in device.config_entries:
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(coordinator, PixooCoordinator):
            return coordinator

    raise HomeAssistantError(f"Device {device_id} is not a Pixoo Canvas device")


def _get_page(coordinator: PixooCoordinator, page_name: str) -> dict[str, Any]:
    """Look up a named page from the config entry's stored pages YAML."""
    try:
        return get_page(coordinator.config_entry, page_name)
    except PagesYamlError as err:
        raise HomeAssistantError(str(err)) from err


async def _async_handle_render_page(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the pixoo_canvas.render_page service call."""
    page_name = call.data.get("page")
    components = call.data.get("components")

    if (page_name is None) == (components is None):
        raise HomeAssistantError("Provide exactly one of 'page' or 'components'")

    coordinator = _get_coordinator(hass, call.data["device_id"])
    variables = call.data.get("variables")

    if page_name:
        page = _get_page(coordinator, page_name)
        await render_configured_page(hass, coordinator.client, page, variables)
    else:
        assert components is not None  # guaranteed by the check above
        await render_page(hass, coordinator.client, components, variables)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Pixoo Canvas services (idempotent across multiple config entries)."""
    if hass.services.has_service(DOMAIN, SERVICE_RENDER_PAGE):
        return

    async def _handle_render_page(call: ServiceCall) -> None:
        await _async_handle_render_page(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_RENDER_PAGE, _handle_render_page, schema=SERVICE_RENDER_PAGE_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister Pixoo Canvas services once no config entries remain."""
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_RENDER_PAGE)
