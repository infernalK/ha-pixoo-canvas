"""Text component: Jinja-templated content drawn with a bundled font."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

from ..bitmap_font import BITMAP_FONT_NAMES, bitmap_text_size, draw_bitmap_text
from ..colors import resolve_color

if TYPE_CHECKING:
    from ..engine import RenderContext

_LOGGER = logging.getLogger(__name__)

# pico_8 is the default: a true pixel-bitmap font, narrow and a full 5px tall
# at native scale. Both bundled fonts (pico_8, gicko) are pixel-bitmap - a
# scaled TrueType outline was tried and dropped, as it reads poorly at the
# tiny sizes a real, diffused LED matrix needs.
DEFAULT_FONT_NAME = "pico_8"
DEFAULT_BITMAP_SCALE = 1


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Render a text component's content and draw it at its position."""
    content = str(component.get("content", ""))
    try:
        text = str(Template(content, hass).async_render(variables=variables))
    except TemplateError as err:
        _LOGGER.warning("Text content template failed to render, skipping: %s", err)
        return

    x, y = component.get("position", [0, 0])
    color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    font_name = str(component.get("font", DEFAULT_FONT_NAME))
    if font_name not in BITMAP_FONT_NAMES:
        font_name = DEFAULT_FONT_NAME
    align = str(component.get("align", "left")).lower()

    scale = int(component.get("font_size", DEFAULT_BITMAP_SCALE))
    text_width, _ = await hass.async_add_executor_job(bitmap_text_size, text, font_name, scale)
    if align == "center":
        x -= text_width // 2
    elif align == "right":
        x -= text_width
    await hass.async_add_executor_job(
        draw_bitmap_text, ctx.image, text, (x, y), color, font_name, scale
    )
