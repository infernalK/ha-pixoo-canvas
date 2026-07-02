"""Progress bar component: horizontal/vertical bar with threshold colors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..colors import RGB, resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext


def _blend(fill: RGB, background: RGB, ratio: float) -> RGB:
    """Blend `fill` into `background` by `ratio` (0 = background, 1 = fill)."""
    return tuple(round(f * ratio + b * (1 - ratio)) for f, b in zip(fill, background))  # type: ignore[return-value]


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw a bar filled proportionally to `value` between `min` and `max`."""
    x, y = component.get("position", [0, 0])
    width, height = component.get("size", [1, 1])
    x, y, width, height = int(x), int(y), int(width), int(height)
    orientation = str(component.get("orientation", "horizontal")).lower()
    transition = str(component.get("transition", "hard")).lower()

    min_value = resolve_value(component.get("min", 0), hass, variables, default=0.0)
    max_value = resolve_value(component.get("max", 100), hass, variables, default=100.0)
    value = resolve_value(component.get("value"), hass, variables, default=min_value)
    value = min(max(value, min_value), max_value)

    span = max_value - min_value
    ratio = 0.0 if span <= 0 else (value - min_value) / span

    background = resolve_color(
        component.get("background_color"), hass, variables, default=(40, 40, 40)
    )
    fill_default = resolve_color(component.get("color"), hass, variables, default=(0, 255, 0))
    thresholds = component.get("color_thresholds")
    fill_color = (
        resolve_threshold_color(value, thresholds, hass, variables, fill_default)
        if thresholds
        else fill_default
    )

    ctx.draw.rectangle((x, y, x + width - 1, y + height - 1), fill=background)

    length = height if orientation == "vertical" else width
    exact_fill = length * ratio
    filled = int(exact_fill)
    fraction = exact_fill - filled if transition == "smooth" else 0.0

    if orientation == "vertical":
        if filled > 0:
            ctx.draw.rectangle(
                (x, y + height - filled, x + width - 1, y + height - 1), fill=fill_color
            )
        if fraction > 0 and filled < height:
            edge_y = y + height - filled - 1
            ctx.draw.rectangle(
                (x, edge_y, x + width - 1, edge_y), fill=_blend(fill_color, background, fraction)
            )
    else:
        if filled > 0:
            ctx.draw.rectangle((x, y, x + filled - 1, y + height - 1), fill=fill_color)
        if fraction > 0 and filled < width:
            edge_x = x + filled
            ctx.draw.rectangle(
                (edge_x, y, edge_x, y + height - 1), fill=_blend(fill_color, background, fraction)
            )
