"""Tests for the Pixoo Canvas switch entities."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, STATE_ON
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import CONF_PAGES_YAML, DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80}

_ONE_PAGE = (
    "- name: A\n"
    "  duration: 30\n"
    "  components:\n"
    "    - type: rectangle\n"
    "      position: [0, 0]\n"
    "      size: [1, 1]\n"
    "      color: red\n"
)


def _rotation_entity_id(hass, entry) -> str:
    registry = er.async_get(hass)
    entry_obj = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_page_rotation"
    )
    assert entry_obj is not None
    return entry_obj


async def test_page_rotation_switch_turn_on_starts_rendering(hass, aioclient_mock):
    """Turning the page rotation switch on renders the first configured page."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(URL, json={"error_code": 0})
    entity_id = _rotation_entity_id(hass, entry)

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    assert hass.states.get(entity_id).state == STATE_ON
    # initial GetAllConf (setup) + one SendHttpGif push from rotation starting
    assert len(aioclient_mock.mock_calls) == 2


async def test_page_rotation_switch_turn_off_stops_rotation(hass, aioclient_mock):
    """Turning the switch off marks rotation as stopped."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(URL, json={"error_code": 0})
    entity_id = _rotation_entity_id(hass, entry)
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    assert hass.states.get(entity_id).state == STATE_ON

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    assert hass.states.get(entity_id).state == "off"


async def test_page_rotation_switch_resumes_after_restart(hass, aioclient_mock):
    """Rotation that was on before a restart (unload + setup) resumes automatically.

    This exercises PageRotator's own storage (rotation.py), applied at
    __init__.py setup time, rather than RestoreEntity: an earlier version
    used RestoreEntity, which depends on a single hass-wide restore-state
    loading task shared by every restorable entity on the instance, and on
    a busy real install that left rotation waiting minutes after a restart.
    """
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _rotation_entity_id(hass, entry)

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    assert hass.states.get(entity_id).state == STATE_ON

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    aioclient_mock.post(URL, json={"error_code": 0})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == STATE_ON


async def test_page_rotation_switch_stays_off_after_restart(hass, aioclient_mock):
    """Rotation left off before a restart stays off, it doesn't default to on."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _rotation_entity_id(hass, entry)
    assert hass.states.get(entity_id).state == "off"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == "off"
