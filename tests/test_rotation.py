"""Tests for the automatic page rotation engine."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_HOST
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.pixoo_canvas.api import PixooConnectionError
from custom_components.pixoo_canvas.const import (
    CONF_DEFAULT_PAGE_DURATION,
    CONF_PAGES_YAML,
    DOMAIN,
)
from custom_components.pixoo_canvas.rotation import PageRotator

HOST = "192.168.1.101"

_PAGE_A_B = (
    "- name: A\n"
    "  duration: 10\n"
    "  components:\n"
    "    - type: rectangle\n"
    "      position: [0, 0]\n"
    "      size: [1, 1]\n"
    "      color: red\n"
    "- name: B\n"
    "  duration: 10\n"
    "  components:\n"
    "    - type: rectangle\n"
    "      position: [0, 0]\n"
    "      size: [1, 1]\n"
    "      color: blue\n"
)


class _FakeClient:
    """Records send_page calls without touching the network."""

    def __init__(self) -> None:
        self.calls: list[bytes] = []

    async def send_page(self, width: int, rgb_bytes: bytes, scroll_texts=None) -> None:
        self.calls.append(rgb_bytes)


def _entry(hass, pages_yaml: str) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: pages_yaml}
    )
    entry.add_to_hass(hass)
    return entry


def _advance(hass, seconds: float) -> None:
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=seconds))


async def test_async_start_renders_first_page_immediately(hass):
    """Starting rotation renders the first enabled page right away."""
    entry = _entry(hass, _PAGE_A_B)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)

    await rotator.async_start()

    assert len(client.calls) == 1
    assert rotator.is_running is True
    await rotator.async_stop()


async def test_rotation_advances_after_duration(hass):
    """Once a page's duration elapses, rotation renders the next page."""
    entry = _entry(hass, _PAGE_A_B)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)
    await rotator.async_start()
    assert len(client.calls) == 1

    _advance(hass, 11)
    await hass.async_block_till_done()

    assert len(client.calls) == 2
    await rotator.async_stop()


async def test_scan_interval_refreshes_mid_duration(hass):
    """A page's scan_interval re-renders it before its duration elapses."""
    pages_yaml = (
        "- name: A\n"
        "  duration: 20\n"
        "  scan_interval: 5\n"
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
        "      color: red\n"
    )
    entry = _entry(hass, pages_yaml)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)
    await rotator.async_start()
    assert len(client.calls) == 1

    _advance(hass, 6)
    await hass.async_block_till_done()

    assert len(client.calls) == 2
    await rotator.async_stop()


async def test_entry_default_page_duration_applies_when_page_has_none(hass):
    """A page without its own `duration` uses the entry's configured default, not the built-in 15s."""
    pages_yaml = (
        "- name: A\n"
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
        "      color: red\n"
        "- name: B\n"
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
        "      color: blue\n"
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        options={CONF_PAGES_YAML: pages_yaml, CONF_DEFAULT_PAGE_DURATION: 5},
    )
    entry.add_to_hass(hass)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)
    await rotator.async_start()
    assert len(client.calls) == 1

    # Past the entry's 5s default, well short of the built-in 15s fallback.
    _advance(hass, 6)
    await hass.async_block_till_done()

    assert len(client.calls) == 2
    await rotator.async_stop()


async def test_page_duration_overrides_entry_default(hass):
    """A page with its own `duration` ignores the entry's default page duration."""
    pages_yaml = (
        "- name: A\n"
        "  duration: 20\n"
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
        "      color: red\n"
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        options={CONF_PAGES_YAML: pages_yaml, CONF_DEFAULT_PAGE_DURATION: 5},
    )
    entry.add_to_hass(hass)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)
    await rotator.async_start()
    assert len(client.calls) == 1

    # Past the entry's 5s default, but short of the page's own 20s duration.
    _advance(hass, 6)
    await hass.async_block_till_done()

    assert len(client.calls) == 1  # still showing page A
    await rotator.async_stop()


async def test_disabled_page_is_skipped(hass):
    """A page whose `enabled` template renders falsy is not shown."""
    pages_yaml = (
        "- name: A\n"
        '  enabled: "{{ false }}"\n'
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
        "      color: red\n"
        "- name: B\n"
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
        "      color: blue\n"
    )
    entry = _entry(hass, pages_yaml)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)

    await rotator.async_start()

    assert len(client.calls) == 1
    assert client.calls[0][:3] == bytes([0, 0, 255])  # page B (blue), A was skipped
    await rotator.async_stop()


async def test_no_pages_configured_is_idle_noop(hass):
    """With no pages configured, rotation stays 'on' but renders nothing."""
    entry = _entry(hass, "")
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)

    await rotator.async_start()

    assert len(client.calls) == 0
    assert rotator.is_running is True
    await rotator.async_stop()


async def test_async_stop_halts_further_rendering(hass):
    """Stopping rotation cancels the scheduled next tick."""
    entry = _entry(hass, _PAGE_A_B)
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)
    await rotator.async_start()
    assert len(client.calls) == 1

    await rotator.async_stop()
    _advance(hass, 30)
    await hass.async_block_till_done()

    assert len(client.calls) == 1
    assert rotator.is_running is False


async def test_device_error_does_not_stall_rotation(hass):
    """A render failure on one page must not prevent rotation from advancing."""

    class _FlakyClient:
        def __init__(self) -> None:
            self.calls = 0

        async def send_page(self, width: int, rgb_bytes: bytes, scroll_texts=None) -> None:
            self.calls += 1
            if self.calls == 1:
                raise PixooConnectionError("boom")

    entry = _entry(hass, _PAGE_A_B)
    client = _FlakyClient()
    rotator = PageRotator(hass, entry, client)
    await rotator.async_start()
    assert client.calls == 1

    _advance(hass, 11)
    await hass.async_block_till_done()

    assert client.calls == 2
    await rotator.async_stop()


async def test_invalid_pages_yaml_is_idle_noop(hass):
    """Malformed pages YAML logs a warning and leaves rotation idle, not crashed."""
    entry = _entry(hass, "- name: [unterminated\n")
    client = _FakeClient()
    rotator = PageRotator(hass, entry, client)

    await rotator.async_start()

    assert len(client.calls) == 0
    assert rotator.is_running is True
    await rotator.async_stop()
