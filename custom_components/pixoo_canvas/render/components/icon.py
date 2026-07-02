"""Icon component: MDI icon glyph drawn from the bundled webfont, tinted by value."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import resolve_color
from ..mdi import load_icon_font, resolve_glyph
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext

_LOGGER = logging.getLogger(__name__)

_DEFAULT_SIZE = 16


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw an MDI icon glyph, tinted per `color`/`color_thresholds`."""
    icon = str(component.get("icon", ""))
    name = icon.split(":", 1)[-1]
    glyph = resolve_glyph(name)
    if glyph is None:
        _LOGGER.warning("Unknown MDI icon %r, skipping", name)
        return

    default_color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    thresholds = component.get("color_thresholds")
    if thresholds:
        value = resolve_value(component.get("value"), hass, variables)
        color = resolve_threshold_color(value, thresholds, hass, variables, default_color)
    else:
        color = default_color

    size = int(component.get("size", _DEFAULT_SIZE))
    font = load_icon_font(size)
    x, y = component.get("position", [0, 0])
    ctx.draw.text((int(x), int(y)), glyph, font=font, fill=color)
