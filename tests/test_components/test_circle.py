"""Tests for the circle render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import circle
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_filled_circle_covers_center_and_edge(hass):
    """A filled circle colors both its center and pixels near its rim."""
    ctx = RenderContext()
    component = {
        "type": "circle",
        "center": [20, 20],
        "radius": 5,
        "color": [0, 255, 0],
    }

    await circle.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 20)) == (0, 255, 0)
    assert ctx.image.getpixel((20, 15)) == (0, 255, 0)


async def test_outline_circle_leaves_center_empty(hass):
    """An outline-only circle leaves its interior untouched."""
    ctx = RenderContext()
    component = {
        "type": "circle",
        "center": [20, 20],
        "radius": 8,
        "color": [255, 255, 255],
        "filled": False,
        "thickness": 1,
    }

    await circle.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 12)) == (255, 255, 255)
    assert ctx.image.getpixel((20, 20)) == (0, 0, 0)


async def test_color_thresholds_override_default_color(hass):
    """When color_thresholds are configured, the fill color follows the value's bracket."""
    ctx = RenderContext()
    component = {
        "type": "circle",
        "center": [10, 10],
        "radius": 4,
        "color": [255, 255, 255],
        "value": 90,
        "color_thresholds": [
            {"value": 0, "color": [0, 255, 0]},
            {"value": 80, "color": [255, 0, 0]},
        ],
    }

    await circle.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((10, 10)) == (255, 0, 0)
