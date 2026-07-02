"""Tests for the bundled font loader/registry."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.font_loader import (
    DEFAULT_FONT_NAME,
    load_font,
)


def test_load_font_default_is_silkscreen():
    """The default font is Silkscreen, chosen for its narrower glyphs."""
    assert DEFAULT_FONT_NAME == "silkscreen"
    load_font()  # does not raise


def test_load_font_known_alternate_font():
    """press_start_2p is available as an explicit alternate font."""
    load_font(size=8, font="press_start_2p")  # does not raise


def test_load_font_unknown_name_falls_back_to_default():
    """An unrecognized font name falls back to the default rather than raising."""
    fallback = load_font(size=6, font="does-not-exist")
    default = load_font(size=6, font=DEFAULT_FONT_NAME)

    assert fallback is default


def test_load_font_caches_by_name_and_size():
    """Repeated calls with the same name/size return the same cached object."""
    first = load_font(size=7, font="silkscreen")
    second = load_font(size=7, font="silkscreen")

    assert first is second
