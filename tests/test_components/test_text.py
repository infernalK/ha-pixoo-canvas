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


async def test_text_font_field_selects_alternate_font(hass):
    """The optional `font` field switches to a different bundled font."""

    def last_lit_column(image):
        for x in reversed(range(image.size[0])):
            for y in range(image.size[1]):
                if image.getpixel((x, y)) != (0, 0, 0):
                    return x
        return None

    ctx_default = RenderContext()
    await text.draw(
        {"type": "text", "position": [0, 0], "content": "Fete du jour"},
        ctx_default,
        hass,
        None,
    )
    ctx_press_start = RenderContext()
    await text.draw(
        {
            "type": "text",
            "position": [0, 0],
            "content": "Fete du jour",
            "font": "press_start_2p",
        },
        ctx_press_start,
        hass,
        None,
    )

    # Silkscreen (the default) is narrower than Press Start 2P at the same size.
    assert last_lit_column(ctx_default.image) < last_lit_column(ctx_press_start.image)
