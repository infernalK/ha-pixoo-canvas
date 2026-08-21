"""Circle component: filled disc or outlined ring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext


def _paint(
    ctx: RenderContext, box: tuple[int, int, int, int], color: Any, filled: bool, thickness: int
) -> None:
    if filled:
        ctx.draw.ellipse(box, fill=color)
    else:
        ctx.draw.ellipse(box, outline=color, width=thickness)


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw a circle at `center`/`radius`, tinted per `color`/`color_thresholds`."""
    center_x, center_y = component.get("center", [0, 0])
    center_x, center_y = int(center_x), int(center_y)
    radius = int(component.get("radius", 1))

    default_color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    thresholds = component.get("color_thresholds")
    if thresholds:
        value = resolve_value(component.get("value"), hass, variables)
        color = resolve_threshold_color(value, thresholds, hass, variables, default_color)
    else:
        color = default_color

    box = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
    filled = bool(component.get("filled", True))
    thickness = int(component.get("thickness", 1))
    await hass.async_add_executor_job(_paint, ctx, box, color, filled, thickness)
