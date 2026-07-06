"""Dispatch a configured page to its renderer, based on its `page_type`.

`page_type: components` (the default, for full backward compatibility) goes
through the normal render engine (a composed RGB buffer, pushed to the
device). `clock`/`channel`/`visualizer` instead switch the device to one of
its built-in native screens - no buffer is composed or pushed for those.
`sound_meter` switches the device to its built-in sound meter (decibel) tool -
also no buffer, and unlike clock/channel/visualizer it takes no `id` since the
device only has the one sound meter. `pv`/`fuel` are prebuilt layouts: their
fields are expanded into a `components` list (see `render.page_templates`) and
rendered like any other `components` page.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

from .api import PixooClient
from .const import DEFAULT_PAGE_TYPE, NATIVE_CHANNEL_PAGE_TYPES
from .render.engine import render_page
from .render.page_templates import build_fuel_components, build_pv_components

_LOGGER = logging.getLogger(__name__)

_NATIVE_CHANNEL_SETTERS = {
    "clock": "set_clock",
    "channel": "set_custom_channel",
    "visualizer": "set_visualizer",
}


def _resolve_int_field(
    page: dict[str, Any],
    field: str,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> int | None:
    """Resolve a page field as a Jinja template (if any) and cast it to int."""
    value = page.get(field)
    if value is None:
        _LOGGER.warning(
            "Page %r (page_type %r) is missing required field %r, skipping",
            page.get("name"),
            page.get("page_type"),
            field,
        )
        return None
    try:
        rendered = Template(str(value), hass).async_render(variables=variables)
    except TemplateError as err:
        _LOGGER.warning("Page %r field %r template failed to render: %s", page.get("name"), field, err)
        return None
    try:
        return int(float(rendered))
    except (TypeError, ValueError):
        _LOGGER.warning("Page %r field %r did not resolve to a number: %r", page.get("name"), field, rendered)
        return None


async def _render_native_channel_page(
    page_type: str,
    page: dict[str, Any],
    client: PixooClient,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Switch the device to a built-in clock/custom-channel/visualizer screen."""
    channel_id = _resolve_int_field(page, "id", hass, variables)
    if channel_id is None:
        return
    setter = getattr(client, _NATIVE_CHANNEL_SETTERS[page_type])
    await setter(channel_id)


async def render_configured_page(
    hass: HomeAssistant,
    client: PixooClient,
    page: dict[str, Any],
    variables: dict[str, Any] | None = None,
) -> None:
    """Render a full page dict, dispatching on its `page_type`."""
    page_type = str(page.get("page_type", DEFAULT_PAGE_TYPE)).lower()

    if page_type == DEFAULT_PAGE_TYPE:
        await render_page(hass, client, page.get("components", []), variables)
    elif page_type in NATIVE_CHANNEL_PAGE_TYPES:
        await _render_native_channel_page(page_type, page, client, hass, variables)
    elif page_type == "sound_meter":
        await client.restart_noise_status()
    elif page_type == "pv":
        await render_page(hass, client, build_pv_components(page), variables)
    elif page_type == "fuel":
        await render_page(hass, client, build_fuel_components(page), variables)
    else:
        _LOGGER.warning("Unknown page_type %r, skipping page %r", page_type, page.get("name"))
