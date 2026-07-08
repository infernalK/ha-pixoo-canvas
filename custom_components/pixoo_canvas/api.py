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
    CMD_GET_CHANNEL,
    CMD_ON_OFF_SCREEN,
    CMD_PLAY_BUZZER,
    CMD_SET_ALARM,
    CMD_RESET_HTTP_GIF_ID,
    CMD_SEND_HTTP_GIF,
    CMD_SEND_HTTP_TEXT,
    CMD_SET_BRIGHTNESS,
    CMD_SET_CHANNEL,
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


def _channel_payload(channel: int) -> dict[str, Any]:
    return {"Command": CMD_SET_CHANNEL, "SelectIndex": channel}


def _alarm_payload(hour: int, minute: int, enabled: bool) -> dict[str, Any]:
    return {"Command": CMD_SET_ALARM, "Status": 1 if enabled else 0, "Hour": hour, "Minute": minute}


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
        # Tracks whether each Tools/* overlay might currently be showing, so
        # routine page renders (send_page/set_clock/set_custom_channel/
        # set_visualizer) only send that tool's stop when it's actually
        # worth sending - see _stop_active_tools(). Default True: be
        # defensive on the first render after a HA/integration restart, in
        # case a tool was left active from before it.
        self._noise_may_be_active = True
        self._timer_may_be_active = True
        self._stopwatch_may_be_active = True
        # Unlike the above (Tools/* overlays, which don't alter the device's
        # own notion of "current channel" - see get_channel), start_visualizer
        # switches the channel itself, so the channel to restore on
        # stop_visualizer must be captured up front rather than read fresh at
        # stop time.
        self._visualizer_may_be_active = False
        self._pre_visualizer_channel: int | None = None

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

    async def get_channel(self) -> int:
        """Fetch the device's current top-level channel (0=Faces, 1=Cloud, 2=Visualizer, 3=Custom).

        Distinct from Channel/GetAllConf: Tools/* overlays (sound meter,
        countdown timer, stopwatch) sit on top of whichever of these four
        channels was active before they started, and this call still reports
        that underlying channel while an overlay is showing.
        """
        data = await self._send({"Command": CMD_GET_CHANNEL})
        return int(data["SelectIndex"])

    async def set_channel(self, channel: int) -> None:
        """Switch to one of the device's 4 top-level channels (see get_channel).

        Used to cleanly back out of a Tools/* overlay (see stop_timer/
        stop_stopwatch): re-selecting the channel that was active before the
        overlay started re-displays it, unlike a bare Tools/* Status:0 stop
        which otherwise leaves the overlay's frame on screen.
        """
        await self._send(_channel_payload(channel))

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

    def _stop_active_tools(self, *, include_noise: bool = True) -> list[dict[str, Any]]:
        """Stop payloads for whichever Tools/* overlays might actually be showing.

        Unlike Channel/* pages, Tools/* commands aren't implicitly cancelled
        by switching to something else - left running, they keep the screen
        (and eventually the whole device) stuck on themselves. That's why
        this is batched into every page/channel-switch request - but
        confirmed on real hardware, sending a Tools/* stop can itself
        briefly flash the screen to that tool's frame even when it was
        never actually running (see stop_timer/stop_stopwatch), which made
        this unconditional stop flash visibly on *every* rotation page
        change. Tracking per-tool whether it might be active (see
        start_timer/stop_timer, start_stopwatch/stop_stopwatch/
        pause_stopwatch, set_noise_status/restart_noise_status) limits the
        stop to the common case where it's actually needed - at the cost of
        not catching a tool started outside this integration (e.g. from the
        Divoom app or a physical remote) until the next locally-tracked
        action runs.
        """
        payloads: list[dict[str, Any]] = []
        if include_noise and self._noise_may_be_active:
            payloads.append(_noise_status_payload(False))
            self._noise_may_be_active = False
        if self._timer_may_be_active:
            payloads.append(_timer_payload(0, 0, 0))
            self._timer_may_be_active = False
        if self._stopwatch_may_be_active:
            payloads.append(_stopwatch_payload(0))
            self._stopwatch_may_be_active = False
        return payloads

    async def set_clock(self, clock_id: int) -> None:
        """Switch the device to one of its built-in clock faces.

        Batched with a Tools/* stop for whichever tools might be active
        (see _stop_active_tools).
        """
        await self.send_command_list(
            [*self._stop_active_tools(), {"Command": CMD_SET_CLOCK, "ClockId": clock_id}]
        )

    async def set_custom_channel(self, index: int) -> None:
        """Switch the device to one of the 3 custom channels configured in the Divoom app.

        See set_clock() for why a Tools/* stop is batched in here too.
        """
        await self.send_command_list(
            [*self._stop_active_tools(), {"Command": CMD_SET_CUSTOM_PAGE, "CustomPageIndex": index}]
        )

    async def set_visualizer(self, position: int) -> None:
        """Switch the device to one of its built-in audio visualizers.

        See set_clock() for why a Tools/* stop is batched in here too.
        """
        await self.send_command_list(
            [*self._stop_active_tools(), {"Command": CMD_SET_VISUALIZER, "EqPosition": position}]
        )

    async def start_visualizer(self, position: int) -> None:
        """Switch to a built-in audio visualizer, remembering the channel to restore.

        Unlike set_visualizer's plain channel switch, this captures the
        channel active *before* switching (unless one is already captured
        from an earlier start_visualizer, so cycling between visualizer
        positions without an intervening stop_visualizer doesn't overwrite
        it with the visualizer's own channel) so stop_visualizer can put it
        back - see the docstring on _pre_visualizer_channel for why this
        can't just be read fresh at stop time the way stop_timer/
        stop_stopwatch do.
        """
        if not self._visualizer_may_be_active:
            try:
                self._pre_visualizer_channel = await self.get_channel()
            except PixooApiError:
                self._pre_visualizer_channel = None
            self._visualizer_may_be_active = True
        await self.set_visualizer(position)

    async def stop_visualizer(self) -> None:
        """Restore the channel that was active before start_visualizer, if captured."""
        if self._pre_visualizer_channel is not None:
            await self.set_channel(self._pre_visualizer_channel)
        self._visualizer_may_be_active = False
        self._pre_visualizer_channel = None

    async def set_noise_status(self, on: bool) -> None:
        """Start or stop the device's built-in sound meter (decibel) tool."""
        await self._send(_noise_status_payload(on))
        self._noise_may_be_active = on

    async def restart_noise_status(self) -> None:
        """Force a 0->1 edge on the sound meter tool in a single request.

        The device only switches the screen into the tool on the 0->1 edge
        of Tools/SetNoiseStatus, so a stop is sent before every start to
        re-trigger it even if a previous rotation turn left it "started"
        without ever stopping it - this part is unconditional, unlike
        _stop_active_tools's noise handling, since it's mandatory for the
        edge-trigger itself, not a defensive extra. Sending those as two
        separate HTTP requests caused the device to reboot - same failure
        mode already seen with unbatched scroll_text requests - so both are
        batched into a single Draw/CommandList call instead. Also stops the
        countdown timer and stopwatch in the same request if either might
        be active (see _stop_active_tools).
        """
        await self.send_command_list(
            [
                *self._stop_active_tools(include_noise=False),
                _noise_status_payload(False),
                _noise_status_payload(True),
            ]
        )
        self._noise_may_be_active = True

    async def stop_sound_meter(self) -> None:
        """Stop the sound meter and restore whatever channel is active underneath.

        Same channel-restore rationale as stop_timer/stop_stopwatch: a
        Tools/* overlay doesn't alter the device's own notion of "current
        channel", so it's read fresh here rather than needing to be
        captured at start time (contrast start_visualizer/stop_visualizer,
        a Channel/* switch that does alter it).
        """
        try:
            channel = await self.get_channel()
        except PixooApiError:
            channel = None
        commands = [_noise_status_payload(False)]
        if channel is not None:
            commands.append(_channel_payload(channel))
        await self.send_command_list(commands)
        self._noise_may_be_active = False

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
        self._noise_may_be_active = False
        self._stopwatch_may_be_active = False
        self._timer_may_be_active = True

    async def stop_timer(self) -> None:
        """Stop the countdown timer and restore whatever channel is active underneath.

        No pause_timer counterpart: confirmed on real hardware (and in
        Divoom's own app) that stopping a countdown timer always resets it
        to 0 - there's no way to freeze it mid-countdown and resume later,
        unlike the stopwatch.

        Confirmed on real hardware: a bare Tools/SetTimer Status:0 can show
        the timer's own frame on screen even when stop_timer is called
        without a preceding start_timer on this client instance (e.g. called
        defensively from a Shortcut, "just in case" something was left
        running) - contrary to Tools/*'s usual 0->1-edge-only screen switch.
        Always re-selecting the current channel (Channel/GetIndex then
        Channel/SetIndex) alongside the stop forces a clean return
        regardless. The channel read is best-effort: if it fails, the stop
        itself must still go out rather than being blocked by it.
        """
        try:
            channel = await self.get_channel()
        except PixooApiError:
            channel = None
        commands = [_timer_payload(0, 0, 0)]
        if channel is not None:
            commands.append(_channel_payload(channel))
        await self.send_command_list(commands)
        self._timer_may_be_active = False

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
        self._noise_may_be_active = False
        self._timer_may_be_active = False
        self._stopwatch_may_be_active = True

    async def stop_stopwatch(self) -> None:
        """Stop the stopwatch and restore whatever channel is active underneath.

        Confirmed on real hardware: a bare Tools/SetStopWatch Status:0 can
        show the stopwatch's own frame on screen even when stop_stopwatch is
        called without a preceding start_stopwatch on this client instance
        (e.g. called defensively from a Shortcut, "just in case" something
        was left running) - contrary to Tools/*'s usual 0->1-edge-only
        screen switch. Always re-selecting the current channel
        (Channel/GetIndex then Channel/SetIndex) alongside the stop forces a
        clean return regardless. The channel read is best-effort: if it
        fails, the stop itself must still go out rather than being blocked
        by it. Use pause_stopwatch instead when the elapsed time should stay
        on screen, ready to resume.
        """
        try:
            channel = await self.get_channel()
        except PixooApiError:
            channel = None
        commands = [_stopwatch_payload(0)]
        if channel is not None:
            commands.append(_channel_payload(channel))
        await self.send_command_list(commands)
        self._stopwatch_may_be_active = False

    async def pause_stopwatch(self) -> None:
        """Pause the stopwatch, keeping its elapsed time on screen to resume later.

        Same underlying command as stop_stopwatch (Status:0), minus the
        channel restore: unlike stop_stopwatch (done with the stopwatch,
        hand the screen back), a pause should stay visible until
        start_stopwatch resumes it. Deliberately does NOT clear
        _stopwatch_may_be_active either, for the same reason: the paused
        stopwatch is still visibly up, so a later page render must still
        stop it (see _stop_active_tools).
        """
        await self._send(_stopwatch_payload(0))

    async def reset_stopwatch(self) -> None:
        """Reset the stopwatch back to zero.

        Deliberately does not touch _stopwatch_may_be_active: whether this
        also stops it if it was running is untested on real hardware (see
        the stop_stopwatch docstring), so it's left as-is rather than
        risking clearing it while the stopwatch might still be active.
        """
        await self._send(_stopwatch_payload(2))

    async def set_alarm(self, hour: int, minute: int, enabled: bool = True) -> None:
        """Set the device's built-in alarm clock to ring at hour:minute (24h).

        Unlike start_timer/start_stopwatch/start_visualizer, the alarm
        doesn't take over the screen immediately - it's a scheduled wake
        handled entirely by the device's own firmware - so this is a plain
        one-shot Alarm/Set call: no _stop_active_tools batching, no
        page-rotation pause needed. See the CMD_SET_ALARM comment in
        const.py - the command name and field shape are still unverified
        end-to-end on real hardware.
        """
        await self._send(_alarm_payload(hour, minute, enabled))

    async def stop_alarm(self) -> None:
        """Disable the alarm clock (Alarm/Set, Status: 0)."""
        await self._send(_alarm_payload(0, 0, False))

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

        ClearHttpText, a Tools/* stop for whichever tools might be active
        (see _stop_active_tools) and SendHttpGif are batched into a single
        Draw/CommandList call. ClearHttpText runs on every page (not just
        ones with their own scroll_text) because the device does *not*
        clear a previous page's scroll_text on its own when a new buffer is
        pushed - a stale one must never survive onto an unrelated page.

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
                *self._stop_active_tools(),
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
