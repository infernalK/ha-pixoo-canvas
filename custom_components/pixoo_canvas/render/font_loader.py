"""Loads and caches the bundled bitmap-style TrueType font."""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

FONTS_DIR = Path(__file__).parent / "fonts"
DEFAULT_FONT_PATH = FONTS_DIR / "PressStart2P-Regular.ttf"
DEFAULT_FONT_SIZE = 6

_cache: dict[int, ImageFont.FreeTypeFont] = {}


def load_font(size: int = DEFAULT_FONT_SIZE) -> ImageFont.FreeTypeFont:
    """Load (and cache) the bundled font at a given pixel size."""
    font = _cache.get(size)
    if font is None:
        font = ImageFont.truetype(str(DEFAULT_FONT_PATH), size)
        _cache[size] = font
    return font
