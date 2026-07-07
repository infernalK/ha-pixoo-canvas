"""Tests for the Pixoo Canvas switch entities."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, STATE_ON
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import CONF_PAGES_YAML, DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80, "SelectIndex": 3}

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


def _mirror_mode_entity_id(hass, entry) -> str:
    registry = er.async_get(hass)
    entry_obj = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_mirror_mode"
    )
    assert entry_obj is not None
    return entry_obj


def _channel_switch_entity_id(hass, entry, key: str) -> str:
    registry = er.async_get(hass)
    entry_obj = registry.async_get_entity_id("switch", DOMAIN, f"{entry.entry_id}_{key}")
    assert entry_obj is not None
    return entry_obj


async def test_mirror_mode_switch_reflects_authoritative_state(hass, aioclient_mock):
    """The mirror mode switch's state comes from GetAllConf's MirrorFlag, not local state."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "MirrorFlag": 1})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _mirror_mode_entity_id(hass, entry)
    assert hass.states.get(entity_id).state == STATE_ON


async def test_mirror_mode_switch_turn_on_sends_command(hass, aioclient_mock):
    """Turning the mirror mode switch on posts Device/SetMirrorMode with Mode: 1."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _mirror_mode_entity_id(hass, entry)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    mirror_calls = [
        call
        for call in aioclient_mock.mock_calls
        if call[2] is not None and call[2].get("Command") == "Device/SetMirrorMode"
    ]
    assert len(mirror_calls) == 1
    assert mirror_calls[0][2]["Mode"] == 1


async def test_mirror_mode_switch_turn_off_sends_command(hass, aioclient_mock):
    """Turning the mirror mode switch off posts Device/SetMirrorMode with Mode: 0."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "MirrorFlag": 1})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _mirror_mode_entity_id(hass, entry)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    mirror_calls = [
        call
        for call in aioclient_mock.mock_calls
        if call[2] is not None and call[2].get("Command") == "Device/SetMirrorMode"
    ]
    assert len(mirror_calls) == 1
    assert mirror_calls[0][2]["Mode"] == 0


async def test_channel_switch_reflects_authoritative_state(hass, aioclient_mock):
    """Only the channel switch matching the coordinator's SelectIndex is on."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 1})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_cloud")).state == STATE_ON
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_faces")).state == "off"
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_visualizer")).state == "off"
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_custom")).state == "off"


async def test_channel_switch_turn_on_sends_set_index(hass, aioclient_mock):
    """Turning a channel switch on posts Channel/SetIndex with the matching SelectIndex."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 0})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    set_index_calls = [
        call
        for call in aioclient_mock.mock_calls
        if call[2] is not None and call[2].get("Command") == "Channel/SetIndex"
    ]
    assert len(set_index_calls) == 1
    assert set_index_calls[0][2]["SelectIndex"] == 3


async def test_channel_switch_turn_off_is_a_no_op(hass, aioclient_mock):
    """Turning off the active channel switch sends no command - it stays on."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 3})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    calls_before = len(aioclient_mock.mock_calls)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    assert len(aioclient_mock.mock_calls) == calls_before
    assert hass.states.get(entity_id).state == STATE_ON


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
    # initial GetAllConf+GetIndex (setup) + one batched ClearHttpText+SendHttpGif from rotation starting
    assert len(aioclient_mock.mock_calls) == 3


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
