"""Sensor platform for Pixoo Canvas — diagnostic entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNEL_NAMES, DOMAIN
from .coordinator import PixooCoordinator, PixooState


@dataclass(frozen=True, kw_only=True)
class PixooSensorEntityDescription(SensorEntityDescription):
    """Describes a Pixoo diagnostic sensor."""

    value_fn: Callable[[PixooState], StateType]


SENSOR_DESCRIPTIONS: tuple[PixooSensorEntityDescription, ...] = (
    PixooSensorEntityDescription(
        key="rotation_flag",
        translation_key="rotation_flag",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.rotation_flag,
    ),
    PixooSensorEntityDescription(
        key="cur_clock_id",
        translation_key="cur_clock_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.cur_clock_id,
    ),
    PixooSensorEntityDescription(
        key="active_channel",
        translation_key="active_channel",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: CHANNEL_NAMES.get(state.channel, "unknown"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Pixoo Canvas diagnostic sensors."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [PixooSensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS]
        + [PixooDeviceIdSensor(hass, entry, coordinator)]
    )


class PixooSensor(CoordinatorEntity[PixooCoordinator], SensorEntity):
    """A diagnostic sensor reflecting one field of the coordinator's state."""

    _attr_has_entity_name = True
    entity_description: PixooSensorEntityDescription

    def __init__(
        self,
        coordinator: PixooCoordinator,
        entry: ConfigEntry,
        description: PixooSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data)


class PixooDeviceIdSensor(SensorEntity):
    """Exposes this device's HA device_id - the value pixoo_canvas services expect.

    render_page/play_buzzer/reboot_device/start_timer/stop_timer all take a
    `device_id`, which isn't otherwise easy to find without digging through
    Settings > Devices > (this device)'s URL - handy to have on hand as a
    plain state when wiring up an iOS/Android Shortcut's "Perform action"
    step, since it can't use HA's device/entity picker UI.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "device_id"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:identifier"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: PixooCoordinator) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_device_id"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        device = dr.async_get(self._hass).async_get_device(identifiers={(DOMAIN, self._entry.entry_id)})
        return device.id if device else None
