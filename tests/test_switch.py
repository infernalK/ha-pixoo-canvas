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


async def test_channel_switches_start_off_regardless_of_live_channel(hass, aioclient_mock):
    """All 4 channel switches start off, even though Channel/GetIndex reports one active.

    is_on tracks a local manual-override flag (see PixooState.manual_channel),
    not the live-polled channel: most rotation pages settle on the Custom
    channel, so a switch tied to the live value would read "on" for
    switch.pixoo_channel_custom almost permanently, regardless of whether it
    was ever actually used.
    """
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 1})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_faces")).state == "off"
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_cloud")).state == "off"
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_visualizer")).state == "off"
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_custom")).state == "off"


async def test_channel_switch_turn_on_sends_set_index_and_turns_on(hass, aioclient_mock):
    """Turning a channel switch on posts Channel/SetIndex and flips it on immediately."""
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
    assert hass.states.get(entity_id).state == STATE_ON


async def test_channel_switch_turn_on_turns_the_other_channel_switches_off(hass, aioclient_mock):
    """Turning a channel switch on immediately turns the other 3 off (mutually exclusive)."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 0})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": _channel_switch_entity_id(hass, entry, "channel_faces")},
        blocking=True,
    )
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_faces")).state == STATE_ON

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": _channel_switch_entity_id(hass, entry, "channel_cloud")},
        blocking=True,
    )

    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_cloud")).state == STATE_ON
    assert hass.states.get(_channel_switch_entity_id(hass, entry, "channel_faces")).state == "off"


async def test_channel_switch_turn_off_sends_no_device_command_and_turns_off(hass, aioclient_mock):
    """Turning off a channel switch sends no command but does flip it off locally."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 3})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    assert hass.states.get(entity_id).state == STATE_ON
    calls_before = len(aioclient_mock.mock_calls)

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    assert len(aioclient_mock.mock_calls) == calls_before
    assert hass.states.get(entity_id).state == "off"


async def test_channel_switch_manual_override_survives_a_regular_poll(hass, aioclient_mock):
    """A channel switch turned on stays on after the coordinator's next regular poll.

    _async_update_data must carry the manual override forward - it's not
    something a plain GetAllConf+GetIndex poll should silently clear.
    """
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 0})
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    assert hass.states.get(entity_id).state == STATE_ON

    await coordinator.async_refresh()

    assert hass.states.get(entity_id).state == STATE_ON


async def test_channel_switch_turn_on_pauses_running_page_rotation(hass, aioclient_mock):
    """Turning a channel switch on pauses page rotation if it was running.

    Otherwise rotation's own schedule would overwrite this channel with the
    next page as soon as it next ticks - same rationale as start_timer.
    """
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 0})
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    aioclient_mock.post(URL, json={"error_code": 0})
    await coordinator.rotator.async_start()
    assert coordinator.rotator.is_running is True

    aioclient_mock.post(URL, json={"error_code": 0})
    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )

    assert coordinator.rotator.is_running is False


async def test_channel_switch_turn_off_resumes_page_rotation_it_paused(hass, aioclient_mock):
    """Turning a channel switch off resumes page rotation that its turn_on had paused."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 0})
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]

    aioclient_mock.post(URL, json={"error_code": 0})
    await coordinator.rotator.async_start()

    aioclient_mock.post(URL, json={"error_code": 0})
    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": entity_id}, blocking=True
    )
    assert coordinator.rotator.is_running is False

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    assert coordinator.rotator.is_running is True


async def test_channel_switch_turn_off_does_not_start_rotation_that_was_already_off(
    hass, aioclient_mock
):
    """Turning a channel switch off doesn't turn rotation on if turn_on never paused it."""
    aioclient_mock.post(URL, json={**GET_ALL_CONF_RESPONSE, "SelectIndex": 3})
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: _ONE_PAGE}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.rotator.is_running is False

    entity_id = _channel_switch_entity_id(hass, entry, "channel_custom")
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    assert coordinator.rotator.is_running is False


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
    # initial GetAllConf+GetIndex+ResetHttpGifId (setup) + one batched ClearHttpText+SendHttpGif from rotation starting
    assert len(aioclient_mock.mock_calls) == 4


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
