"""Tests for the render engine's page composition and push."""

from __future__ import annotations

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.pixoo_canvas.api import PixooClient
from custom_components.pixoo_canvas.render.engine import render_page

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


class _FakeClient:
    """Records send_gif/send_text_animation/clear_text_overlays calls, no network."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes]] = []
        self.text_calls: list[dict] = []
        self.clear_text_calls = 0

    async def send_gif(self, width: int, rgb_bytes: bytes) -> None:
        self.calls.append((width, rgb_bytes))

    async def send_text_animation(self, text_id, position, text, color, **kwargs):
        self.text_calls.append({"text_id": text_id, "position": position, "text": text, "color": color, **kwargs})

    async def clear_text_overlays(self) -> None:
        self.clear_text_calls += 1


async def test_render_page_always_clears_text_overlays_first(hass):
    """Every render clears leftover scroll_text overlays, even on a page with none.

    Divoom's firmware doesn't clear a previous page's scrolling text on its
    own when a new buffer is pushed, so a page without scroll_text could
    otherwise end up with a stale one stuck on top of it.
    """
    client = _FakeClient()

    await render_page(hass, client, [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}])

    assert client.clear_text_calls == 1


async def test_render_page_pushes_once_with_full_buffer(hass):
    """A page with one full-screen rectangle pushes a single, correctly sized buffer."""
    client = _FakeClient()
    components = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": [0, 255, 0]}
    ]

    await render_page(hass, client, components)

    assert len(client.calls) == 1
    width, rgb_bytes = client.calls[0]
    assert width == 64
    assert len(rgb_bytes) == 64 * 64 * 3
    assert rgb_bytes[:3] == bytes([0, 255, 0])


async def test_render_page_skips_unknown_component_type(hass):
    """Unknown component types are skipped rather than raising."""
    client = _FakeClient()

    await render_page(hass, client, [{"type": "does_not_exist"}])

    assert len(client.calls) == 1


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

    _, rgb_bytes = client.calls[0]
    assert rgb_bytes[:3] == bytes([255, 0, 0])


async def test_render_page_pushed_via_real_client(hass, aioclient_mock):
    """End-to-end: render_page drives the real PixooClient, clearing text then pushing the gif."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await render_page(hass, client, [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}])

    # ClearHttpText (always, to drop any stale scroll_text) + SendHttpGif.
    assert len(aioclient_mock.mock_calls) == 2


async def test_render_page_sends_scroll_text_after_the_buffer_push(hass):
    """scroll_text components are sent as SendHttpText calls after the main gif push."""
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

    assert client.clear_text_calls == 1
    assert len(client.calls) == 1  # exactly one buffer push, same as without scroll_text
    assert len(client.text_calls) == 1
    call = client.text_calls[0]
    assert call["text"] == "hello"
    assert call["position"] == (0, 40)
    assert call["color"] == "#FFFF00"
    assert call["direction"] == 1  # right
    assert call["align"] == 2  # center
    assert call["text_id"] == 0
