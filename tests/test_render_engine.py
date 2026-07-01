"""Tests for the render engine's page composition and push."""

from __future__ import annotations

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.pixoo_canvas.api import PixooClient
from custom_components.pixoo_canvas.render.engine import render_page

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


class _FakeClient:
    """Records send_gif calls without touching the network."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, bytes]] = []

    async def send_gif(self, width: int, rgb_bytes: bytes) -> None:
        self.calls.append((width, rgb_bytes))


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
    """End-to-end: render_page drives the real PixooClient.send_gif -> HTTP POST."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await render_page(hass, client, [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}])

    assert len(aioclient_mock.mock_calls) == 1
