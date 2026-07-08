"""Tests for the integration's async_setup_entry."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.api import PixooClient, PixooResponseError
from custom_components.pixoo_canvas.const import DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80, "SelectIndex": 3}


async def test_setup_resets_the_device_gif_id_counter(hass, aioclient_mock):
    """Setup sends Draw/ResetHttpGifId, so a HA restart can't desync it from the device's own counter.

    Regression test: a fresh PixooClient always starts its local PicID
    counter at 0, but the device's own counter (which SendHttpGif is gated
    on) survives an HA restart untouched - without this reset, the very
    first page pushed after a restart could be silently ignored.
    """
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    commands = [call[2]["Command"] for call in aioclient_mock.mock_calls]
    assert "Draw/ResetHttpGifId" in commands


async def test_setup_survives_gif_id_reset_failure(hass, aioclient_mock, monkeypatch):
    """A failed ResetHttpGifId (e.g. a transient error) doesn't block entry setup."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)

    async def _boom(self) -> None:
        raise PixooResponseError("boom")

    monkeypatch.setattr(PixooClient, "reset_gif_id", _boom)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state.value == "loaded"
