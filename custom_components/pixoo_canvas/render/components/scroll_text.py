"""Scroll text component: native, device-animated scrolling text overlay.

Unlike `text` (drawn into our own RGB buffer, static), this queues a
`Draw/SendHttpText` call that `engine.py` sends after the page's buffer push.
The Pixoo's own firmware animates the scroll in hardware — smoother than
anything we could do by re-pushing shifted frames ourselves, but only takes
effect while the device is showing a custom image ("drawing mode"), which a
page render already puts it in via its own SendHttpGif push right before.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

from ..colors import resolve_color

if TYPE_CHECKING:
    from ..engine import RenderContext

_LOGGER = logging.getLogger(__name__)

_DIRECTIONS = {"left": 0, "right": 1}
_ALIGNMENTS = {"left": 1, "center": 2, "right": 3}


async def draw(
    component: dict[str, Any],
    ctx: RenderContext,
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> None:
    """Resolve a scroll_text component's fields and queue it for engine.py to send."""
    content = str(component.get("content", ""))
    try:
        text = str(Template(content, hass).async_render(variables=variables))
    except TemplateError as err:
        _LOGGER.warning("Scroll text content template failed to render, skipping: %s", err)
        return

    x, y = component.get("position", [0, 0])
    color = resolve_color(component.get("color"), hass, variables, default=(255, 255, 255))
    direction = _DIRECTIONS.get(str(component.get("direction", "left")).lower(), 0)
    align = _ALIGNMENTS.get(str(component.get("align", "left")).lower(), 1)

    ctx.scroll_texts.append(
        {
            "text_id": int(component.get("text_id", len(ctx.scroll_texts))),
            "position": (int(x), int(y)),
            "text": text,
            "color": color,
            "direction": direction,
            "font": int(component.get("divoom_font", 0)),
            "width": int(component.get("width", ctx.size)),
            "speed": int(component.get("speed", 100)),
            "align": align,
        }
    )
