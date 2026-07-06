"""Tests for the Pixoo Canvas device_id diagnostic sensor."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80}


def _device_id_entity_id(hass, entry) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_device_id")
    assert entity_id is not None
    return entity_id


async def test_device_id_sensor_matches_the_device_registry_id(hass, aioclient_mock):
    """The device_id sensor's state is exactly this config entry's HA device_id."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None

    entity_id = _device_id_entity_id(hass, entry)
    assert hass.states.get(entity_id).state == device.id
