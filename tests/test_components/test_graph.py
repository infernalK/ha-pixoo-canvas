"""Tests for the graph render component.

History fetching (`_fetch_history`) hits HA's recorder, which isn't set up in these
tests, so it's monkeypatched with canned values - these tests target the
aggregation/plotting logic, not the recorder integration itself.
"""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import graph
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_no_history_leaves_only_background(hass, monkeypatch):
    """With no history data, only the background rectangle is drawn."""

    async def _fake_history(*_args, **_kwargs):
        return []

    monkeypatch.setattr(graph, "_fetch_history", _fake_history)

    ctx = RenderContext()
    component = {
        "type": "graph",
        "position": [0, 0],
        "size": [10, 10],
        "entity_id": "sensor.missing",
        "background_color": [10, 10, 10],
    }

    await graph.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((5, 5)) == (10, 10, 10)


async def test_line_style_plots_rising_values_upward(hass, monkeypatch):
    """Rising values are plotted with higher points nearer the top of the box."""

    async def _fake_history(*_args, **_kwargs):
        return [0, 100]

    monkeypatch.setattr(graph, "_fetch_history", _fake_history)

    ctx = RenderContext()
    component = {
        "type": "graph",
        "position": [0, 0],
        "size": [10, 10],
        "entity_id": "sensor.rising",
        "points": 2,
        "aggregate_func": "avg",
        "line_color": [255, 255, 255],
        "background_color": [0, 0, 0],
    }

    await graph.draw(component, ctx, hass, None)

    # The min value (0) plots at the bottom row, the max value (100) at the top row.
    assert ctx.image.getpixel((0, 9)) == (255, 255, 255)
    assert ctx.image.getpixel((9, 0)) == (255, 255, 255)


async def test_bar_style_fills_from_bottom(hass, monkeypatch):
    """Bar style draws each point as a column rising from the bottom of the box."""

    async def _fake_history(*_args, **_kwargs):
        return [50]

    monkeypatch.setattr(graph, "_fetch_history", _fake_history)

    ctx = RenderContext()
    component = {
        "type": "graph",
        "position": [0, 0],
        "size": [4, 10],
        "entity_id": "sensor.single",
        "points": 1,
        "style": "bar",
        "min_value": 0,
        "max_value": 100,
        "line_color": [0, 255, 0],
        "background_color": [0, 0, 0],
    }

    await graph.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 9)) == (0, 255, 0)  # bottom of the bar
    assert ctx.image.getpixel((0, 5)) == (0, 255, 0)  # mid-height, ~50%
    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)  # above the bar
