"""Line component: straight segment with configurable thickness."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw a straight line between `start` and `end`, tinted per `color`/`color_thresholds`."""
    start_x, start_y = component.get("start", [0, 0])
    end_x, end_y = component.get("end", [0, 0])

    default_color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    thresholds = component.get("color_thresholds")
    if thresholds:
        value = resolve_value(component.get("value"), hass, variables)
        color = resolve_threshold_color(value, thresholds, hass, variables, default_color)
    else:
        color = default_color

    thickness = int(component.get("thickness", 1))
    ctx.draw.line(
        [(int(start_x), int(start_y)), (int(end_x), int(end_y))], fill=color, width=thickness
    )
