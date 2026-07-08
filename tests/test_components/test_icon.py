"""Tests for the icon render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import icon
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_icon_is_tinted_and_drawn(hass):
    """A known MDI icon is drawn in its resolved color at its position."""
    ctx = RenderContext()
    component = {
        "type": "icon",
        "icon": "mdi:thermometer",
        "position": [4, 4],
        "size": 16,
        "color": [255, 0, 0],
    }

    await icon.draw(component, ctx, hass, None)

    assert any(
        ctx.image.getpixel((x, y)) == (255, 0, 0)
        for x in range(4, 24)
        for y in range(4, 24)
    )
    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)


async def test_icon_strips_mdi_prefix(hass):
    """The 'mdi:' prefix is stripped before resolving the icon name."""
    ctx = RenderContext()

    await icon.draw(
        {
            "type": "icon",
            "icon": "mdi:battery",
            "position": [0, 0],
            "size": 16,
            "color": [0, 255, 0],
        },
        ctx,
        hass,
        None,
    )

    assert any(
        ctx.image.getpixel((x, y)) == (0, 255, 0)
        for x in range(16)
        for y in range(16)
    )


async def test_icon_color_thresholds_pick_bracket_color(hass):
    """color_thresholds select the tint based on the resolved value."""
    ctx = RenderContext()
    component = {
        "type": "icon",
        "icon": "mdi:battery",
        "position": [0, 0],
        "size": 16,
        "color": [0, 255, 0],
        "value": 15,
        "color_thresholds": [
            {"value": 0, "color": [255, 0, 0]},
            {"value": 50, "color": [0, 255, 0]},
        ],
    }

    await icon.draw(component, ctx, hass, None)

    assert any(
        ctx.image.getpixel((x, y)) == (255, 0, 0) for x in range(16) for y in range(16)
    )
    assert not any(
        ctx.image.getpixel((x, y)) == (0, 255, 0) for x in range(16) for y in range(16)
    )


async def test_icon_name_supports_templates(hass):
    """A Jinja template in 'icon' is rendered before resolving the glyph."""
    ctx = RenderContext()

    await icon.draw(
        {
            "type": "icon",
            "icon": "{{ 'mdi:battery' }}",
            "position": [0, 0],
            "size": 16,
            "color": [0, 255, 0],
        },
        ctx,
        hass,
        None,
    )

    assert any(
        ctx.image.getpixel((x, y)) == (0, 255, 0) for x in range(16) for y in range(16)
    )


async def test_icon_missing_name_is_noop(hass):
    """No 'icon' field leaves the buffer untouched."""
    ctx = RenderContext()

    await icon.draw({"type": "icon", "position": [0, 0]}, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)


async def test_icon_unknown_name_is_noop(hass):
    """An icon name absent from the bundled font's codepoint table is skipped."""
    ctx = RenderContext()

    await icon.draw(
        {"type": "icon", "icon": "mdi:not-a-real-icon-name", "position": [0, 0]},
        ctx,
        hass,
        None,
    )

    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)
