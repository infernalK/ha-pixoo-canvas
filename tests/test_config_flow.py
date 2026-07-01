"""Tests for the Pixoo Canvas config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pixoo_canvas.const import DOMAIN

HOST = "192.168.1.101"
URL = f"http://{HOST}/post"


async def test_user_flow_success(hass, aioclient_mock):
    """A reachable device creates a config entry."""
    aioclient_mock.post(URL, json={"error_code": 0, "LightSwitch": 1, "Brightness": 80})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == HOST
    assert result["data"] == {CONF_HOST: HOST}


async def test_user_flow_cannot_connect(hass, aioclient_mock):
    """An unreachable device re-shows the form with an error."""
    aioclient_mock.post(URL, exc=TimeoutError)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
