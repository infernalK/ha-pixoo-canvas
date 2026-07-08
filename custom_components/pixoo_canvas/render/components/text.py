"""Text component: static bitmap text, or (with `scroll: true`) a native
device-animated scroll.

Static text is drawn into our own RGB buffer with a bundled bitmap font.
Scrolling text instead queues a `Draw/SendHttpText` call that `engine.py`
sends after the page's buffer push - the Pixoo's own firmware animates the
scroll in hardware, smoother than anything we could do by re-pushing shifted
frames ourselves, but only takes effect while the device is showing a custom
image ("drawing mode"), which a page render already puts it in via its own
SendHttpGif push right before.
"""

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

_SCROLL_DIRECTIONS = {"left": 0, "right": 1}
_SCROLL_ALIGNMENTS = {"left": 1, "center": 2, "right": 3}


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Render a text component's content: a static draw, or a queued native scroll."""
    content = str(component.get("content", ""))
    try:
        text = str(Template(content, hass).async_render(variables=variables))
    except TemplateError as err:
        _LOGGER.warning("Text content template failed to render, skipping: %s", err)
        return

    x, y = component.get("position", [0, 0])
    color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    align = str(component.get("align", "left")).lower()

    if component.get("scroll"):
        direction = _SCROLL_DIRECTIONS.get(
            str(component.get("scroll_direction", "left")).lower(), 0
        )
        ctx.scroll_texts.append(
            {
                "text_id": int(component.get("text_id", len(ctx.scroll_texts))),
                "position": (int(x), int(y)),
                "text": text,
                "color": color,
                "direction": direction,
                "font": int(component.get("divoom_font", 0)),
                "width": int(component.get("text_width", ctx.size)),
                "speed": int(component.get("scroll_speed", 100)),
                "align": _SCROLL_ALIGNMENTS.get(align, 1),
            }
        )
        return

    font_name = str(component.get("font", DEFAULT_FONT_NAME))
    if font_name not in BITMAP_FONT_NAMES:
        font_name = DEFAULT_FONT_NAME

    scale = int(component.get("font_size", DEFAULT_BITMAP_SCALE))
    text_width, _ = await hass.async_add_executor_job(bitmap_text_size, text, font_name, scale)
    if align == "center":
        x -= text_width // 2
    elif align == "right":
        x -= text_width
    await hass.async_add_executor_job(
        draw_bitmap_text, ctx.image, text, (x, y), color, font_name, scale
    )
