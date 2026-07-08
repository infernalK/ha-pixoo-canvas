"""Tests for the arrow render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import arrow
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_pointing_north_draws_shaft_upward(hass):
    """angle=0 (north) draws the shaft from center straight up."""
    ctx = RenderContext()
    component = {
        "type": "arrow",
        "center": [20, 20],
        "length": 10,
        "angle": 0,
        "color": [0, 255, 0],
        "thickness": 1,
        "head_size": 3,
    }

    await arrow.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 15)) == (0, 255, 0)  # midpoint of the shaft
    assert ctx.image.getpixel((20, 10)) == (0, 255, 0)  # tip


async def test_pointing_east_draws_shaft_rightward(hass):
    """angle=90 (east) draws the shaft from center to the right."""
    ctx = RenderContext()
    component = {
        "type": "arrow",
        "center": [20, 20],
        "length": 10,
        "angle": 90,
        "color": [0, 255, 0],
        "thickness": 1,
        "head_size": 3,
    }

    await arrow.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((25, 20)) == (0, 255, 0)
    assert ctx.image.getpixel((30, 20)) == (0, 255, 0)


async def test_color_thresholds_override_default_color(hass):
    """When color_thresholds are configured, the arrow color follows the value's bracket."""
    ctx = RenderContext()
    component = {
        "type": "arrow",
        "center": [20, 20],
        "length": 10,
        "angle": 0,
        "color": [255, 255, 255],
        "value": 30,
        "color_thresholds": [
            {"value": 0, "color": [0, 255, 0]},
            {"value": 25, "color": [255, 0, 0]},
        ],
    }

    await arrow.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 15)) == (255, 0, 0)
