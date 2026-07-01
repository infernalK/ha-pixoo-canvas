"""Tests for the Pixoo Canvas options flow (pages YAML editor)."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import CONF_PAGES_YAML, DOMAIN

HOST = "192.168.1.101"


def _make_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST})
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_accepts_valid_pages_yaml(hass):
    """A well-formed pages list is saved to entry.options."""
    entry = _make_entry(hass)
    pages_yaml = (
        "- name: Temperatures\n  components:\n    - type: text\n      position: [0, 0]\n"
    )

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PAGES_YAML: pages_yaml}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_PAGES_YAML: pages_yaml}


async def test_options_flow_rejects_invalid_yaml(hass):
    """Unparsable YAML re-shows the form with an error."""
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PAGES_YAML: "foo: [unterminated"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_yaml"}


async def test_options_flow_rejects_wrong_schema(hass):
    """Valid YAML that isn't a list of {name, components} pages is rejected."""
    entry = _make_entry(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_PAGES_YAML: "just_a_string"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_schema"}
