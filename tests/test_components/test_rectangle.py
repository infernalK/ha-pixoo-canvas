"""Tests for the rectangle render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import rectangle
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_filled_rectangle(hass):
    """A filled rectangle colors every pixel in its box."""
    ctx = RenderContext()
    component = {
        "type": "rectangle",
        "position": [2, 2],
        "size": [4, 4],
        "color": [0, 255, 0],
    }

    await rectangle.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((2, 2)) == (0, 255, 0)
    assert ctx.image.getpixel((5, 5)) == (0, 255, 0)
    assert ctx.image.getpixel((6, 6)) == (0, 0, 0)


async def test_outlined_rectangle_does_not_fill_center(hass):
    """An outlined rectangle leaves its interior untouched."""
    ctx = RenderContext()
    component = {
        "type": "rectangle",
        "position": [0, 0],
        "size": [10, 10],
        "color": "red",
        "filled": False,
    }

    await rectangle.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (255, 0, 0)
    assert ctx.image.getpixel((5, 5)) == (0, 0, 0)
