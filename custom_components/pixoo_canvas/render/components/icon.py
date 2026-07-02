"""Icon component: MDI icon fetched as SVG, tinted, rasterized, and pasted."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import TYPE_CHECKING, Any

import cairosvg
from PIL import Image

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..colors import RGB, resolve_color
from ..values import resolve_threshold_color, resolve_value

if TYPE_CHECKING:
    from ..engine import RenderContext

_LOGGER = logging.getLogger(__name__)

_MDI_SVG_URL = "https://cdn.jsdelivr.net/npm/@mdi/svg@latest/svg/{name}.svg"
_DEFAULT_SIZE = 16


def _tint_svg(svg_text: str, color: RGB) -> str:
    """Force the icon's fill color by setting it on the root <svg> element."""
    hex_color = "#{:02x}{:02x}{:02x}".format(*color)
    return re.sub(r"<svg ", f'<svg fill="{hex_color}" ', svg_text, count=1)


def _rasterize(svg_text: str, size: int) -> Image.Image:
    """Render tinted SVG markup to an RGBA raster of `size`x`size`."""
    png_bytes = cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"), output_width=size, output_height=size
    )
    return Image.open(BytesIO(png_bytes)).convert("RGBA")


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Fetch an MDI icon, tint it per `color`/`color_thresholds`, and paste it."""
    icon = str(component.get("icon", ""))
    name = icon.split(":", 1)[-1]
    if not name:
        _LOGGER.warning("Icon component missing 'icon', skipping")
        return

    default_color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    thresholds = component.get("color_thresholds")
    if thresholds:
        value = resolve_value(component.get("value"), hass, variables)
        color = resolve_threshold_color(value, thresholds, hass, variables, default_color)
    else:
        color = default_color

    session = async_get_clientsession(hass)
    async with session.get(_MDI_SVG_URL.format(name=name)) as resp:
        resp.raise_for_status()
        svg_text = await resp.text()

    size = int(component.get("size", _DEFAULT_SIZE))
    tinted = _tint_svg(svg_text, color)
    icon_img = await hass.async_add_executor_job(_rasterize, tinted, size)

    x, y = component.get("position", [0, 0])
    ctx.image.paste(icon_img, (int(x), int(y)), icon_img)
