"""Tests for the arc render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import arc
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_filled_pie_slice_covers_swept_quadrant(hass):
    """A 0->90 (top-to-east, clockwise) filled slice covers the NE quadrant, not SW."""
    ctx = RenderContext()
    component = {
        "type": "arc",
        "center": [20, 20],
        "radius": 10,
        "start_angle": 0,
        "end_angle": 90,
        "color": [255, 0, 0],
        "filled": True,
    }

    await arc.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 12)) == (255, 0, 0)  # near top
    assert ctx.image.getpixel((26, 20)) == (255, 0, 0)  # near east
    assert ctx.image.getpixel((14, 26)) == (0, 0, 0)  # SW, outside the slice


async def test_outline_arc_leaves_center_empty(hass):
    """An outline (non-filled) arc doesn't touch the center pixel."""
    ctx = RenderContext()
    component = {
        "type": "arc",
        "center": [20, 20],
        "radius": 10,
        "start_angle": 0,
        "end_angle": 180,
        "color": [255, 255, 255],
        "filled": False,
        "thickness": 2,
    }

    await arc.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 20)) == (0, 0, 0)


async def test_color_thresholds_override_default_color(hass):
    """When color_thresholds are configured, the arc color follows the value's bracket."""
    ctx = RenderContext()
    component = {
        "type": "arc",
        "center": [20, 20],
        "radius": 10,
        "start_angle": 0,
        "end_angle": 90,
        "color": [255, 255, 255],
        "filled": True,
        "value": 90,
        "color_thresholds": [
            {"value": 0, "color": [0, 255, 0]},
            {"value": 80, "color": [255, 0, 0]},
        ],
    }

    await arc.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 12)) == (255, 0, 0)


async def test_background_color_draws_full_track_behind_the_sweep(hass):
    """background_color draws a full ring first, so the (small) sweep sits over a full track."""
    ctx = RenderContext()
    component = {
        "type": "arc",
        "center": [20, 20],
        "radius": 10,
        "start_angle": 0,
        "end_angle": 10,  # a small sweep near the top only
        "color": [255, 0, 0],
        "filled": False,
        "thickness": 2,
        "background_color": [60, 60, 60],
    }

    await arc.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((20, 10)) == (255, 0, 0)  # inside the sweep (top)
    assert ctx.image.getpixel((10, 20)) == (60, 60, 60)  # outside the sweep (west), still on the track
