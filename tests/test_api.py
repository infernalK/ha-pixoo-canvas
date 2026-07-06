"""Tests for PixooClient: batching, text-overlay clearing, and the settle delay."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.pixoo_canvas.api import PixooClient
from custom_components.pixoo_canvas.const import SCROLL_TEXT_SETTLE_DELAY

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


async def test_send_page_batches_clear_and_gif_into_one_request(hass, aioclient_mock):
    """ClearHttpText + SendHttpGif are sent as a single Draw/CommandList request."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.send_page(64, b"\x00" * (64 * 64 * 3))

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload["Command"] == "Draw/CommandList"
    commands = payload["CommandList"]
    assert [c["Command"] for c in commands] == ["Draw/ClearHttpText", "Draw/SendHttpGif"]


async def test_send_page_always_clears_even_without_scroll_text(hass, aioclient_mock):
    """A page with no scroll_text still clears any stale overlay from a previous page."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.send_page(64, b"\x00" * (64 * 64 * 3), scroll_texts=None)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload["CommandList"][0]["Command"] == "Draw/ClearHttpText"


async def test_send_page_sends_scroll_texts_as_second_batched_request(hass, aioclient_mock):
    """scroll_texts are sent as a second Draw/CommandList call, one entry per text."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    scroll_texts = [
        {
            "text_id": 0,
            "position": (0, 40),
            "text": "hello",
            "color": "#FFFF00",
            "direction": 0,
            "font": 0,
            "width": 64,
            "speed": 100,
            "align": 1,
        },
        {
            "text_id": 1,
            "position": (0, 50),
            "text": "world",
            "color": "#00FF00",
            "direction": 1,
            "font": 2,
            "width": 64,
            "speed": 50,
            "align": 2,
        },
    ]

    await client.send_page(64, b"\x00" * (64 * 64 * 3), scroll_texts)

    assert len(aioclient_mock.mock_calls) == 2
    text_payload = aioclient_mock.mock_calls[1][2]
    assert text_payload["Command"] == "Draw/CommandList"
    commands = text_payload["CommandList"]
    assert len(commands) == 2
    assert commands[0]["TextId"] == 0
    assert commands[0]["TextString"] == "hello"
    assert commands[0]["color"] == "#FFFF00"
    assert commands[1]["TextId"] == 1
    assert commands[1]["TextString"] == "world"


async def test_send_page_waits_before_scroll_text_batch(hass, aioclient_mock):
    """A settle delay separates the clear+gif batch from the scroll_text batch."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    scroll_texts = [
        {
            "text_id": 0,
            "position": (0, 0),
            "text": "hi",
            "color": "#FFFFFF",
            "direction": 0,
            "font": 0,
            "width": 64,
            "speed": 100,
            "align": 1,
        }
    ]

    with patch("custom_components.pixoo_canvas.api.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        await client.send_page(64, b"\x00" * (64 * 64 * 3), scroll_texts)

    mock_sleep.assert_awaited_once_with(SCROLL_TEXT_SETTLE_DELAY)


async def test_send_page_no_delay_without_scroll_text(hass, aioclient_mock):
    """No settle delay (and no second request) for a page without scroll_text."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    with patch("custom_components.pixoo_canvas.api.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        await client.send_page(64, b"\x00" * (64 * 64 * 3))

    mock_sleep.assert_not_awaited()
    assert len(aioclient_mock.mock_calls) == 1


async def test_set_clock_sends_clock_select_id(hass, aioclient_mock):
    """set_clock posts Channel/SetClockSelectId with the given ClockId."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_clock(182)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Channel/SetClockSelectId", "ClockId": 182}


async def test_set_custom_channel_sends_custom_page_index(hass, aioclient_mock):
    """set_custom_channel posts Channel/SetCustomPageIndex with the given index."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_custom_channel(1)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Channel/SetCustomPageIndex", "CustomPageIndex": 1}


async def test_set_visualizer_sends_eq_position(hass, aioclient_mock):
    """set_visualizer posts Channel/SetEqPosition with the given position."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_visualizer(2)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Channel/SetEqPosition", "EqPosition": 2}


async def test_set_noise_status_sends_start(hass, aioclient_mock):
    """set_noise_status(True) posts Tools/SetNoiseStatus with NoiseStatus: 1."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_noise_status(True)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 1}


async def test_set_noise_status_sends_stop(hass, aioclient_mock):
    """set_noise_status(False) posts Tools/SetNoiseStatus with NoiseStatus: 0."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_noise_status(False)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0}


async def test_play_buzzer_sends_cycle_and_total_times(hass, aioclient_mock):
    """play_buzzer posts Device/PlayBuzzer with the cycle/total timings in ms."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.play_buzzer(500, 500, 3000)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Device/PlayBuzzer",
        "ActiveTimeInCycle": 500,
        "OffTimeInCycle": 500,
        "PlayTotalTime": 3000,
    }
