"""Tests for the Pixoo Canvas render_page service."""

from __future__ import annotations

import pytest
import voluptuous as vol

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

    # initial GetAllConf (setup) + one batched ClearHttpText+SendHttpGif request
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

    # initial GetAllConf (setup) + one batched ClearHttpText+SendHttpGif request
    assert len(aioclient_mock.mock_calls) == 2


async def test_render_page_with_native_clock_page(hass, aioclient_mock):
    """render_page on a page_type: clock page calls Channel/SetClockSelectId, not SendHttpGif."""
    pages_yaml = "- name: Horloge\n  page_type: clock\n  id: 182\n"
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: pages_yaml})
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "render_page",
        {"device_id": _device_id(hass, entry), "page": "Horloge"},
        blocking=True,
    )

    # initial GetAllConf (setup) + one batched Draw/CommandList request
    assert len(aioclient_mock.mock_calls) == 2
    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Channel/SetClockSelectId", "ClockId": 182},
        ],
    }


async def test_render_page_with_inline_page_type_clock(hass, aioclient_mock):
    """render_page accepts an inline page_type (e.g. clock), not just components."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "render_page",
        {"device_id": _device_id(hass, entry), "page_type": "clock", "id": 182},
        blocking=True,
    )

    # initial GetAllConf (setup) + one batched Draw/CommandList request
    assert len(aioclient_mock.mock_calls) == 2
    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Channel/SetClockSelectId", "ClockId": 182},
        ],
    }


async def test_render_page_with_inline_page_type_pv(hass, aioclient_mock):
    """render_page accepts an inline page_type: pv page with its own fields."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "render_page",
        {
            "device_id": _device_id(hass, entry),
            "page_type": "pv",
            "power": 1200,
            "storage": 80,
        },
        blocking=True,
    )

    # initial GetAllConf (setup) + one batched ClearHttpText+SendHttpGif request
    assert len(aioclient_mock.mock_calls) == 2


async def test_render_page_rejects_invalid_inline_page_type(hass, aioclient_mock):
    """An inline clock/channel/visualizer page without an 'id' raises."""
    entry = await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "render_page",
            {"device_id": _device_id(hass, entry), "page_type": "clock"},
            blocking=True,
        )


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


async def test_play_buzzer_sends_default_timings(hass, aioclient_mock):
    """play_buzzer with no explicit timings uses the documented defaults."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "play_buzzer",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Device/PlayBuzzer",
        "ActiveTimeInCycle": 500,
        "OffTimeInCycle": 500,
        "PlayTotalTime": 3000,
    }


async def test_play_buzzer_with_custom_timings(hass, aioclient_mock):
    """play_buzzer forwards explicit timings to the device."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "play_buzzer",
        {
            "device_id": _device_id(hass, entry),
            "active_time_ms": 200,
            "off_time_ms": 100,
            "total_time_ms": 1000,
        },
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Device/PlayBuzzer",
        "ActiveTimeInCycle": 200,
        "OffTimeInCycle": 100,
        "PlayTotalTime": 1000,
    }


async def test_play_buzzer_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "play_buzzer",
            {"device_id": "does-not-exist"},
            blocking=True,
        )


async def test_reboot_device_sends_sys_reboot(hass, aioclient_mock):
    """reboot_device posts Device/SysReboot for the given device."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "reboot_device",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {"Command": "Device/SysReboot"}


async def test_reboot_device_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "reboot_device",
            {"device_id": "does-not-exist"},
            blocking=True,
        )


_ONE_PAGE = (
    "- name: A\n"
    "  duration: 30\n"
    "  components:\n"
    "    - type: rectangle\n"
    "      position: [0, 0]\n"
    "      size: [1, 1]\n"
    "      color: red\n"
)


async def test_start_timer_pauses_running_page_rotation(hass, aioclient_mock):
    """start_timer pauses page rotation if it was running.

    Otherwise rotation's own schedule would overwrite the timer with the
    next page as soon as it next ticks, since rotation doesn't know the
    timer was started out-of-band.
    """
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: _ONE_PAGE})
    coordinator = hass.data[DOMAIN][entry.entry_id]
    aioclient_mock.post(URL, json={"error_code": 0})
    await coordinator.rotator.async_start()
    assert coordinator.rotator.is_running is True

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "start_timer",
        {"device_id": _device_id(hass, entry), "minutes": 5},
        blocking=True,
    )

    assert coordinator.rotator.is_running is False


async def test_stop_timer_resumes_page_rotation_it_paused(hass, aioclient_mock):
    """stop_timer resumes page rotation that start_timer had paused."""
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: _ONE_PAGE})
    coordinator = hass.data[DOMAIN][entry.entry_id]
    aioclient_mock.post(URL, json={"error_code": 0})
    await coordinator.rotator.async_start()

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "start_timer",
        {"device_id": _device_id(hass, entry), "minutes": 5},
        blocking=True,
    )
    assert coordinator.rotator.is_running is False

    aioclient_mock.post(URL, json={"error_code": 0})
    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "stop_timer",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    assert coordinator.rotator.is_running is True


async def test_stop_timer_does_not_start_rotation_that_was_already_off(hass, aioclient_mock):
    """stop_timer doesn't turn rotation on if start_timer never paused it."""
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: _ONE_PAGE})
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.rotator.is_running is False

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "stop_timer",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    assert coordinator.rotator.is_running is False


async def test_start_timer_sends_minute_second_and_status_1(hass, aioclient_mock):
    """start_timer posts Tools/SetTimer with the given minutes/seconds and Status: 1."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "start_timer",
        {"device_id": _device_id(hass, entry), "minutes": 5, "seconds": 30},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetTimer", "Minute": 5, "Second": 30, "Status": 1},
        ],
    }


async def test_start_timer_rejects_zero_duration(hass, aioclient_mock):
    """start_timer with minutes=0 and seconds=0 (the default) raises."""
    entry = await _setup_entry(hass, aioclient_mock)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "start_timer",
            {"device_id": _device_id(hass, entry)},
            blocking=True,
        )


async def test_start_timer_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "start_timer",
            {"device_id": "does-not-exist", "minutes": 5},
            blocking=True,
        )


async def test_stop_timer_sends_status_0(hass, aioclient_mock):
    """stop_timer posts Tools/SetTimer with Status: 0."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "stop_timer",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0}


async def test_stop_timer_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "stop_timer",
            {"device_id": "does-not-exist"},
            blocking=True,
        )


async def test_start_stopwatch_pauses_running_page_rotation(hass, aioclient_mock):
    """start_stopwatch pauses page rotation if it was running.

    Same rationale as start_timer: rotation's own schedule would otherwise
    overwrite the stopwatch with the next page as soon as it next ticks.
    """
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: _ONE_PAGE})
    coordinator = hass.data[DOMAIN][entry.entry_id]
    aioclient_mock.post(URL, json={"error_code": 0})
    await coordinator.rotator.async_start()
    assert coordinator.rotator.is_running is True

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "start_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    assert coordinator.rotator.is_running is False


async def test_stop_stopwatch_resumes_page_rotation_it_paused(hass, aioclient_mock):
    """stop_stopwatch resumes page rotation that start_stopwatch had paused."""
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: _ONE_PAGE})
    coordinator = hass.data[DOMAIN][entry.entry_id]
    aioclient_mock.post(URL, json={"error_code": 0})
    await coordinator.rotator.async_start()

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "start_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )
    assert coordinator.rotator.is_running is False

    aioclient_mock.post(URL, json={"error_code": 0})
    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "stop_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    assert coordinator.rotator.is_running is True


async def test_stop_stopwatch_does_not_start_rotation_that_was_already_off(hass, aioclient_mock):
    """stop_stopwatch doesn't turn rotation on if start_stopwatch never paused it."""
    entry = await _setup_entry(hass, aioclient_mock, options={CONF_PAGES_YAML: _ONE_PAGE})
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.rotator.is_running is False

    aioclient_mock.post(URL, json={"error_code": 0})
    await hass.services.async_call(
        DOMAIN,
        "stop_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    assert coordinator.rotator.is_running is False


async def test_start_stopwatch_sends_status_1(hass, aioclient_mock):
    """start_stopwatch posts a stop+start Tools/SetStopWatch batch, plus noise/timer stops."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "start_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {
        "Command": "Draw/CommandList",
        "CommandList": [
            {"Command": "Tools/SetNoiseStatus", "NoiseStatus": 0},
            {"Command": "Tools/SetTimer", "Minute": 0, "Second": 0, "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 0},
            {"Command": "Tools/SetStopWatch", "Status": 1},
        ],
    }


async def test_start_stopwatch_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "start_stopwatch",
            {"device_id": "does-not-exist"},
            blocking=True,
        )


async def test_stop_stopwatch_sends_status_0(hass, aioclient_mock):
    """stop_stopwatch posts Tools/SetStopWatch with Status: 0."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "stop_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {"Command": "Tools/SetStopWatch", "Status": 0}


async def test_stop_stopwatch_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "stop_stopwatch",
            {"device_id": "does-not-exist"},
            blocking=True,
        )


async def test_reset_stopwatch_sends_status_2(hass, aioclient_mock):
    """reset_stopwatch posts Tools/SetStopWatch with Status: 2."""
    entry = await _setup_entry(hass, aioclient_mock)
    aioclient_mock.post(URL, json={"error_code": 0})

    await hass.services.async_call(
        DOMAIN,
        "reset_stopwatch",
        {"device_id": _device_id(hass, entry)},
        blocking=True,
    )

    payload = aioclient_mock.mock_calls[-1][2]
    assert payload == {"Command": "Tools/SetStopWatch", "Status": 2}


async def test_reset_stopwatch_unknown_device_id(hass, aioclient_mock):
    """An unknown device_id raises."""
    await _setup_entry(hass, aioclient_mock)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "reset_stopwatch",
            {"device_id": "does-not-exist"},
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
