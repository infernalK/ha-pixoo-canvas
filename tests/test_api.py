"""Tests for PixooClient: batching, text-overlay clearing, and the settle delay."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.pixoo_canvas.api import PixooClient, PixooConnectionError
from custom_components.pixoo_canvas.const import SCROLL_TEXT_SETTLE_DELAY

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


async def test_send_page_batches_clear_and_gif_into_one_request(hass, aioclient_mock):
    """ClearHttpText + Tools/* stops + SendHttpGif are sent as one Draw/CommandList request.

    The Tools/* stops appear here because a fresh client defaults to
    "a tool might be active" (see _stop_active_tools) - this is the first
    render on this client instance. See
    test_send_page_skips_tools_stop_once_nothing_may_be_active for the
    (much more common) steady-state case.
    """
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


async def test_send_page_skips_tools_stop_once_nothing_may_be_active(hass, aioclient_mock):
    """A second page render in a row doesn't repeat the Tools/* stop.

    Confirmed on real hardware: sending a Tools/* stop can itself briefly
    flash the screen to that tool's frame even when nothing was running,
    which made the unconditional stop flash on every single rotation page
    change. Once the first render has stopped whatever might have been
    active, subsequent renders skip it entirely until start_timer/
    start_stopwatch/restart_noise_status/set_noise_status(True) runs again.
    """
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    await client.send_page(64, b"\x00" * (64 * 64 * 3))

    await client.send_page(64, b"\x00" * (64 * 64 * 3))

    payload = aioclient_mock.mock_calls[-1][2]
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


async def test_get_channel_returns_select_index(hass, aioclient_mock):
    """get_channel posts Channel/GetIndex and returns the device's SelectIndex."""
    aioclient_mock.post(URL, json={"error_code": 0, "SelectIndex": 2})
    client = PixooClient(async_get_clientsession(hass), HOST)

    result = await client.get_channel()

    assert result == 2
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Channel/GetIndex"}


async def test_set_channel_sends_select_index(hass, aioclient_mock):
    """set_channel posts Channel/SetIndex with the given SelectIndex."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_channel(3)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Channel/SetIndex", "SelectIndex": 3}


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


async def test_set_clock_skips_tools_stop_once_nothing_may_be_active(hass, aioclient_mock):
    """A second channel-switching call in a row doesn't repeat the Tools/* stop."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    await client.set_clock(182)

    await client.set_clock(200)

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [{"Command": "Channel/SetClockSelectId", "ClockId": 200}],
    }


async def test_set_clock_stops_timer_again_after_start_timer(hass, aioclient_mock):
    """start_timer re-arms the Tools/SetTimer stop for the next channel switch."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    await client.set_clock(182)
    await client.start_timer(5, 0)

    await client.set_clock(200)

    payload = aioclient_mock.mock_calls[-1][2]
    commands = payload["CommandList"]
    assert {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0} in commands


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


async def test_send_page_stops_noise_again_after_restart_noise_status(hass, aioclient_mock):
    """restart_noise_status re-arms the noise stop for the next page render."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    await client.send_page(64, b"\x00" * (64 * 64 * 3))
    await client.restart_noise_status()

    await client.send_page(64, b"\x00" * (64 * 64 * 3))

    payload = aioclient_mock.mock_calls[-1][2]
    commands = [c["Command"] for c in payload["CommandList"]]
    assert commands == ["Draw/ClearHttpText", "Tools/SetNoiseStatus", "Draw/SendHttpGif"]


async def test_start_timer_batches_stops_and_start_in_one_request(hass, aioclient_mock):
    """start_timer sends the noise/stopwatch/timer stop+start batch as a single request."""
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


async def test_stop_timer_reads_then_restores_the_current_channel(hass, aioclient_mock):
    """stop_timer fetches Channel/GetIndex first, then stops the timer and restores it.

    No snapshot from a preceding start_timer needed: confirmed on real
    hardware that a bare Tools/SetTimer Status:0 can show the timer's own
    frame even when stop_timer is called "cold" (no prior start_timer on
    this client instance, e.g. called defensively from a Shortcut) - so the
    channel is always re-read and re-selected, unconditionally.
    """
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=3)) as mock_get_channel:
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.stop_timer()

    mock_get_channel.assert_awaited_once()
    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Channel/SetIndex", "SelectIndex": 3},
        ],
    }


async def test_stop_timer_still_stops_if_the_channel_read_fails(hass, aioclient_mock):
    """stop_timer's stop still goes out even if the Channel/GetIndex read errors."""
    with patch.object(
        PixooClient, "get_channel", new=AsyncMock(side_effect=PixooConnectionError("boom"))
    ):
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.stop_timer()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [{"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0}],
    }


async def test_start_stopwatch_batches_stops_and_start_in_one_request(hass, aioclient_mock):
    """start_stopwatch sends the noise/timer stop + stopwatch start as a single request.

    No self-stop before the start: confirmed on real hardware, sending
    Tools/SetStopWatch Status:0 right before Status:1 made the stopwatch
    resume from its pre-reset elapsed time instead of restarting from 0
    after a reset_stopwatch call.
    """
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
            {"Command": "Tools/SetStopWatch", "Status": 1},
        ],
    }


async def test_stop_stopwatch_reads_then_restores_the_current_channel(hass, aioclient_mock):
    """stop_stopwatch fetches Channel/GetIndex first, then stops it and restores the channel.

    No snapshot from a preceding start_stopwatch needed - same "cold call"
    rationale as stop_timer.
    """
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=1)) as mock_get_channel:
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.stop_stopwatch()

    mock_get_channel.assert_awaited_once()
    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Channel/SetIndex", "SelectIndex": 1},
        ],
    }


async def test_stop_stopwatch_still_stops_if_the_channel_read_fails(hass, aioclient_mock):
    """stop_stopwatch's stop still goes out even if the Channel/GetIndex read errors."""
    with patch.object(
        PixooClient, "get_channel", new=AsyncMock(side_effect=PixooConnectionError("boom"))
    ):
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.stop_stopwatch()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [{"Command": "Tools/SetStopWatch", "Status": 0}],
    }


async def test_pause_stopwatch_sends_status_0_without_channel_restore(hass, aioclient_mock):
    """pause_stopwatch posts a bare Tools/SetStopWatch Status:0 and never restores the channel."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.pause_stopwatch()

    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetStopWatch", "Status": 0}


async def test_send_page_still_stops_a_paused_stopwatch(hass, aioclient_mock):
    """pause_stopwatch leaves the stopwatch visible, so the next page render must still clear it."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)
    await client.send_page(64, b"\x00" * (64 * 64 * 3))
    await client.start_stopwatch()
    await client.pause_stopwatch()

    await client.send_page(64, b"\x00" * (64 * 64 * 3))

    payload = aioclient_mock.mock_calls[-1][2]
    commands = [c["Command"] for c in payload["CommandList"]]
    assert "Tools/SetStopWatch" in commands


async def test_reset_stopwatch_sends_status_2(hass, aioclient_mock):
    """reset_stopwatch posts Tools/SetStopWatch with Status: 2."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.reset_stopwatch()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Tools/SetStopWatch", "Status": 2}


async def test_start_visualizer_reads_channel_then_switches(hass, aioclient_mock):
    """start_visualizer captures the current channel, then batches Tools/* stops with SetEqPosition."""
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=1)) as mock_get_channel:
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.start_visualizer(2)

    mock_get_channel.assert_awaited_once()
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


async def test_start_visualizer_does_not_recapture_channel_on_a_second_call(hass, aioclient_mock):
    """Switching visualizer positions without an intervening stop doesn't overwrite the saved channel."""
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=1)) as mock_get_channel:
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)
        await client.start_visualizer(2)

        await client.start_visualizer(3)

    mock_get_channel.assert_awaited_once()


async def test_start_visualizer_still_switches_if_the_channel_read_fails(hass, aioclient_mock):
    """start_visualizer's switch still goes out even if the Channel/GetIndex read errors."""
    with patch.object(
        PixooClient, "get_channel", new=AsyncMock(side_effect=PixooConnectionError("boom"))
    ):
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.start_visualizer(2)

    payload = aioclient_mock.mock_calls[0][2]
    commands = [c["Command"] for c in payload["CommandList"]]
    assert commands[-1] == "Channel/SetEqPosition"


async def test_stop_visualizer_restores_the_channel_captured_by_start_visualizer(hass, aioclient_mock):
    """stop_visualizer restores the channel captured when start_visualizer first switched."""
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=1)):
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)
        await client.start_visualizer(2)

        await client.stop_visualizer()

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {"Command": "Channel/SetIndex", "SelectIndex": 1}


async def test_stop_visualizer_is_a_noop_without_a_captured_channel(hass, aioclient_mock):
    """stop_visualizer sends nothing if start_visualizer never captured a channel (cold call, or the read failed)."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.stop_visualizer()

    assert len(aioclient_mock.mock_calls) == 0


async def test_start_visualizer_recaptures_channel_after_a_stop_visualizer(hass, aioclient_mock):
    """A start_visualizer after stop_visualizer captures the channel again (a fresh session)."""
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=1)) as mock_get_channel:
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)
        await client.start_visualizer(2)
        await client.stop_visualizer()

        await client.start_visualizer(3)

    assert mock_get_channel.await_count == 2


async def test_stop_sound_meter_reads_then_restores_the_current_channel(hass, aioclient_mock):
    """stop_sound_meter fetches Channel/GetIndex first, then stops the noise tool and restores it."""
    with patch.object(PixooClient, "get_channel", new=AsyncMock(return_value=3)) as mock_get_channel:
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.stop_sound_meter()

    mock_get_channel.assert_awaited_once()
    assert len(aioclient_mock.mock_calls) == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Channel/SetIndex", "SelectIndex": 3},
        ],
    }


async def test_stop_sound_meter_still_stops_if_the_channel_read_fails(hass, aioclient_mock):
    """stop_sound_meter's stop still goes out even if the Channel/GetIndex read errors."""
    with patch.object(
        PixooClient, "get_channel", new=AsyncMock(side_effect=PixooConnectionError("boom"))
    ):
        aioclient_mock.post(URL, json={"error_code": 0})
        client = PixooClient(async_get_clientsession(hass), HOST)

        await client.stop_sound_meter()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [{"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0}],
    }


async def test_set_alarm_sends_enable_flag_1_with_alarm_time(hass, aioclient_mock):
    """set_alarm posts Alarm/Set with EnableFlag: 1 and AlarmTime as 'HH:MM'."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_alarm(7, 30)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Alarm/Set", "EnableFlag": 1, "AlarmTime": "07:30"}


async def test_set_alarm_enabled_false_sends_enable_flag_0(hass, aioclient_mock):
    """set_alarm(enabled=False) still posts the given AlarmTime, but with EnableFlag: 0."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.set_alarm(7, 30, enabled=False)

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Alarm/Set", "EnableFlag": 0, "AlarmTime": "07:30"}


async def test_stop_alarm_sends_enable_flag_0_with_zeroed_time(hass, aioclient_mock):
    """stop_alarm posts Alarm/Set with EnableFlag: 0, AlarmTime: '00:00'."""
    aioclient_mock.post(URL, json={"error_code": 0})
    client = PixooClient(async_get_clientsession(hass), HOST)

    await client.stop_alarm()

    payload = aioclient_mock.mock_calls[0][2]
    assert payload == {"Command": "Alarm/Set", "EnableFlag": 0, "AlarmTime": "00:00"}


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
