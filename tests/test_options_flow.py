"""Tests for the Pixoo Canvas options flow (device IP, default page duration, pages)."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import (
    CONF_DEFAULT_PAGE_DURATION,
    CONF_PAGES_YAML,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.pixoo_canvas.coordinator import PixooCoordinator

HOST = "192.168.1.101"
NEW_HOST = "192.168.1.102"
URL = f"http://{HOST}/post"
NEW_URL = f"http://{NEW_HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80, "SelectIndex": 3}


def _make_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_accepts_valid_input(hass, aioclient_mock):
    """A well-formed host/default_page_duration/pages submission is saved."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = _make_entry(hass)
    pages_yaml = (
        "- name: Temperatures\n  components:\n    - type: text\n      position: [0, 0]\n"
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml}


async def test_options_flow_changing_host_updates_entry_data(hass, aioclient_mock):
    """Submitting a different host updates entry.data, not just entry.options."""
    aioclient_mock.post(NEW_URL, json=GET_ALL_CONF_RESPONSE)
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: NEW_HOST, CONF_DEFAULT_PAGE_DURATION: 15, CONF_PAGES_YAML: ""},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_HOST] == NEW_HOST


async def test_options_flow_rejects_unreachable_host(hass, aioclient_mock):
    """An unreachable new host re-shows the form with a connection error."""
    aioclient_mock.post(NEW_URL, exc=TimeoutError)
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: NEW_HOST, CONF_DEFAULT_PAGE_DURATION: 15, CONF_PAGES_YAML: ""},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data[CONF_HOST] == HOST  # unchanged


async def test_options_flow_saves_without_connection_when_host_unchanged(hass, aioclient_mock):
    """Saving pages/duration with an unchanged host doesn't require the device to be reachable."""
    entry = _make_entry(hass)
    pages_yaml = "- name: Temperatures\n  components:\n    - type: text\n      position: [0, 0]\n"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml}
    assert len(aioclient_mock.mock_calls) == 0


async def test_options_flow_rejects_invalid_yaml(hass, aioclient_mock):
    """Unparsable pages YAML re-shows the form with an error, without testing the connection."""
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 15, CONF_PAGES_YAML: "foo: [unterminated"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_yaml"}


async def test_options_flow_rejects_wrong_schema(hass, aioclient_mock):
    """Valid YAML that isn't a list of {name, components} pages is rejected."""
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 15, CONF_PAGES_YAML: "just_a_string"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_schema"}


async def test_options_flow_accepts_native_channel_page_type(hass, aioclient_mock):
    """A clock/channel/visualizer page with an `id` (no `components`) is valid."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = _make_entry(hass)
    pages_yaml = "- name: Horloge\n  page_type: clock\n  id: 182\n"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_rejects_native_channel_page_without_id(hass, aioclient_mock):
    """A clock/channel/visualizer page without an `id` is rejected."""
    entry = _make_entry(hass)
    pages_yaml = "- name: Horloge\n  page_type: clock\n"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_schema"}


async def test_options_flow_accepts_pv_page_type_without_components(hass, aioclient_mock):
    """A pv/fuel page needs neither `components` nor `id` to be valid."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = _make_entry(hass)
    pages_yaml = "- name: Solaire\n  page_type: pv\n  power: 1200\n  storage: 80\n"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 20, CONF_PAGES_YAML: pages_yaml},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_coordinator_poll_interval_is_not_user_configurable(hass, aioclient_mock):
    """The device poll interval stays fixed regardless of options - it's internal, not a user setting."""
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = _make_entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.update_interval.total_seconds() == DEFAULT_SCAN_INTERVAL

    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_DEFAULT_PAGE_DURATION: 42, CONF_PAGES_YAML: ""}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    coordinator_after: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator_after.update_interval.total_seconds() == DEFAULT_SCAN_INTERVAL
