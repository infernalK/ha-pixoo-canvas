"""Text component: Jinja-templated content drawn with the bundled bitmap font."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from ..colors import resolve_color
from ..font_loader import DEFAULT_FONT_SIZE, load_font

if TYPE_CHECKING:
    from ..engine import RenderContext


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
    font = await hass.async_add_executor_job(
        load_font, int(component.get("font_size", DEFAULT_FONT_SIZE))
    )
    align = str(component.get("align", "left")).lower()

    if align in ("center", "right"):
        bbox = ctx.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if align == "center":
            x -= text_width // 2
        elif align == "right":
            x -= text_width

    ctx.draw.text((x, y), text, fill=color, font=font)
