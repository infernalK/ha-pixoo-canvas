"""Tests for the image render component."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from custom_components.pixoo_canvas.render.components import image
from custom_components.pixoo_canvas.render.engine import RenderContext

URL = "http://example.com/pic.png"


def _png_bytes(color: tuple[int, int, int], size: tuple[int, int] = (4, 4)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


async def test_image_from_url(hass, aioclient_mock):
    """An image_url is fetched and pasted onto the buffer."""
    aioclient_mock.get(URL, content=_png_bytes((0, 0, 255)))
    ctx = RenderContext()

    await image.draw({"type": "image", "position": [0, 0], "image_url": URL}, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (0, 0, 255)


async def test_image_from_path(hass, tmp_path):
    """An image_path is read from disk and pasted onto the buffer."""
    path = tmp_path / "pic.png"
    path.write_bytes(_png_bytes((255, 0, 0)))
    ctx = RenderContext()

    await image.draw(
        {"type": "image", "position": [10, 10], "image_path": str(path)}, ctx, hass, None
    )

    assert ctx.image.getpixel((10, 10)) == (255, 0, 0)


async def test_image_missing_source_is_noop(hass):
    """No image_url/image_path leaves the buffer untouched."""
    ctx = RenderContext()

    await image.draw({"type": "image", "position": [0, 0]}, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)
