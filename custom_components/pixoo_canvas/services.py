"""Home Assistant service handlers for Pixoo Canvas."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    DEFAULT_BUZZER_ACTIVE_TIME_MS,
    DEFAULT_BUZZER_OFF_TIME_MS,
    DEFAULT_BUZZER_TOTAL_TIME_MS,
    DOMAIN,
    SERVICE_PLAY_BUZZER,
    SERVICE_RENDER_PAGE,
)
from .coordinator import PixooCoordinator
from .page_render import render_configured_page
from .pages import PagesYamlError, get_page, is_valid_page_shape

_LOGGER = logging.getLogger(__name__)

# Fields carrying the inline page definition itself, as opposed to call
# routing/metadata (device_id, page name lookup, template variables). Passed
# straight through to render_configured_page as the page dict, so any
# page_type's fields (id for clock/channel/visualizer; power/storage/... for
# pv; title/name1/price1/... for fuel) work without a fixed schema per type.
_ROUTING_KEYS = {"device_id", "page", "variables"}

SERVICE_RENDER_PAGE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional("page"): cv.string,
        vol.Optional("page_type"): cv.string,
        vol.Optional("components"): [dict],
        vol.Optional("variables"): dict,
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_PLAY_BUZZER_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional("active_time_ms", default=DEFAULT_BUZZER_ACTIVE_TIME_MS): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("off_time_ms", default=DEFAULT_BUZZER_OFF_TIME_MS): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional("total_time_ms", default=DEFAULT_BUZZER_TOTAL_TIME_MS): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
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
    inline_page = {k: v for k, v in call.data.items() if k not in _ROUTING_KEYS}

    if (page_name is None) == (not inline_page):
        raise HomeAssistantError(
            "Provide exactly one of 'page', or inline page fields "
            "('components', 'page_type', and/or its other fields)"
        )

    coordinator = _get_coordinator(hass, call.data["device_id"])
    variables = call.data.get("variables")

    if page_name:
        page = _get_page(coordinator, page_name)
    else:
        if not is_valid_page_shape(inline_page):
            raise HomeAssistantError(f"Invalid inline page definition: {inline_page}")
        page = inline_page

    await render_configured_page(hass, coordinator.client, page, variables)


async def _async_handle_play_buzzer(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the pixoo_canvas.play_buzzer service call."""
    coordinator = _get_coordinator(hass, call.data["device_id"])
    await coordinator.client.play_buzzer(
        call.data["active_time_ms"], call.data["off_time_ms"], call.data["total_time_ms"]
    )


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Pixoo Canvas services (idempotent across multiple config entries)."""
    if hass.services.has_service(DOMAIN, SERVICE_RENDER_PAGE):
        return

    async def _handle_render_page(call: ServiceCall) -> None:
        await _async_handle_render_page(hass, call)

    async def _handle_play_buzzer(call: ServiceCall) -> None:
        await _async_handle_play_buzzer(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_RENDER_PAGE, _handle_render_page, schema=SERVICE_RENDER_PAGE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_BUZZER, _handle_play_buzzer, schema=SERVICE_PLAY_BUZZER_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister Pixoo Canvas services once no config entries remain."""
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_RENDER_PAGE)
        hass.services.async_remove(DOMAIN, SERVICE_PLAY_BUZZER)
