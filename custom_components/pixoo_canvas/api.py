"""Async HTTP client for the Divoom Pixoo 64 /post API."""

from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp

from .const import (
    CMD_GET_ALL_CONF,
    CMD_ON_OFF_SCREEN,
    CMD_RESET_HTTP_GIF_ID,
    CMD_SEND_HTTP_GIF,
    CMD_SEND_HTTP_TEXT,
    CMD_SET_BRIGHTNESS,
    CMD_SET_ROTATION_ANGLE,
    DEFAULT_PIC_SPEED_MS,
    DEFAULT_TIMEOUT,
    PIC_ID_MAX,
)

_LOGGER = logging.getLogger(__name__)


class PixooApiError(Exception):
    """Base error for Pixoo API communication."""


class PixooConnectionError(PixooApiError):
    """Raised when the device cannot be reached."""


class PixooResponseError(PixooApiError):
    """Raised when the device returns an error response."""


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

    async def send_text_animation(
        self,
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
    ) -> None:
        """Push a native, device-animated scrolling text overlay.

        Only takes effect while the device is showing a custom image pushed
        via send_gif() ("drawing mode") — Divoom's firmware silently ignores
        it if the device is on a clock face or other built-in channel.
        `text_id` (0-19) identifies this text slot; sending the same
        `text_id` again replaces/updates it. `font` selects one of Divoom's
        own 8 built-in device fonts (0-7) — unrelated to this integration's
        bundled fonts, which only apply to the `text` component's buffer
        drawing.
        """
        await self._send(
            {
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
        )

    async def reset_gif_id(self) -> None:
        """Reset the device's animation frame counter.

        Divoom firmware can stop accepting SendHttpGif pushes once PicID has
        climbed high enough without ever being reset; send_gif() calls this
        automatically before the counter reaches PIC_ID_MAX.
        """
        await self._send({"Command": CMD_RESET_HTTP_GIF_ID})
        self._pic_id = 0

    async def send_gif(self, width: int, rgb_bytes: bytes) -> None:
        """Push a single-frame RGB buffer to the screen."""
        if self._pic_id >= PIC_ID_MAX:
            await self.reset_gif_id()
        self._pic_id += 1
        await self._send(
            {
                "Command": CMD_SEND_HTTP_GIF,
                "PicNum": 1,
                "PicWidth": width,
                "PicOffset": 0,
                "PicID": self._pic_id,
                "PicSpeed": DEFAULT_PIC_SPEED_MS,
                "PicData": base64.b64encode(rgb_bytes).decode("ascii"),
            }
        )
