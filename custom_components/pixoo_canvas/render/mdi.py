"""Resolves MDI icon names to glyphs of the bundled webfont, offline.

No native SVG library, no network fetch: the same tinting/rasterization
concerns that broke `cairosvg` (missing system libcairo) and `resvg_py`
(unreachable HA musllinux wheel mirror on HAOS ARM) don't apply here, since
this only uses Pillow (already a proven dependency) to draw a font glyph,
exactly like the `text` component does.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

_MDI_DIR = Path(__file__).parent / "fonts" / "mdi"
_FONT_PATH = _MDI_DIR / "materialdesignicons-webfont.ttf"
_CODEPOINTS_PATH = _MDI_DIR / "codepoints.json"

_codepoints: dict[str, str] | None = None
_font_cache: dict[int, ImageFont.FreeTypeFont] = {}


def _load_codepoints() -> dict[str, str]:
    global _codepoints
    if _codepoints is None:
        _codepoints = json.loads(_CODEPOINTS_PATH.read_text(encoding="utf-8"))
    return _codepoints


def resolve_glyph(name: str) -> str | None:
    """Return the single-character glyph for an MDI icon name, or None if unknown."""
    codepoint = _load_codepoints().get(name)
    if codepoint is None:
        return None
    return chr(int(codepoint, 16))


def load_icon_font(size: int) -> ImageFont.FreeTypeFont:
    """Load (and cache) the bundled MDI webfont at a given pixel size."""
    font = _font_cache.get(size)
    if font is None:
        font = ImageFont.truetype(str(_FONT_PATH), size)
        _font_cache[size] = font
    return font
