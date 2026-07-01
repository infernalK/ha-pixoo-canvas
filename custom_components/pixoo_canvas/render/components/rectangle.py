"""Rectangle component: filled or outlined box."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import resolve_color

if TYPE_CHECKING:
    from ..engine import RenderContext


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw a filled or outlined rectangle at its position/size."""
    x, y = component.get("position", [0, 0])
    width, height = component.get("size", [1, 1])
    color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))

    box = (int(x), int(y), int(x) + int(width) - 1, int(y) + int(height) - 1)
    if bool(component.get("filled", True)):
        ctx.draw.rectangle(box, fill=color)
    else:
        ctx.draw.rectangle(box, outline=color)
