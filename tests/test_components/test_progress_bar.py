"""Tests for the progress_bar render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import progress_bar
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_horizontal_bar_fills_proportionally(hass):
    """A 50% value fills half the bar's width, leaving the rest as background."""
    ctx = RenderContext()
    component = {
        "type": "progress_bar",
        "position": [0, 0],
        "size": [10, 2],
        "min": 0,
        "max": 100,
        "value": 50,
        "color": [0, 255, 0],
        "background_color": [10, 10, 10],
    }

    await progress_bar.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (0, 255, 0)
    assert ctx.image.getpixel((4, 0)) == (0, 255, 0)
    assert ctx.image.getpixel((5, 0)) == (10, 10, 10)
    assert ctx.image.getpixel((9, 0)) == (10, 10, 10)


async def test_vertical_bar_fills_from_bottom(hass):
    """A vertical bar fills from the bottom of its box upward."""
    ctx = RenderContext()
    component = {
        "type": "progress_bar",
        "position": [0, 0],
        "size": [2, 10],
        "orientation": "vertical",
        "min": 0,
        "max": 100,
        "value": 50,
        "color": [0, 255, 0],
        "background_color": [10, 10, 10],
    }

    await progress_bar.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 9)) == (0, 255, 0)
    assert ctx.image.getpixel((0, 5)) == (0, 255, 0)
    assert ctx.image.getpixel((0, 4)) == (10, 10, 10)
    assert ctx.image.getpixel((0, 0)) == (10, 10, 10)


async def test_value_clamped_to_max(hass):
    """A value above max fills the entire bar."""
    ctx = RenderContext()
    component = {
        "type": "progress_bar",
        "position": [0, 0],
        "size": [10, 1],
        "min": 0,
        "max": 100,
        "value": 500,
        "color": [0, 255, 0],
    }

    await progress_bar.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((9, 0)) == (0, 255, 0)


async def test_color_thresholds_override_default_color(hass):
    """When color_thresholds are configured, the fill color follows the value's bracket."""
    ctx = RenderContext()
    component = {
        "type": "progress_bar",
        "position": [0, 0],
        "size": [10, 1],
        "min": 0,
        "max": 100,
        "value": 90,
        "color": [0, 255, 0],
        "color_thresholds": [
            {"value": 0, "color": [0, 255, 0]},
            {"value": 80, "color": [255, 0, 0]},
        ],
    }

    await progress_bar.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (255, 0, 0)


async def test_smooth_transition_blends_edge_pixel(hass):
    """A smooth transition blends the fractional boundary pixel instead of a hard cut."""
    ctx = RenderContext()
    component = {
        "type": "progress_bar",
        "position": [0, 0],
        "size": [10, 1],
        "min": 0,
        "max": 100,
        "value": 25,
        "color": [255, 255, 255],
        "background_color": [0, 0, 0],
        "transition": "smooth",
    }

    await progress_bar.draw(component, ctx, hass, None)

    # exact_fill = 2.5px: pixel 0-1 fully filled, pixel 2 blended, pixel 3+ background.
    assert ctx.image.getpixel((1, 0)) == (255, 255, 255)
    edge = ctx.image.getpixel((2, 0))
    assert edge not in ((255, 255, 255), (0, 0, 0))
    assert ctx.image.getpixel((3, 0)) == (0, 0, 0)
