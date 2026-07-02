"""Tests for the Pixoo Canvas config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pixoo_canvas.config_flow import DISCOVERY_URL, MANUAL_ENTRY_VALUE
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


async def test_user_flow_shows_discovered_devices(hass, aioclient_mock):
    """When Divoom's LAN lookup finds a device, a picker is shown instead of a text field."""
    aioclient_mock.get(
        DISCOVERY_URL,
        json={
            "DeviceList": [
                {"DeviceName": "Pixoo64", "DevicePrivateIP": HOST},
            ]
        },
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "pick_device"
    schema_options = result["data_schema"].schema[CONF_HOST].config["options"]
    values = {opt["value"] for opt in schema_options}
    assert HOST in values
    assert MANUAL_ENTRY_VALUE in values


async def test_user_flow_picking_discovered_device_tests_connection(hass, aioclient_mock):
    """Selecting a discovered device goes straight to the connection test."""
    aioclient_mock.get(
        DISCOVERY_URL,
        json={"DeviceList": [{"DeviceName": "Pixoo64", "DevicePrivateIP": HOST}]},
    )
    aioclient_mock.post(URL, json={"error_code": 0, "LightSwitch": 1, "Brightness": 80})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST}


async def test_user_flow_picking_manual_shows_text_entry(hass, aioclient_mock):
    """Selecting 'Enter IP manually' falls back to the plain text host field."""
    aioclient_mock.get(
        DISCOVERY_URL,
        json={"DeviceList": [{"DeviceName": "Pixoo64", "DevicePrivateIP": HOST}]},
    )
    aioclient_mock.post(URL, json={"error_code": 0, "LightSwitch": 1, "Brightness": 80})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: MANUAL_ENTRY_VALUE}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: HOST}


async def test_user_flow_discovery_error_falls_back_to_manual(hass, aioclient_mock):
    """If Divoom's LAN lookup errors out, setup falls back to manual entry, not a crash."""
    aioclient_mock.get(DISCOVERY_URL, exc=TimeoutError)
    aioclient_mock.post(URL, json={"error_code": 0, "LightSwitch": 1, "Brightness": 80})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_user_flow_discovery_excludes_already_configured_devices(hass, aioclient_mock):
    """A discovered device that's already configured is not offered again."""
    aioclient_mock.post(URL, json={"error_code": 0, "LightSwitch": 1, "Brightness": 80})
    first = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    aioclient_mock.get(DISCOVERY_URL, exc=TimeoutError)
    await hass.config_entries.flow.async_configure(first["flow_id"], {CONF_HOST: HOST})

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        DISCOVERY_URL,
        json={"DeviceList": [{"DeviceName": "Pixoo64", "DevicePrivateIP": HOST}]},
    )

    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # The only discovered device is already configured, so no picker is shown.
    assert second["step_id"] == "manual"
