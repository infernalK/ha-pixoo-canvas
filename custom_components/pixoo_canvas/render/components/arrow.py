"""Arrow component: directional shaft + triangular head, for compass/wind/heading displays."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext


def _point(origin_x: float, origin_y: float, length: float, angle_degrees: float) -> tuple[float, float]:
    """A point `length` away from `origin`, at `angle_degrees` (0 = north/up, clockwise)."""
    rad = math.radians(angle_degrees)
    return origin_x + length * math.sin(rad), origin_y - length * math.cos(rad)


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw an arrow from `center`, `length` pixels long, pointing at `angle`."""
    center_x, center_y = component.get("center", [0, 0])
    center_x, center_y = int(center_x), int(center_y)
    length = resolve_value(component.get("length", 1), hass, variables, default=1.0)
    angle = resolve_value(component.get("angle", 0), hass, variables, default=0.0)

    default_color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    thresholds = component.get("color_thresholds")
    if thresholds:
        value = resolve_value(component.get("value"), hass, variables)
        color = resolve_threshold_color(value, thresholds, hass, variables, default_color)
    else:
        color = default_color

    thickness = int(component.get("thickness", 2))
    head_size = resolve_value(component.get("head_size", 4), hass, variables, default=4.0)

    tip_x, tip_y = _point(center_x, center_y, length, angle)
    ctx.draw.line([(center_x, center_y), (tip_x, tip_y)], fill=color, width=thickness)

    head1 = _point(tip_x, tip_y, head_size, angle + 150)
    head2 = _point(tip_x, tip_y, head_size, angle - 150)
    ctx.draw.polygon([(tip_x, tip_y), head1, head2], fill=color)
