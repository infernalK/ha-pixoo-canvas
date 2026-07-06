"""Tests for PixooClient: batching, text-overlay clearing, and the settle delay."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.pixoo_canvas.api import PixooClient
from custom_components.pixoo_canvas.const import SCROLL_TEXT_SETTLE_DELAY

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


async def test_send_page_batches_clear_and_gif_into_one_request(hass, aioclient_mock):
    """ClearHttpText + Tools/* stops + SendHttpGif are sent as one Draw/CommandList request."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.send_page(64, b"\x00" * (64 * 64 * 3))

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload["Command"] == "Draw/CommandList"
    commands = payload["CommandList"]
    assert [c["Command"] for c in commands] == [
        "Draw/ClearHttpText",
        "Tools/SetNoiseStatus",
        "Tools/SetTimer",
        "Tools/SetStopWatch",
        "Draw/SendHttpGif",
    ]


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
    """set_clock batches Tools/* stops with Channel/SetClockSelectId in one request.

    The stops guard against a sound meter or countdown timer being left
    running from a previous page and swallowing this channel switch (see
    send_page's docstring for the same issue on the buffer-push side).
    """
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_clock(182)

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Channel/SetClockSelectId", "ClockId": 182},
        ],
    }


async def test_set_custom_channel_sends_custom_page_index(hass, aioclient_mock):
    """set_custom_channel batches Tools/* stops with Channel/SetCustomPageIndex."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_custom_channel(1)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Channel/SetCustomPageIndex", "CustomPageIndex": 1},
        ],
    }


async def test_set_visualizer_sends_eq_position(hass, aioclient_mock):
    """set_visualizer batches Tools/* stops with Channel/SetEqPosition."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_visualizer(2)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Channel/SetEqPosition", "EqPosition": 2},
        ],
    }


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


async def test_restart_noise_status_batches_stop_and_start(hass, aioclient_mock):
    """restart_noise_status sends timer/stopwatch-stop+noise-stop+noise-start as one request.

    Sending noise-stop and noise-start as two separate HTTP requests caused
    the device to reboot (same failure mode as unbatched scroll_text
    requests), so both must go out in a single call - along with a
    countdown-timer/stopwatch stop, in case one of those was the tool left
    running instead.
    """
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.restart_noise_status()

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 1},
        ],
    }


async def test_start_timer_batches_noise_stopwatch_stops_timer_stop_and_start(hass, aioclient_mock):
    """start_timer sends noise/stopwatch-stop+timer-stop+timer-start as one request."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.start_timer(5, 30)

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetTimer", "Minute": 5, "Second": 30, "Status": 1},
        ],
    }


async def test_stop_timer_sends_status_0(hass, aioclient_mock):
    """stop_timer posts Tools/SetTimer with Status: 0."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.stop_timer()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0}


async def test_start_stopwatch_batches_noise_timer_stops_stopwatch_stop_and_start(
    hass, aioclient_mock
):
    """start_stopwatch sends noise/timer-stop+stopwatch-stop+stopwatch-start as one request."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.start_stopwatch()

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 1},
        ],
    }


async def test_stop_stopwatch_sends_status_0(hass, aioclient_mock):
    """stop_stopwatch posts Tools/SetStopWatch with Status: 0."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.stop_stopwatch()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetStopWatch", "Status": 0}


async def test_reset_stopwatch_sends_status_2(hass, aioclient_mock):
    """reset_stopwatch posts Tools/SetStopWatch with Status: 2."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.reset_stopwatch()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetStopWatch", "Status": 2}


async def test_set_mirror_mode_sends_mode_1(hass, aioclient_mock):
    """set_mirror_mode(True) posts Device/SetMirrorMode with Mode: 1."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_mirror_mode(True)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Device/SetMirrorMode", "Mode": 1}


async def test_set_mirror_mode_sends_mode_0(hass, aioclient_mock):
    """set_mirror_mode(False) posts Device/SetMirrorMode with Mode: 0."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_mirror_mode(False)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Device/SetMirrorMode", "Mode": 0}


async def test_reboot_sends_sys_reboot(hass, aioclient_mock):
    """reboot posts Device/SysReboot with no extra fields."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.reboot()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Device/SysReboot"}


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
