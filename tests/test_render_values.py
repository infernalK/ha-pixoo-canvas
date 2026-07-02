"""Tests for numeric value and threshold-color resolution helpers."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.values import resolve_threshold_color, resolve_value


async def test_resolve_value_literal(hass):
    """A literal number is passed through as a float."""
    assert resolve_value(42, hass, None) == 42.0


async def test_resolve_value_template(hass):
    """A Jinja2 template string is rendered and coerced to a float."""
    assert resolve_value("{{ 20 + 5 }}", hass, None) == 25.0


async def test_resolve_value_invalid_falls_back_to_default(hass):
    """A non-numeric result falls back to the given default."""
    assert resolve_value("not-a-number", hass, None, default=-1.0) == -1.0
    assert resolve_value(None, hass, None, default=7.0) == 7.0


async def test_resolve_threshold_color_picks_highest_matching_threshold(hass):
    """The color of the highest threshold at or below the value wins."""
    thresholds = [
        {"value": 0, "color": [0, 255, 0]},
        {"value": 60, "color": [255, 165, 0]},
        {"value": 80, "color": [255, 0, 0]},
    ]

    assert resolve_threshold_color(10, thresholds, hass, None, (1, 1, 1)) == (0, 255, 0)
    assert resolve_threshold_color(60, thresholds, hass, None, (1, 1, 1)) == (255, 165, 0)
    assert resolve_threshold_color(95, thresholds, hass, None, (1, 1, 1)) == (255, 0, 0)


async def test_resolve_threshold_color_below_all_thresholds_uses_default(hass):
    """A value below every threshold falls back to the default color."""
    thresholds = [{"value": 60, "color": [255, 0, 0]}]

    assert resolve_threshold_color(10, thresholds, hass, None, (9, 9, 9)) == (9, 9, 9)


async def test_resolve_threshold_color_empty_uses_default(hass):
    """No thresholds configured falls back to the default color."""
    assert resolve_threshold_color(50, None, hass, None, (9, 9, 9)) == (9, 9, 9)
