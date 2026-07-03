"""Pixel-bitmap fonts ported from gickowtf/pixoo-homeassistant (MIT license).

These are true fixed-grid pixel fonts (glyphs as flat 0/1 arrays drawn pixel
by pixel), not scaled TrueType outlines. `pico_8` is the same font this
project's own pages referenced as `font: pico_8` before migrating, and it
stays both narrow and a full 5px tall at native scale — legible on a real,
diffused LED matrix in a way a small TrueType font isn't. See
render/fonts/bitmap/SOURCE.txt for provenance.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from .colors import RGB

_DATA_PATH = Path(__file__).parent / "fonts" / "bitmap" / "gickowtf_fonts.json"

_FONT_KEYS = {"pico_8": "FONT_PICO_8", "gicko": "FONT_GICKO"}
BITMAP_FONT_NAMES = tuple(_FONT_KEYS)

_fonts: dict[str, dict[str, list[int]]] | None = None


def _load_fonts() -> dict[str, dict[str, list[int]]]:
    global _fonts
    if _fonts is None:
        _fonts = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return _fonts


def _glyph(font_name: str, char: str) -> list[int] | None:
    table = _load_fonts().get(_FONT_KEYS.get(font_name, ""), {})
    # gicko has no lowercase glyphs at all (only pico_8 does); fall back to
    # the uppercase glyph before giving up on '?', since it's the same letter.
    return table.get(char) or table.get(char.upper()) or table.get("?")


def bitmap_text_size(text: str, font_name: str, scale: int = 1) -> tuple[int, int]:
    """Return the (width, height) in pixels `text` occupies at `scale`."""
    width = 0
    height = 0
    for char in text:
        glyph = _glyph(font_name, char)
        if glyph is None:
            continue
        x_size = glyph[-1]
        height = max(height, (len(glyph) - 1) // x_size)
        width += x_size + 1
    return max(0, width - 1) * scale, height * scale


def draw_bitmap_text(
    image: Image.Image,
    text: str,
    xy: tuple[int, int],
    color: RGB,
    font_name: str,
    scale: int = 1,
) -> None:
    """Draw `text` in a bitmap font at `xy`, each 'on' pixel scaled to `scale`x`scale`."""
    draw = ImageDraw.Draw(image)
    x_offset = 0
    for char in text:
        glyph = _glyph(font_name, char)
        if glyph is None:
            continue
        x_size = glyph[-1]
        for index, bit in enumerate(glyph[:-1]):
            if not bit:
                continue
            local_x = index % x_size
            local_y = index // x_size
            px = xy[0] + (x_offset + local_x) * scale
            py = xy[1] + local_y * scale
            draw.rectangle((px, py, px + scale - 1, py + scale - 1), fill=color)
        x_offset += x_size + 1
