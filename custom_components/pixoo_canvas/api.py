"""Async HTTP client for the Divoom Pixoo 64 /post API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    CMD_GET_ALL_CONF,
    CMD_ON_OFF_SCREEN,
    CMD_SET_BRIGHTNESS,
    DEFAULT_TIMEOUT,
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
