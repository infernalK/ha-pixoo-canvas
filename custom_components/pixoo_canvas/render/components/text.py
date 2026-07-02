"""Text component: Jinja-templated content drawn with a bundled font."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from ..bitmap_font import BITMAP_FONT_NAMES, bitmap_text_size, draw_bitmap_text
from ..colors import resolve_color
from ..font_loader import DEFAULT_FONT_SIZE, load_font

if TYPE_CHECKING:
    from ..engine import RenderContext

# pico_8 is the default: a true pixel-bitmap font (not a scaled TrueType
# outline) that stays narrow *and* a full 5px tall at native scale, which
# reads far better on a real, diffused LED matrix than a small TrueType font.
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
    text = str(Template(content, hass).async_render(variables=variables))

    x, y = component.get("position", [0, 0])
    color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    font_name = str(component.get("font", DEFAULT_FONT_NAME))
    align = str(component.get("align", "left")).lower()

    if font_name in BITMAP_FONT_NAMES:
        scale = int(component.get("font_size", DEFAULT_BITMAP_SCALE))
        text_width, _ = await hass.async_add_executor_job(
            bitmap_text_size, text, font_name, scale
        )
        if align == "center":
            x -= text_width // 2
        elif align == "right":
            x -= text_width
        await hass.async_add_executor_job(
            draw_bitmap_text, ctx.image, text, (x, y), color, font_name, scale
        )
        return

    font = await hass.async_add_executor_job(
        load_font, int(component.get("font_size", DEFAULT_FONT_SIZE)), font_name
    )
    if align in ("center", "right"):
        bbox = ctx.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if align == "center":
            x -= text_width // 2
        elif align == "right":
            x -= text_width

    ctx.draw.text((x, y), text, fill=color, font=font)
