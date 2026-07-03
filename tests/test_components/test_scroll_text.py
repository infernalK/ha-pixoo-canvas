"""Tests for the scroll_text render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import scroll_text
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_scroll_text_queues_resolved_fields(hass):
    """draw() appends a resolved entry to ctx.scroll_texts, drawing nothing into the buffer."""
    ctx = RenderContext()
    component = {
        "type": "scroll_text",
        "position": [2, 40],
        "content": "{{ 1 + 1 }} bottles",
        "color": [0, 255, 0],
        "direction": "left",
        "align": "left",
        "speed": 50,
        "width": 64,
        "divoom_font": 3,
    }

    await scroll_text.draw(component, ctx, hass, None)

    assert len(ctx.scroll_texts) == 1
    entry = ctx.scroll_texts[0]
    assert entry["text"] == "2 bottles"
    assert entry["position"] == (2, 40)
    assert entry["color"] == (0, 255, 0)
    assert entry["direction"] == 0
    assert entry["align"] == 1
    assert entry["speed"] == 50
    assert entry["width"] == 64
    assert entry["font"] == 3
    # Nothing is drawn into the pixel buffer: it's a hardware overlay, not a buffer draw.
    assert ctx.image.getpixel((2, 40)) == (0, 0, 0)


async def test_scroll_text_id_defaults_to_list_position(hass):
    """Without an explicit text_id, successive scroll_text components get 0, 1, 2..."""
    ctx = RenderContext()

    await scroll_text.draw(
        {"type": "scroll_text", "position": [0, 0], "content": "a"}, ctx, hass, None
    )
    await scroll_text.draw(
        {"type": "scroll_text", "position": [0, 10], "content": "b"}, ctx, hass, None
    )

    assert [entry["text_id"] for entry in ctx.scroll_texts] == [0, 1]


async def test_scroll_text_explicit_id_and_defaults(hass):
    """An explicit text_id is used as-is; direction/align/font/speed default sensibly."""
    ctx = RenderContext()

    await scroll_text.draw(
        {"type": "scroll_text", "position": [0, 0], "content": "hi", "text_id": 7}, ctx, hass, None
    )

    entry = ctx.scroll_texts[0]
    assert entry["text_id"] == 7
    assert entry["direction"] == 0  # left
    assert entry["align"] == 1  # left
    assert entry["font"] == 0
    assert entry["speed"] == 100


async def test_scroll_text_content_template_error_is_skipped(hass):
    """A content template that fails to render is skipped, not raised."""
    ctx = RenderContext()

    await scroll_text.draw(
        {
            "type": "scroll_text",
            "position": [0, 0],
            "content": "{{ states('sensor.does_not_exist')|int }}",
        },
        ctx,
        hass,
        None,
    )

    assert ctx.scroll_texts == []
