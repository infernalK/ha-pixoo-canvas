"""Loads and caches the bundled bitmap-style TrueType fonts."""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

FONTS_DIR = Path(__file__).parent / "fonts"

# These are the scalable TrueType alternatives to the default bitmap font
# (see components/text.py, DEFAULT_FONT_NAME = "pico_8"). Press Start 2P is
# this module's own fallback for an unrecognized TTF font name: it renders
# taller (7px at size 6) than Silkscreen (4px at the same size), and glyph
# height is what makes text legible on a real, diffused LED matrix.
FONT_PATHS: dict[str, Path] = {
    "press_start_2p": FONTS_DIR / "press_start_2p" / "PressStart2P-Regular.ttf",
    "silkscreen": FONTS_DIR / "silkscreen" / "Silkscreen-Regular.ttf",
    "silkscreen_bold": FONTS_DIR / "silkscreen" / "Silkscreen-Bold.ttf",
}

DEFAULT_FONT_NAME = "press_start_2p"
DEFAULT_FONT_SIZE = 6

_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def load_font(
    size: int = DEFAULT_FONT_SIZE, font: str = DEFAULT_FONT_NAME
) -> ImageFont.FreeTypeFont:
    """Load (and cache) a bundled font by name at a given pixel size.

    Falls back to the default font for an unknown name rather than raising,
    consistent with the rest of the render engine's "skip/fallback, don't
    crash the page" philosophy.
    """
    name = font if font in FONT_PATHS else DEFAULT_FONT_NAME
    key = (name, size)
    cached = _cache.get(key)
    if cached is None:
        cached = ImageFont.truetype(str(FONT_PATHS[name]), size)
        _cache[key] = cached
    return cached
