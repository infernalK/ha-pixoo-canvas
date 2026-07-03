"""Color resolution shared by render components."""

from __future__ import annotations

import logging
from typing import Any

from PIL import ImageColor

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)

RGB = tuple[int, int, int]


def resolve_color(
    value: Any,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
    default: RGB,
) -> RGB:
    """Resolve a component color field to an (r, g, b) tuple.

    Accepts a literal [r, g, b] sequence, a CSS color name, a hex string, or
    a Jinja2 template string (rendered via HA's Template helper) evaluating
    to any of the above. A template that fails to render (e.g. a sensor
    briefly at "unknown") falls back to `default` instead of raising, so one
    bad color field can't take down a whole page render.
    """
    if value is None:
        return default

    if isinstance(value, str) and "{{" in value:
        try:
            value = Template(value, hass).async_render(variables=variables)
        except TemplateError as err:
            _LOGGER.warning("Color template failed to render, using default: %s", err)
            return default

    if isinstance(value, (list, tuple)) and len(value) == 3:
        return int(value[0]), int(value[1]), int(value[2])

    try:
        rgb = ImageColor.getrgb(str(value))
    except ValueError:
        return default
    # getrgb() returns 4 components (RGBA) for some inputs (e.g. "#RRGGBBAA");
    # every caller expects a plain 3-tuple, so drop any alpha channel.
    return rgb[0], rgb[1], rgb[2]
