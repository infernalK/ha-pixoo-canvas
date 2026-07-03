"""Tests for the render engine's page composition and push.

Batching, clearing stale scroll_text, and the settle delay are all
PixooClient.send_page's responsibility now (see test_api.py) - these tests
only cover what render_page itself does: composing the buffer and building
the scroll_texts list (with hex colors) passed to send_page().
"""

from __future__ import annotations

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.pixoo_canvas.api import PixooClient
from custom_components.pixoo_canvas.render.engine import render_page

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


class _FakeClient:
    """Records send_page calls without touching the network."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes, list[dict] | None]] = []

    async def send_page(self, width, rgb_bytes, scroll_texts=None) -> None:
        self.calls.append((width, rgb_bytes, scroll_texts))


async def test_render_page_pushes_once_with_full_buffer(hass):
    """A page with one full-screen rectangle pushes a single, correctly sized buffer."""
    client = _FakeClient()
    components = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": [0, 255, 0]}
    ]

    await render_page(hass, client, components)

    assert len(client.calls) == 1
    width, rgb_bytes, scroll_texts = client.calls[0]
    assert width == 64
    assert len(rgb_bytes) == 64 * 64 * 3
    assert rgb_bytes[:3] == bytes([0, 255, 0])
    assert scroll_texts == []


async def test_render_page_skips_unknown_component_type(hass):
    """Unknown component types are skipped rather than raising."""
    client = _FakeClient()

    await render_page(hass, client, [{"type": "does_not_exist"}])

    assert len(client.calls) == 1


async def test_render_page_skips_component_that_raises(hass, monkeypatch):
    """A component whose drawer raises is logged and skipped, not fatal to the page.

    Regression test: an `image` component with an unreachable image_url (e.g.
    during an internet outage, for a URL off the local network) used to raise
    and abort the whole page - now every component's failure is contained, so
    the rest of the page still renders and gets pushed.
    """
    from custom_components.pixoo_canvas.render.components import rectangle as rectangle_component

    async def _boom(component, ctx, hass, variables):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "custom_components.pixoo_canvas.render.engine._COMPONENT_DRAWERS",
        {"rectangle": rectangle_component.draw, "image": _boom},
    )
    client = _FakeClient()
    components = [
        {"type": "image", "image_url": "http://example.com/broken.png", "position": [0, 0]},
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": [0, 255, 0]},
    ]

    await render_page(hass, client, components)

    assert len(client.calls) == 1
    _, rgb_bytes, _ = client.calls[0]
    assert rgb_bytes[:3] == bytes([0, 255, 0])


async def test_render_page_expands_templatable_components(hass):
    """A templatable component's rendered list is spliced in and drawn."""
    client = _FakeClient()
    components = [
        {
            "type": "templatable",
            "template": (
                "{{ [{'type': 'rectangle', 'position': [0, 0], 'size': [64, 64], "
                "'color': [255, 0, 0]}] }}"
            ),
        }
    ]

    await render_page(hass, client, components)

    _, rgb_bytes, _ = client.calls[0]
    assert rgb_bytes[:3] == bytes([255, 0, 0])


async def test_render_page_pushed_via_real_client(hass, aioclient_mock):
    """End-to-end: render_page drives the real PixooClient.send_page -> one batched POST."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await render_page(hass, client, [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}])

    # ClearHttpText + SendHttpGif batched into a single Draw/CommandList request.
    assert len(aioclient_mock.mock_calls) == 1


async def test_render_page_builds_scroll_text_with_hex_color(hass):
    """scroll_text components are passed to send_page with an RGB->hex converted color."""
    client = _FakeClient()
    components = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": [0, 0, 0]},
        {
            "type": "scroll_text",
            "position": [0, 40],
            "content": "hello",
            "color": [255, 255, 0],
            "direction": "right",
            "align": "center",
        },
    ]

    await render_page(hass, client, components)

    assert len(client.calls) == 1  # exactly one send_page call, same as without scroll_text
    _, _, scroll_texts = client.calls[0]
    assert len(scroll_texts) == 1
    entry = scroll_texts[0]
    assert entry["text"] == "hello"
    assert entry["position"] == (0, 40)
    assert entry["color"] == "#FFFF00"
    assert entry["direction"] == 1  # right
    assert entry["align"] == 2  # center
    assert entry["text_id"] == 0
