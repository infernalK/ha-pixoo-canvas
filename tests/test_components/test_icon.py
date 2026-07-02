"""Tests for the icon render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import icon
from custom_components.pixoo_canvas.render.engine import RenderContext

_SQUARE_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path d="M0 0h24v24H0z"/></svg>'
)


def _mock_icon(aioclient_mock, name: str, svg: str = _SQUARE_ICON_SVG) -> None:
    url = f"https://cdn.jsdelivr.net/npm/@mdi/svg@latest/svg/{name}.svg"
    aioclient_mock.get(url, content=svg.encode("utf-8"))


async def test_icon_is_tinted_and_pasted(hass, aioclient_mock):
    """A fetched MDI icon is tinted to its color and pasted at its position."""
    _mock_icon(aioclient_mock, "thermometer")
    ctx = RenderContext()
    component = {
        "type": "icon",
        "icon": "mdi:thermometer",
        "position": [4, 4],
        "size": 8,
        "color": [255, 0, 0],
    }

    await icon.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((8, 8)) == (255, 0, 0)
    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)


async def test_icon_strips_mdi_prefix(hass, aioclient_mock):
    """The 'mdi:' prefix is stripped before resolving the icon name."""
    _mock_icon(aioclient_mock, "battery")
    ctx = RenderContext()

    await icon.draw(
        {
            "type": "icon",
            "icon": "mdi:battery",
            "position": [0, 0],
            "size": 4,
            "color": [0, 255, 0],
        },
        ctx,
        hass,
        None,
    )

    assert ctx.image.getpixel((1, 1)) == (0, 255, 0)


async def test_icon_color_thresholds_pick_bracket_color(hass, aioclient_mock):
    """color_thresholds select the tint based on the resolved value."""
    _mock_icon(aioclient_mock, "battery")
    ctx = RenderContext()
    component = {
        "type": "icon",
        "icon": "mdi:battery",
        "position": [0, 0],
        "size": 4,
        "color": [0, 255, 0],
        "value": 15,
        "color_thresholds": [
            {"value": 0, "color": [255, 0, 0]},
            {"value": 50, "color": [0, 255, 0]},
        ],
    }

    await icon.draw(component, ctx, hass, None)

    assert ctx.image.getpixel((1, 1)) == (255, 0, 0)


async def test_icon_missing_name_is_noop(hass):
    """No 'icon' field leaves the buffer untouched."""
    ctx = RenderContext()

    await icon.draw({"type": "icon", "position": [0, 0]}, ctx, hass, None)

    assert ctx.image.getpixel((0, 0)) == (0, 0, 0)
