"""Tests for the Pixoo Canvas reboot button."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80, "SelectIndex": 3}


def _reboot_entity_id(hass, entry) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("button", DOMAIN, f"{entry.entry_id}_reboot")
    assert entity_id is not None
    return entity_id


async def test_reboot_button_press_sends_sys_reboot(hass, aioclient_mock):
    """Pressing the reboot button posts Device/SysReboot."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(URL, json={"error_code": 0})
    entity_id = _reboot_entity_id(hass, entry)

    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {"Command": "Device/SysReboot"}
