"""Color resolution shared by render components."""

from __future__ import annotations

from typing import Any

from PIL import ImageColor

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

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
    to any of the above.
    """
    if value is None:
        return default

    if isinstance(value, str) and "{{" in value:
        value = Template(value, hass).async_render(variables=variables)

    if isinstance(value, (list, tuple)) and len(value) == 3:
        return int(value[0]), int(value[1]), int(value[2])

    try:
        return ImageColor.getrgb(str(value))
    except ValueError:
        return default
