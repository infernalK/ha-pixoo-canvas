"""Page composition: buffer + draw primitives, templatable expansion, push to device."""

from __future__ import annotations

import logging
from typing import Any

from PIL import Image, ImageDraw

from homeassistant.core import HomeAssistant

from ..api import PixooClient
from ..const import PIC_WIDTH
from .components import image as image_component
from .components import rectangle as rectangle_component
from .components import templatable as templatable_component
from .components import text as text_component

_LOGGER = logging.getLogger(__name__)

_COMPONENT_DRAWERS = {
    "text": text_component.draw,
    "rectangle": rectangle_component.draw,
    "image": image_component.draw,
}


class RenderContext:
    """RGB 64x64 drawing buffer for a single Pixoo page."""

    def __init__(self, size: int = PIC_WIDTH) -> None:
        self.size = size
        self.image = Image.new("RGB", (size, size), (0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def to_rgb_bytes(self) -> bytes:
        """Return the raw RGB888 buffer bytes, row-major, as expected by SendHttpGif."""
        return self.image.tobytes()


async def render_page(
    hass: HomeAssistant,
    client: PixooClient,
    components: list[dict[str, Any]],
    variables: dict[str, Any] | None = None,
) -> None:
    """Compose a page's components onto a buffer and push it to the device."""
    ctx = RenderContext()
    pending = list(components)
    index = 0
    while index < len(pending):
        component = pending[index]
        comp_type = component.get("type")

        if comp_type == "templatable":
            expanded = await templatable_component.expand(component, hass, variables)
            pending[index + 1 : index + 1] = expanded
            index += 1
            continue

        drawer = _COMPONENT_DRAWERS.get(comp_type)
        if drawer is None:
            _LOGGER.warning("Unknown component type %s, skipping", comp_type)
            index += 1
            continue

        await drawer(component, ctx, hass, variables)
        index += 1

    await client.send_gif(ctx.size, ctx.to_rgb_bytes())
