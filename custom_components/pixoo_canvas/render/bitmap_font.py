"""Pixel-bitmap fonts, ported from gickowtf/pixoo-homeassistant and trip5/Matrix-Fonts.

These are true fixed-grid pixel fonts (glyphs as flat 0/1 arrays drawn pixel
by pixel), not scaled TrueType outlines - legible on a real, diffused LED
matrix in a way a small TrueType font isn't. `pico_8` is the same font this
project's own pages referenced as `font: pico_8` before migrating. See
render/fonts/bitmap/SOURCE.txt and render/fonts/matrix/SOURCE.txt for
provenance of each font.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from .colors import RGB

_FONTS_DIR = Path(__file__).parent / "fonts"

# Each bundled font: which JSON file its glyph table lives in, and the key
# under which that table is stored (a single JSON file can hold more than
# one font, as gickowtf_fonts.json does).
_FONT_SOURCES: dict[str, tuple[Path, str]] = {
    "pico_8": (_FONTS_DIR / "bitmap" / "gickowtf_fonts.json", "FONT_PICO_8"),
    "gicko": (_FONTS_DIR / "bitmap" / "gickowtf_fonts.json", "FONT_GICKO"),
    "matrix_chunky_6": (_FONTS_DIR / "matrix" / "matrix_fonts.json", "MatrixChunky6"),
    "matrix_chunky_8": (_FONTS_DIR / "matrix" / "matrix_fonts.json", "MatrixChunky8"),
}
BITMAP_FONT_NAMES = tuple(_FONT_SOURCES)

_json_cache: dict[Path, dict[str, dict[str, list[int]]]] = {}


def _load_json(path: Path) -> dict[str, dict[str, list[int]]]:
    cached = _json_cache.get(path)
    if cached is None:
        cached = json.loads(path.read_text(encoding="utf-8"))
        _json_cache[path] = cached
    return cached


def _glyph(font_name: str, char: str) -> list[int] | None:
    source = _FONT_SOURCES.get(font_name)
    table = _load_json(source[0]).get(source[1], {}) if source else {}
    # gicko has no lowercase glyphs at all; fall back to the uppercase glyph
    # before giving up on '?', since it's the same letter.
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
