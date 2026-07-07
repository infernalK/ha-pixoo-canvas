"""Tests for the Pixoo Canvas coordinator."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.api import PixooClient
from custom_components.pixoo_canvas.const import DOMAIN
from custom_components.pixoo_canvas.coordinator import PixooCoordinator

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


def _make_coordinator(hass) -> PixooCoordinator:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    client = PixooClient(async_get_clientsession(hass), HOST)
    return PixooCoordinator(hass, entry, client)


async def test_coordinator_parses_state(hass, aioclient_mock):
    """A well-formed GetAllConf response is parsed into PixooState."""
    aioclient_mock.post(
        URL,
        json={
            "error_code": 0,
            "LightSwitch": 1,
            "Brightness": 80,
            "RotationFlag": 0,
            "MirrorFlag": 1,
            "CurClockId": 5,
            "GyrateAngle": 2,
            "SelectIndex": 3,
        },
    )

    coordinator = _make_coordinator(hass)
    await coordinator.async_refresh()

    assert coordinator.last_update_success is True
    assert coordinator.data.light_switch is True
    assert coordinator.data.brightness == 80
    assert coordinator.data.mirror_flag is True
    assert coordinator.data.cur_clock_id == 5
    assert coordinator.data.gyrate_angle == 2
    assert coordinator.data.channel == 3


async def test_coordinator_missing_light_switch(hass, aioclient_mock):
    """A response missing LightSwitch results in a clean update failure."""
    aioclient_mock.post(URL, json={"error_code": 0, "Brightness": 50, "SelectIndex": 3})

    coordinator = _make_coordinator(hass)
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_missing_channel(hass, aioclient_mock):
    """A Channel/GetIndex response missing SelectIndex results in a clean update failure."""
    aioclient_mock.post(URL, json={"error_code": 0, "LightSwitch": 1, "Brightness": 80})

    coordinator = _make_coordinator(hass)
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_coordinator_network_error(hass, aioclient_mock):
    """A network error results in a clean update failure, not a crash."""
    aioclient_mock.post(URL, exc=TimeoutError)

    coordinator = _make_coordinator(hass)
    await coordinator.async_refresh()

    assert coordinator.last_update_success is False
