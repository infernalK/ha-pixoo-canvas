"""Tests for the line render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import line
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_horizontal_line_drawn(hass):
    """A horizontal line fills the pixels between start and end."""
    ctx = RenderContext()
    component = {
        "type": "line",
        "start": [0, 5],
        "end": [10, 5],
        "color": [255, 0, 0],
    }

    await line.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 5)) == (255, 0, 0)
    assert ctx.image.getpixel((10, 5)) == (255, 0, 0)
    assert ctx.image.getpixel((5, 4)) == (0, 0, 0)


async def test_thickness_widens_the_line(hass):
    """A thicker line covers pixels on both sides of the center axis."""
    ctx = RenderContext()
    component = {
        "type": "line",
        "start": [0, 10],
        "end": [10, 10],
        "color": [255, 255, 255],
        "thickness": 3,
    }

    await line.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((5, 9)) == (255, 255, 255)
    assert ctx.image.getpixel((5, 10)) == (255, 255, 255)
    assert ctx.image.getpixel((5, 11)) == (255, 255, 255)


async def test_color_thresholds_override_default_color(hass):
    """When color_thresholds are configured, the line color follows the value's bracket."""
    ctx = RenderContext()
    component = {
        "type": "line",
        "start": [0, 0],
        "end": [10, 0],
        "color": [255, 255, 255],
        "value": 30,
        "color_thresholds": [
            {"value": 0, "color": [0, 255, 0]},
            {"value": 25, "color": [255, 0, 0]},
        ],
    }

    await line.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (255, 0, 0)
