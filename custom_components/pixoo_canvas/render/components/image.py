"""Image component: static image or first frame of an animated GIF."""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from ..engine import RenderContext

_LOGGER = logging.getLogger(__name__)


def _decode_first_frame(raw: bytes) -> Image.Image:
    """Decode image bytes, keeping only the first frame (Phase 3 renders static pages)."""
    img = Image.open(BytesIO(raw))
    img.seek(0)
    return img.convert("RGB")


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Fetch/open an image and paste it onto the buffer at its position."""
    image_url = component.get("image_url")
    image_path = component.get("image_path")

    if image_url:
        session = async_get_clientsession(hass)
        async with session.get(image_url) as resp:
            resp.raise_for_status()
            raw = await resp.read()
    elif image_path:
        raw = await hass.async_add_executor_job(Path(image_path).read_bytes)
    else:
        _LOGGER.warning("Image component missing image_url/image_path, skipping")
        return

    img = await hass.async_add_executor_job(_decode_first_frame, raw)
    x, y = component.get("position", [0, 0])
    ctx.image.paste(img, (int(x), int(y)))
