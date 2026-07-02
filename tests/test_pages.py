"""Tests for the pages YAML parsing helpers."""

from __future__ import annotations

import pytest

from homeassistant.const import CONF_HOST
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import CONF_PAGES_YAML, DOMAIN
from custom_components.pixoo_canvas.pages import PagesYamlError, get_page, parse_pages

HOST = "192.168.1.101"


def _entry(hass, pages_yaml: str) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: HOST}, options={CONF_PAGES_YAML: pages_yaml}
    )
    entry.add_to_hass(hass)
    return entry


async def test_parse_pages_empty_options_returns_empty_list(hass):
    """No pages_yaml configured parses to an empty list, not an error."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options={})
    entry.add_to_hass(hass)

    assert parse_pages(entry) == []


async def test_parse_pages_valid_yaml(hass):
    """A valid pages YAML parses into a list of page dicts."""
    entry = _entry(hass, "- name: A\n  components: []\n- name: B\n  components: []\n")

    pages = parse_pages(entry)

    assert [p["name"] for p in pages] == ["A", "B"]


async def test_parse_pages_invalid_yaml_raises(hass):
    """Malformed YAML raises PagesYamlError."""
    entry = _entry(hass, "- name: [unterminated\n")

    with pytest.raises(PagesYamlError):
        parse_pages(entry)


async def test_get_page_returns_matching_page(hass):
    """get_page finds the page whose name matches."""
    entry = _entry(hass, "- name: A\n  components: []\n- name: B\n  components: [1]\n")

    page = get_page(entry, "B")

    assert page["components"] == [1]


async def test_get_page_missing_name_raises(hass):
    """get_page raises PagesYamlError when no page matches."""
    entry = _entry(hass, "- name: A\n  components: []\n")

    with pytest.raises(PagesYamlError):
        get_page(entry, "Nope")
