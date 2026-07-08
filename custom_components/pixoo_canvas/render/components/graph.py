"""Graph component: an entity's recorder history, plotted as a line/area/bar chart."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..colors import resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext

_LOGGER = logging.getLogger(__name__)

_DEFAULT_LINE_COLOR = (52, 152, 219)
_DEFAULT_FILL_COLOR = (26, 82, 118)
_DEFAULT_BACKGROUND_COLOR = (17, 17, 17)


async def _fetch_history(hass: HomeAssistant, entity_id: str, hours: float) -> list[float]:
    """Numeric states for `entity_id` over the last `hours`, oldest first."""
    try:
        from homeassistant.components.recorder import get_instance
        from homeassistant.components.recorder.history import state_changes_during_period

        end_time = dt_util.utcnow()
        start_time = end_time - timedelta(hours=hours)
        history = await get_instance(hass).async_add_executor_job(
            state_changes_during_period, hass, start_time, end_time, entity_id
        )
    except Exception:  # noqa: BLE001 - recorder may be unavailable/unloaded
        _LOGGER.warning("Graph: failed to fetch history for %s", entity_id, exc_info=True)
        return []

    values = []
    for state in history.get(entity_id, []):
        try:
            values.append(float(state.state))
        except (TypeError, ValueError):
            continue
    return values


def _aggregate(values: list[float], num_points: int, func: str) -> list[float]:
    """Bin `values` down to at most `num_points` points using `func`."""
    bin_size = max(1, len(values) // num_points)
    aggregate = {"min": min, "max": max}.get(func)
    aggregated = []
    for i in range(0, len(values), bin_size):
        bucket = values[i : i + bin_size]
        if func == "last":
            aggregated.append(bucket[-1])
        elif aggregate:
            aggregated.append(aggregate(bucket))
        else:
            aggregated.append(sum(bucket) / len(bucket))
    return aggregated[-num_points:]


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Draw `entity_id`'s recent history as a line, filled area, or bar chart."""
    x, y = component.get("position", [0, 0])
    width, height = component.get("size", [1, 1])
    x, y, width, height = int(x), int(y), int(width), int(height)

    background = resolve_color(
        component.get("background_color"), hass, variables, default=_DEFAULT_BACKGROUND_COLOR
    )
    ctx.draw.rectangle((x, y, x + width - 1, y + height - 1), fill=background)

    entity_id = str(component.get("entity_id", ""))
    hours = resolve_value(component.get("hours", 24), hass, variables, default=24.0)
    values = await _fetch_history(hass, entity_id, hours)
    if not values:
        return

    num_points = int(component.get("points") or width)
    aggregate_func = str(component.get("aggregate_func", "avg")).lower()
    aggregated = _aggregate(values, max(1, num_points), aggregate_func)
    if not aggregated:
        return

    min_value = component.get("min_value")
    max_value = component.get("max_value")
    y_min = resolve_value(min_value, hass, variables, default=min(aggregated)) if min_value is not None else min(aggregated)
    y_max = resolve_value(max_value, hass, variables, default=max(aggregated)) if max_value is not None else max(aggregated)
    y_range = y_max - y_min if y_max > y_min else 1

    default_color = resolve_color(component.get("line_color"), hass, variables, default=_DEFAULT_LINE_COLOR)
    thresholds = component.get("color_thresholds")

    def color_for(val: float) -> tuple[int, int, int]:
        if thresholds:
            return resolve_threshold_color(val, thresholds, hass, variables, default_color)
        return default_color

    x_step = (width - 1) / (len(aggregated) - 1) if len(aggregated) > 1 else 0
    points_px = []
    for i, val in enumerate(aggregated):
        px_x = x + (round(i * x_step) if x_step else i)
        normalized_y = (val - y_min) / y_range
        px_y = y + height - 1 - round(normalized_y * (height - 1))
        points_px.append((px_x, px_y, val))

    style = str(component.get("style", "line")).lower()
    bottom_y = y + height - 1

    if style == "bar":
        bar_width = max(1, width // len(aggregated) - 1)
        for px_x, px_y, val in points_px:
            if px_y < bottom_y:
                ctx.draw.rectangle(
                    (px_x, px_y, min(px_x + bar_width - 1, x + width - 1), bottom_y),
                    fill=color_for(val),
                )
        return

    if style == "area" or bool(component.get("show_fill", False)):
        fill_color = resolve_color(component.get("fill_color"), hass, variables, default=_DEFAULT_FILL_COLOR)
        for px_x, px_y, _val in points_px:
            if px_y < bottom_y:
                ctx.draw.line([(px_x, px_y), (px_x, bottom_y)], fill=fill_color)

    for (x1, y1, v1), (x2, y2, v2) in zip(points_px, points_px[1:]):
        ctx.draw.line([(x1, y1), (x2, y2)], fill=color_for((v1 + v2) / 2))
