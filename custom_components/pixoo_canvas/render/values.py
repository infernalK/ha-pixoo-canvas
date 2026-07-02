"""Numeric value and threshold-color resolution shared by render components."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template

from .colors import RGB, resolve_color


def resolve_value(
    value: Any,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
    default: float = 0.0,
) -> float:
    """Resolve a component numeric field to a float.

    Accepts a literal number, a numeric string, or a Jinja2 template string
    (rendered via HA's Template helper) evaluating to a number.
    """
    if value is None:
        return default

    if isinstance(value, str) and "{{" in value:
        value = Template(value, hass).async_render(variables=variables)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def resolve_threshold_color(
    value: float,
    thresholds: list[dict[str, Any]] | None,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
    default: RGB,
) -> RGB:
    """Pick a color from ascending `color_thresholds` entries for a numeric value.

    Each entry is `{"value": <threshold>, "color": <color>}`. The color of the
    highest threshold that is <= `value` wins; if `value` is below every
    threshold, `default` is returned.
    """
    if not thresholds:
        return default

    color = default
    ordered = sorted(thresholds, key=lambda entry: resolve_value(entry.get("value"), hass, variables))
    for entry in ordered:
        threshold = resolve_value(entry.get("value"), hass, variables)
        if value < threshold:
            break
        color = resolve_color(entry.get("color"), hass, variables, default)
    return color
