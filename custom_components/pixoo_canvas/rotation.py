"""Automatic page rotation: cycles the device through enabled pages on a timer."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.template import Template

from .api import PixooApiError, PixooClient
from .const import DEFAULT_PAGE_DURATION, MIN_PAGE_DURATION, ROTATION_IDLE_POLL_INTERVAL
from .pages import PagesYamlError, parse_pages
from .render.engine import render_page

_LOGGER = logging.getLogger(__name__)


def _parse_duration(value: Any) -> float:
    """Parse a page's `duration` field, falling back to the default on bad input."""
    if value is None:
        return DEFAULT_PAGE_DURATION
    try:
        return max(MIN_PAGE_DURATION, float(value))
    except (TypeError, ValueError):
        _LOGGER.warning("Invalid page duration %r, using the default", value)
        return DEFAULT_PAGE_DURATION


def _parse_scan_interval(value: Any) -> float | None:
    """Parse a page's optional `scan_interval` field, or None if absent/invalid."""
    if value is None:
        return None
    try:
        return max(MIN_PAGE_DURATION, float(value))
    except (TypeError, ValueError):
        _LOGGER.warning("Invalid page scan_interval %r, ignoring", value)
        return None


def _is_page_enabled(page: dict[str, Any], hass: HomeAssistant) -> bool:
    """Evaluate a page's optional `enabled` Jinja template (default: enabled)."""
    enabled = page.get("enabled")
    if enabled is None:
        return True
    try:
        return bool(Template(str(enabled), hass).async_render())
    except TemplateError as err:
        _LOGGER.warning("Page %r has an invalid 'enabled' template: %s", page.get("name"), err)
        return False


class PageRotator:
    """Cycles the device through configured pages, honoring duration/scan_interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: PixooClient) -> None:
        self._hass = hass
        self._entry = entry
        self._client = client
        self._running = False
        self._unsub: CALLBACK_TYPE | None = None
        self._pages: list[dict[str, Any]] = []
        self._page_index = 0
        self._elapsed = 0.0
        self._pending_step = 0.0

    @property
    def is_running(self) -> bool:
        """Whether the rotation loop is currently active."""
        return self._running

    async def async_start(self) -> None:
        """Start the rotation loop, if not already running."""
        if self._running:
            return
        self._running = True
        self._pages = []
        self._page_index = 0
        self._elapsed = 0.0
        await self._select_page()

    def async_stop(self) -> None:
        """Stop the rotation loop."""
        self._running = False
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def _enabled_pages(self) -> list[dict[str, Any]]:
        try:
            pages = parse_pages(self._entry)
        except PagesYamlError as err:
            _LOGGER.warning("Cannot rotate pages: %s", err)
            return []
        return [page for page in pages if _is_page_enabled(page, self._hass)]

    async def _render(self, page: dict[str, Any]) -> None:
        try:
            await render_page(self._hass, self._client, page.get("components", []))
        except PixooApiError as err:
            _LOGGER.warning(
                "Failed to render page %r during rotation: %s", page.get("name"), err
            )
        except Exception:  # noqa: BLE001 - a single bad page must not stall rotation forever
            _LOGGER.exception(
                "Unexpected error rendering page %r during rotation", page.get("name")
            )

    async def _select_page(self) -> None:
        """Fetch pages if needed, render the current one, and schedule the next check."""
        if not self._pages:
            self._pages = self._enabled_pages()
            self._page_index = 0
            self._elapsed = 0.0
            if not self._pages:
                self._pending_step = ROTATION_IDLE_POLL_INTERVAL
                self._unsub = async_call_later(self._hass, self._pending_step, self._tick)
                return

        await self._render(self._pages[self._page_index])
        self._schedule_next()

    def _schedule_next(self) -> None:
        """Schedule the next tick: either a scan_interval refresh or the page's end."""
        page = self._pages[self._page_index]
        duration = _parse_duration(page.get("duration"))
        scan_interval = _parse_scan_interval(page.get("scan_interval"))
        remaining = max(0.0, duration - self._elapsed)
        self._pending_step = min(scan_interval, remaining) if scan_interval else remaining
        self._unsub = async_call_later(self._hass, self._pending_step, self._tick)

    async def _tick(self, _now: datetime) -> None:
        """Handle a scheduled wake-up: advance to the next page or refresh the current one."""
        if not self._running:
            return

        if not self._pages:
            await self._select_page()
            return

        self._elapsed += self._pending_step
        page = self._pages[self._page_index]
        duration = _parse_duration(page.get("duration"))

        if self._elapsed >= duration:
            self._page_index += 1
            self._elapsed = 0.0
            if self._page_index >= len(self._pages):
                self._pages = []
            await self._select_page()
        else:
            await self._render(page)
            self._schedule_next()
