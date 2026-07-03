"""Sensor platform for Pixoo Canvas — diagnostic entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
        key="mirror_flag",
        translation_key="mirror_flag",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.mirror_flag,
    ),
    PixooSensorEntityDescription(
        key="cur_clock_id",
        translation_key="cur_clock_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.cur_clock_id,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Pixoo Canvas diagnostic sensors."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PixooSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
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
