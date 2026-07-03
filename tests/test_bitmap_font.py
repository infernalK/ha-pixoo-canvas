"""Tests for the gickowtf-derived pixel-bitmap fonts (pico_8, gicko)."""

from __future__ import annotations

from PIL import Image

from custom_components.pixoo_canvas.render.bitmap_font import (
    BITMAP_FONT_NAMES,
    bitmap_text_size,
    draw_bitmap_text,
)


def test_bitmap_font_names_include_pico_8_and_gicko():
    """Both ported gickowtf font tables are available."""
    assert set(BITMAP_FONT_NAMES) == {"pico_8", "gicko"}


def test_bitmap_text_size_scales_linearly():
    """Doubling the scale doubles both the measured width and height."""
    width1, height1 = bitmap_text_size("SPA", "pico_8", scale=1)
    width2, height2 = bitmap_text_size("SPA", "pico_8", scale=2)

    assert width2 == width1 * 2
    assert height2 == height1 * 2
    assert width1 > 0
    assert height1 > 0


def test_bitmap_text_size_unknown_char_falls_back_to_placeholder():
    """An unsupported character still contributes width via the '?' glyph."""
    width_known, _ = bitmap_text_size("A", "pico_8")
    width_unknown, _ = bitmap_text_size("\N{GREEK SMALL LETTER ALPHA}", "pico_8")

    assert width_unknown == width_known  # both fall back to the same '?' glyph


def test_bitmap_text_size_lowercase_falls_back_to_uppercase_glyph():
    """gicko has no lowercase glyphs; lowercase should reuse the uppercase one, not '?'."""
    width_lower, _ = bitmap_text_size("salut", "gicko")
    width_upper, _ = bitmap_text_size("SALUT", "gicko")
    width_placeholder, _ = bitmap_text_size("?????", "gicko")

    assert width_lower == width_upper
    assert width_lower != width_placeholder


def test_draw_bitmap_text_paints_pixels_at_native_scale():
    """At scale 1, pico_8 draws individual pixels within the glyph's cell."""
    image = Image.new("RGB", (64, 64), (0, 0, 0))

    draw_bitmap_text(image, "0", (0, 0), (255, 0, 0), "pico_8", scale=1)

    lit = [(x, y) for x in range(8) for y in range(8) if image.getpixel((x, y)) == (255, 0, 0)]
    assert lit  # something was drawn
    # pico_8 digits are a 3-wide grid; nothing should be lit past column 3.
    assert all(x < 3 for x, _y in lit)


def test_draw_bitmap_text_scale_2_paints_2x2_blocks():
    """At scale 2, each 'on' pixel becomes a 2x2 block."""
    image = Image.new("RGB", (64, 64), (0, 0, 0))

    draw_bitmap_text(image, "0", (0, 0), (255, 0, 0), "pico_8", scale=2)

    # The top-left corner of pico_8's '0' is lit; its 2x scaled block should
    # cover (0,0)-(1,1).
    assert image.getpixel((0, 0)) == (255, 0, 0)
    assert image.getpixel((1, 1)) == (255, 0, 0)
