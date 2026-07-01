"""Tests for the Pixoo Canvas render_page service."""

from __future__ import annotations

import pytest

from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pixoo_canvas.const import CONF_PAGES_YAML, DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"

GET_ALL_CONF_RESPONSE = {"error_code": 0, "LightSwitch": 1, "Brightness": 80}


async def _setup_entry(hass, aioclient_mock, options=None):
    aioclient_mock.post(URL, json=GET_ALL_CONF_RESPONSE)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: HOST}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _device_id(hass, entry) -> str:
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None
    return device.id


async def test_render_page_with_inline_components(hass, aioclient_mock):
    """render_page accepts an inline components list and pushes it."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "render_page",
        {
            "device_id": _device_id(hass, entry),
            "components": [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}],
        },
        blocking=True,
    )

    # initial GetAllConf (setup) + the SendHttpGif push
    assert len(aioclient_mock.mock_calls) == 2


async def test_render_page_with_named_page(hass, aioclient_mock):
    """render_page looks up a named page from the entry's options."""
    pages_yaml = (
        "- name: Temperatures\n"
        "  components:\n"
        "    - type: rectangle\n"
        "      position: [0, 0]\n"
        "      size: [1, 1]\n"
    )
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: pages_yaml})
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "render_page",
        {"device_id": _device_id(hass, entry), "page": "Temperatures"},
        blocking=True,
    )

    assert len(aioclient_mock.mock_calls) == 2


async def test_render_page_requires_page_or_components(hass, aioclient_mock):
    """Calling without page or components raises."""
    entry = await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "render_page",
            {"device_id": _device_id(hass, entry)},
            blocking=True,
        )


async def test_render_page_rejects_both_page_and_components(hass, aioclient_mock):
    """Calling with both page and components raises."""
    entry = await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "render_page",
            {
                "device_id": _device_id(hass, entry),
                "page": "Foo",
                "components": [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}],
            },
            blocking=True,
        )


async def test_render_page_unknown_page_name(hass, aioclient_mock):
    """A page name not present in the configured pages raises."""
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: "[]"})

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "render_page",
            {"device_id": _device_id(hass, entry), "page": "Nope"},
            blocking=True,
        )


async def test_render_page_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "render_page",
            {
                "device_id": "does-not-exist",
                "components": [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}],
            },
            blocking=True,
        )
