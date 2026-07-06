"""Async HTTP client for the Divoom Pixoo 64 /post API."""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

import aiohttp

from .const import (
    CMD_CLEAR_HTTP_TEXT,
    CMD_COMMAND_LIST,
    CMD_GET_ALL_CONF,
    CMD_ON_OFF_SCREEN,
    CMD_PLAY_BUZZER,
    CMD_RESET_HTTP_GIF_ID,
    CMD_SEND_HTTP_GIF,
    CMD_SEND_HTTP_TEXT,
    CMD_SET_BRIGHTNESS,
    CMD_SET_CLOCK,
    CMD_SET_CUSTOM_PAGE,
    CMD_SET_MIRROR_MODE,
    CMD_SET_NOISE_STATUS,
    CMD_SET_ROTATION_ANGLE,
    CMD_SET_STOPWATCH,
    CMD_SET_TIMER,
    CMD_SET_VISUALIZER,
    CMD_SYS_REBOOT,
    DEFAULT_PIC_SPEED_MS,
    DEFAULT_TIMEOUT,
    PIC_ID_MAX,
    SCROLL_TEXT_SETTLE_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class PixooApiError(Exception):
    """Base error for Pixoo API communication."""


class PixooConnectionError(PixooApiError):
    """Raised when the device cannot be reached."""


class PixooResponseError(PixooApiError):
    """Raised when the device returns an error response."""


def _clear_text_payload() -> dict[str, Any]:
    return {"Command": CMD_CLEAR_HTTP_TEXT}


def _noise_status_payload(on: bool) -> dict[str, Any]:
    return {"Command": CMD_SET_NOISE_STATUS, "NoiseStatus": 1 if on else 0}


def _timer_payload(minutes: int, seconds: int, status: int) -> dict[str, Any]:
    return {"Command": CMD_SET_TIMER, "Minute": minutes, "Second": seconds, "Status": status}


def _stopwatch_payload(status: int) -> dict[str, Any]:
    return {"Command": CMD_SET_STOPWATCH, "Status": status}


def _stop_tools_payloads() -> list[dict[str, Any]]:
    """Payloads that force-stop every Tools/* overlay (sound meter, countdown timer, stopwatch).

    Unlike Channel/* pages, Tools/* commands aren't implicitly cancelled by
    switching to something else - left running, they keep the screen (and
    eventually the whole device) stuck on themselves. Bundled into every
    page/channel-switch request so no Tools/* overlay can ever survive onto
    an unrelated page - add any future Tools/* command's stop here too.
    """
    return [_noise_status_payload(False), _timer_payload(0, 0, 0), _stopwatch_payload(0)]


def _gif_payload(pic_id: int, width: int, rgb_bytes: bytes) -> dict[str, Any]:
    return {
        "Command": CMD_SEND_HTTP_GIF,
        "PicNum": 1,
        "PicWidth": width,
        "PicOffset": 0,
        "PicID": pic_id,
        "PicSpeed": DEFAULT_PIC_SPEED_MS,
        "PicData": base64.b64encode(rgb_bytes).decode("ascii"),
    }


def _text_payload(
    text_id: int,
    position: tuple[int, int],
    text: str,
    color: str,
    *,
    direction: int = 0,
    font: int = 0,
    width: int = 64,
    speed: int = 100,
    align: int = 1,
) -> dict[str, Any]:
    return {
        "Command": CMD_SEND_HTTP_TEXT,
        "TextId": text_id,
        "x": position[0],
        "y": position[1],
        "dir": direction,
        "font": font,
        "TextWidth": width,
        "speed": speed,
        "TextString": text,
        "color": color,
        "align": align,
    }


class PixooClient:
    """Async client for a Divoom Pixoo 64 device's local HTTP API."""

    def __init__(self, session: aiohttp.ClientSession, host: str) -> None:
        self._session = session
        self._url = f"http://{host}/post"
        self._pic_id = 0

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a command payload and return the parsed JSON response."""
        try:
            async with self._session.post(
                self._url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except TimeoutError as err:
            raise PixooConnectionError(f"Timeout contacting {self._url}") from err
        except aiohttp.ClientError as err:
            raise PixooConnectionError(f"Cannot connect to {self._url}: {err}") from err
        except ValueError as err:
            # The device occasionally returns a truncated/malformed body.
            raise PixooResponseError(f"Malformed response from {self._url}: {err}") from err

        error_code = data.get("error_code")
        if error_code not in (0, None):
            raise PixooResponseError(
                f"Device returned error_code={error_code} for {payload.get('Command')}"
            )

        return data

    async def get_all_conf(self) -> dict[str, Any]:
        """Fetch the device's full configuration (authoritative state)."""
        return await self._send({"Command": CMD_GET_ALL_CONF})

    async def set_screen_power(self, on: bool) -> None:
        """Turn the screen on or off."""
        await self._send({"Command": CMD_ON_OFF_SCREEN, "OnOff": 1 if on else 0})

    async def set_brightness(self, brightness: int) -> None:
        """Set the screen brightness (0-100)."""
        await self._send(
            {"Command": CMD_SET_BRIGHTNESS, "Brightness": max(0, min(100, brightness))}
        )

    async def set_rotation_angle(self, mode: int) -> None:
        """Set the physical screen orientation: 0=0°, 1=90°, 2=180°, 3=270°."""
        await self._send({"Command": CMD_SET_ROTATION_ANGLE, "Mode": mode})

    async def set_mirror_mode(self, on: bool) -> None:
        """Mirror the screen horizontally."""
        await self._send({"Command": CMD_SET_MIRROR_MODE, "Mode": 1 if on else 0})

    async def set_clock(self, clock_id: int) -> None:
        """Switch the device to one of its built-in clock faces.

        Batched with a Tools/* stop (see _stop_tools_payloads): unlike
        Channel/* commands, Tools overlays (sound meter, countdown timer, stopwatch)
        don't get implicitly cancelled by switching channel - left running,
        they keep the screen (and eventually the whole device, when pushes
        pile up unanswered) stuck on themselves.
        """
        await self.send_command_list(
            [*_stop_tools_payloads(), {"Command": CMD_SET_CLOCK, "ClockId": clock_id}]
        )

    async def set_custom_channel(self, index: int) -> None:
        """Switch the device to one of the 3 custom channels configured in the Divoom app.

        See set_clock() for why a Tools/* stop is batched in here too.
        """
        await self.send_command_list(
            [*_stop_tools_payloads(), {"Command": CMD_SET_CUSTOM_PAGE, "CustomPageIndex": index}]
        )

    async def set_visualizer(self, position: int) -> None:
        """Switch the device to one of its built-in audio visualizers.

        See set_clock() for why a Tools/* stop is batched in here too.
        """
        await self.send_command_list(
            [*_stop_tools_payloads(), {"Command": CMD_SET_VISUALIZER, "EqPosition": position}]
        )

    async def set_noise_status(self, on: bool) -> None:
        """Start or stop the device's built-in sound meter (decibel) tool."""
        await self._send(_noise_status_payload(on))

    async def restart_noise_status(self) -> None:
        """Force a 0->1 edge on the sound meter tool in a single request.

        The device only switches the screen into the tool on the 0->1 edge
        of Tools/SetNoiseStatus, so a stop is sent before every start to
        re-trigger it even if a previous rotation turn left it "started"
        without ever stopping it. Sending those as two separate HTTP
        requests caused the device to reboot - same failure mode already
        seen with unbatched scroll_text requests - so both are batched into
        a single Draw/CommandList call instead. Also stops the countdown
        timer and stopwatch in the same request, in case one of those was
        the one left running.
        """
        await self.send_command_list(
            [
                _timer_payload(0, 0, 0),
                _stopwatch_payload(0),
                _noise_status_payload(False),
                _noise_status_payload(True),
            ]
        )

    async def start_timer(self, minutes: int, seconds: int) -> None:
        """Start a countdown timer, forcing a 0->1 edge in a single request.

        Same edge-triggering and batching rationale as restart_noise_status:
        a stop is sent before the start to re-trigger the device's screen
        switch even if a previous call left the timer "running", and the
        sound meter/stopwatch are stopped too in case one of those was the
        one left running.
        """
        await self.send_command_list(
            [
                _noise_status_payload(False),
                _stopwatch_payload(0),
                _timer_payload(0, 0, 0),
                _timer_payload(minutes, seconds, 1),
            ]
        )

    async def stop_timer(self) -> None:
        """Stop the countdown timer."""
        await self._send(_timer_payload(0, 0, 0))

    async def start_stopwatch(self) -> None:
        """Start the stopwatch.

        Unlike restart_noise_status/start_timer, this does NOT force its
        own stop before the start. Confirmed on real hardware: Tools/
        SetStopWatch's Status:0 (stop) resumes the stopwatch's internal
        elapsed-time counter from wherever it was *before* a preceding
        reset_stopwatch (Status:2) call - reset only clears the on-screen
        display, not that counter - so sending stop-then-start here made
        start_stopwatch right after reset_stopwatch resume from a stale
        non-zero value instead of restarting from 0. The sound meter and
        countdown timer are still stopped here (different tools, no
        evidence of the same issue), in case one of those was left running.
        """
        await self.send_command_list(
            [
                _noise_status_payload(False),
                _timer_payload(0, 0, 0),
                _stopwatch_payload(1),
            ]
        )

    async def stop_stopwatch(self) -> None:
        """Stop the stopwatch."""
        await self._send(_stopwatch_payload(0))

    async def reset_stopwatch(self) -> None:
        """Reset the stopwatch back to zero."""
        await self._send(_stopwatch_payload(2))

    async def reboot(self) -> None:
        """Reboot the device (Device/SysReboot). The screen goes dark for a while."""
        await self._send({"Command": CMD_SYS_REBOOT})

    async def play_buzzer(self, active_time_ms: int, off_time_ms: int, total_time_ms: int) -> None:
        """Play the device's buzzer: on/off cycles of `active_time_ms`/`off_time_ms`, for `total_time_ms` overall."""
        await self._send(
            {
                "Command": CMD_PLAY_BUZZER,
                "ActiveTimeInCycle": active_time_ms,
                "OffTimeInCycle": off_time_ms,
                "PlayTotalTime": total_time_ms,
            }
        )

    async def reset_gif_id(self) -> None:
        """Reset the device's animation frame counter.

        Divoom firmware can stop accepting SendHttpGif pushes once PicID has
        climbed high enough without ever being reset; send_page() calls this
        automatically before the counter reaches PIC_ID_MAX.
        """
        await self._send({"Command": CMD_RESET_HTTP_GIF_ID})
        self._pic_id = 0

    async def send_command_list(self, commands: list[dict[str, Any]]) -> None:
        """Send several commands as a single batched Draw/CommandList request.

        Fewer separate HTTP round-trips per page render - some Pixoo units
        are prone to rebooting under frequent, rapid separate requests, and
        batching noticeably helped.
        """
        await self._send({"Command": CMD_COMMAND_LIST, "CommandList": commands})

    async def send_page(
        self,
        width: int,
        rgb_bytes: bytes,
        scroll_texts: list[dict[str, Any]] | None = None,
    ) -> None:
        """Push a page's buffer, then any scroll_text overlays it defines.

        ClearHttpText, a Tools/* stop (see _stop_tools_payloads) and
        SendHttpGif are batched into a single Draw/CommandList call.
        ClearHttpText runs on every page (not just ones with their own
        scroll_text) because the device does *not* clear a previous page's
        scroll_text on its own when a new buffer is pushed - a stale one
        must never survive onto an unrelated page. The Tools/* stop runs
        for the same reason: those overlays (sound meter, countdown timer, stopwatch)
        aren't implicitly cancelled by a new buffer push either, and left
        running they keep the screen (and eventually the whole device)
        stuck on themselves.

        If `scroll_texts` is given, waits SCROLL_TEXT_SETTLE_DELAY before
        sending them as a second batched call: Divoom's docs say
        SendHttpText is silently ignored unless the device has already
        finished switching into drawing mode from the gif push, and an
        HTTP 200 for that push isn't proof it has.
        """
        if self._pic_id >= PIC_ID_MAX:
            await self.reset_gif_id()
        self._pic_id += 1
        await self.send_command_list(
            [
                _clear_text_payload(),
                *_stop_tools_payloads(),
                _gif_payload(self._pic_id, width, rgb_bytes),
            ]
        )

        if scroll_texts:
            await asyncio.sleep(SCROLL_TEXT_SETTLE_DELAY)
            await self.send_command_list(
                [
                    _text_payload(
                        scroll_text["text_id"],
                        scroll_text["position"],
                        scroll_text["text"],
                        scroll_text["color"],
                        direction=scroll_text["direction"],
                        font=scroll_text["font"],
                        width=scroll_text["width"],
                        speed=scroll_text["speed"],
                        align=scroll_text["align"],
                    )
                    for scroll_text in scroll_texts
                ]
            )
