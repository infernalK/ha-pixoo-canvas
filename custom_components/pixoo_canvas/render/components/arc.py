"""Arc component: circular arc outline or pie slice, for gauges and progress rings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext

# Angles are authored as "0 = top (12 o'clock), clockwise", matching the rest of this
# integration's compass/gauge components. Pillow measures from 3 o'clock, also
# clockwise, so shifting by -90 degrees converts one convention to the other.
_ANGLE_OFFSET = 90


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw an arc/pie slice at `center`/`radius` between `start_angle` and `end_angle`."""
    center_x, center_y = component.get("center", [0, 0])
    center_x, center_y = int(center_x), int(center_y)
    radius = int(component.get("radius", 1))

    start_angle = resolve_value(component.get("start_angle", 0), hass, variables, default=0.0)
    end_angle = resolve_value(component.get("end_angle", 90), hass, variables, default=90.0)

    default_color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    thresholds = component.get("color_thresholds")
    if thresholds:
        value = resolve_value(component.get("value"), hass, variables)
        color = resolve_threshold_color(value, thresholds, hass, variables, default_color)
    else:
        color = default_color

    box = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
    filled = bool(component.get("filled", False))
    thickness = int(component.get("thickness", 2))

    background = component.get("background_color")
    if background is not None:
        # A full circle (any start/end 360 degrees apart draws the same complete
        # ring), so it always represents the gauge's full range regardless of
        # this arc's own start_angle/end_angle - the "track" a partial sweep
        # reads against, same idea as progress_bar's background_color.
        bg_color = resolve_color(background, hass, variables, default=(40, 40, 40))
        if filled:
            ctx.draw.pieslice(box, start=-90, end=270, fill=bg_color)
        else:
            ctx.draw.arc(box, start=-90, end=270, fill=bg_color, width=thickness)

    pillow_start = start_angle - _ANGLE_OFFSET
    pillow_end = end_angle - _ANGLE_OFFSET

    if filled:
        ctx.draw.pieslice(box, start=pillow_start, end=pillow_end, fill=color)
    else:
        ctx.draw.arc(box, start=pillow_start, end=pillow_end, fill=color, width=thickness)
