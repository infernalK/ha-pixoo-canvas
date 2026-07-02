"""Tests for the Pixoo Canvas screen orientation select entity."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


def _orientation_entity_id(hass, entry) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.entry_id}_screen_orientation"
    )
    assert entity_id is not None
    return entity_id


async def _setup_entry(hass, aioclient_mock, gyrate_angle: int = 0) -> MockConfigEntry:
    aioclient_mock.post(
        URL,
        json={
            "error_code": 0,
            "LightSwitch": 1,
            "Brightness": 80,
            "GyrateAngle": gyrate_angle,
        },
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_screen_orientation_reflects_gyrate_angle(hass, aioclient_mock):
    """The select's current_option reflects the coordinator's authoritative GyrateAngle."""
    entry = await _setup_entry(hass, aioclient_mock, gyrate_angle=2)
    entity_id = _orientation_entity_id(hass, entry)

    assert hass.states.get(entity_id).state == "180"


async def test_screen_orientation_options_are_the_four_angles(hass, aioclient_mock):
    """The select exposes exactly the four supported rotation angles."""
    entry = await _setup_entry(hass, aioclient_mock)
    entity_id = _orientation_entity_id(hass, entry)

    options = hass.states.get(entity_id).attributes["options"]
    assert options == ["0", "90", "180", "270"]


async def test_selecting_option_calls_set_rotation_angle(hass, aioclient_mock):
    """Selecting an option sends Device/SetScreenRotationAngle with the matching Mode."""
    entry = await _setup_entry(hass, aioclient_mock)
    entity_id = _orientation_entity_id(hass, entry)

    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "270"},
        blocking=True,
    )

    set_rotation_calls = [
        call
        for call in aioclient_mock.mock_calls
        if call[2] is not None and call[2].get("Command") == "Device/SetScreenRotationAngle"
    ]
    assert len(set_rotation_calls) == 1
    assert set_rotation_calls[0][2]["Mode"] == 3
