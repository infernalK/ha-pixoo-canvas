"""Tests for the text render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import text
from custom_components.pixoo_canvas.render.engine import RenderContext


async def test_text_renders_template_content(hass):
    """The content field is rendered as a Jinja2 template before drawing."""
    ctx = RenderContext()
    component = {
        "type": "text",
        "position": [0, 0],
        "content": "{{ 1 + 1 }}",
        "color": [255, 255, 255],
    }

    await text.draw(component, ctx, hass, None)

    # Something was drawn: at least one non-black pixel exists on the buffer.
    assert any(
        ctx.image.getpixel((x, y)) != (0, 0, 0)
        for x in range(ctx.size)
        for y in range(ctx.size)
    )


async def test_text_center_alignment_shifts_left_of_position(hass):
    """Center-aligned text starts drawing to the left of its anchor x."""
    ctx_left = RenderContext()
    await text.draw(
        {"type": "text", "position": [32, 0], "content": "HELLO", "align": "left"},
        ctx_left,
        hass,
        None,
    )
    ctx_center = RenderContext()
    await text.draw(
        {"type": "text", "position": [32, 0], "content": "HELLO", "align": "center"},
        ctx_center,
        hass,
        None,
    )

    def first_lit_column(image):
        for x in range(image.size[0]):
            for y in range(image.size[1]):
                if image.getpixel((x, y)) != (0, 0, 0):
                    return x
        return None

    assert first_lit_column(ctx_center.image) < first_lit_column(ctx_left.image)


def _last_lit_column(image):
    for x in reversed(range(image.size[0])):
        for y in range(image.size[1]):
            if image.getpixel((x, y)) != (0, 0, 0):
                return x
    return None


async def test_text_font_field_selects_alternate_font(hass):
    """The optional `font` field switches to a different bundled font."""
    ctx_default = RenderContext()
    await text.draw(
        {"type": "text", "position": [0, 0], "content": "Fete du jour"},
        ctx_default,
        hass,
        None,
    )
    ctx_gicko = RenderContext()
    await text.draw(
        {
            "type": "text",
            "position": [0, 0],
            "content": "Fete du jour",
            "font": "gicko",
        },
        ctx_gicko,
        hass,
        None,
    )

    # gicko is a wider bitmap font than pico_8 (the default) at the same scale.
    assert _last_lit_column(ctx_default.image) < _last_lit_column(ctx_gicko.image)


async def test_text_unknown_font_falls_back_to_default(hass):
    """An unrecognized `font` name falls back to the bitmap default rather than raising."""
    ctx_default = RenderContext()
    await text.draw(
        {"type": "text", "position": [0, 0], "content": "Fete du jour"},
        ctx_default,
        hass,
        None,
    )
    ctx_unknown = RenderContext()
    await text.draw(
        {
            "type": "text",
            "position": [0, 0],
            "content": "Fete du jour",
            "font": "does-not-exist",
        },
        ctx_unknown,
        hass,
        None,
    )

    assert _last_lit_column(ctx_default.image) == _last_lit_column(ctx_unknown.image)


async def test_text_bitmap_font_size_acts_as_integer_scale(hass):
    """For bitmap fonts, `font_size` is an integer scale factor, not a point size."""
    ctx_scale1 = RenderContext()
    await text.draw(
        {"type": "text", "position": [0, 0], "content": "SPA", "font_size": 1},
        ctx_scale1,
        hass,
        None,
    )
    ctx_scale2 = RenderContext()
    await text.draw(
        {"type": "text", "position": [0, 0], "content": "SPA", "font_size": 2},
        ctx_scale2,
        hass,
        None,
    )

    assert _last_lit_column(ctx_scale2.image) > _last_lit_column(ctx_scale1.image)


async def test_text_content_template_error_is_skipped(hass):
    """A content template that fails to render (e.g. |int on an unavailable sensor) draws nothing."""
    ctx = RenderContext()
    component = {
        "type": "text",
        "position": [0, 0],
        "content": "{{ states('sensor.does_not_exist')|int }}",
        "color": [255, 255, 255],
    }

    await text.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)


async def test_text_scroll_queues_resolved_fields_instead_of_drawing(hass):
    """`scroll: true` appends a resolved entry to ctx.scroll_texts, drawing nothing into the buffer."""
    ctx = RenderContext()
    component = {
        "type": "text",
        "position": [2, 40],
        "content": "{{ 1 + 1 }} bottles",
        "color": [0, 255, 0],
        "scroll": True,
        "scroll_direction": "left",
        "align": "left",
        "scroll_speed": 50,
        "text_width": 64,
        "divoom_font": 3,
    }

    await text.draw(component, ctx, hass, None)

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


async def test_text_scroll_id_defaults_to_list_position(hass):
    """Without an explicit text_id, successive scrolling texts get 0, 1, 2..."""
    ctx = RenderContext()

    await text.draw(
        {"type": "text", "position": [0, 0], "content": "a", "scroll": True}, ctx, hass, None
    )
    await text.draw(
        {"type": "text", "position": [0, 10], "content": "b", "scroll": True}, ctx, hass, None
    )

    assert [entry["text_id"] for entry in ctx.scroll_texts] == [0, 1]


async def test_text_scroll_explicit_id_and_defaults(hass):
    """An explicit text_id is used as-is; direction/align/font/speed default sensibly."""
    ctx = RenderContext()

    await text.draw(
        {"type": "text", "position": [0, 0], "content": "hi", "scroll": True, "text_id": 7},
        ctx,
        hass,
        None,
    )

    entry = ctx.scroll_texts[0]
    assert entry["text_id"] == 7
    assert entry["direction"] == 0  # left
    assert entry["align"] == 1  # left
    assert entry["font"] == 0
    assert entry["speed"] == 100


async def test_text_scroll_content_template_error_is_skipped(hass):
    """A content template that fails to render is skipped, not raised."""
    ctx = RenderContext()

    await text.draw(
        {
            "type": "text",
            "position": [0, 0],
            "content": "{{ states('sensor.does_not_exist')|int }}",
            "scroll": True,
        },
        ctx,
        hass,
        None,
    )

    assert ctx.scroll_texts == []
