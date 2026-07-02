"""Switch platform for Pixoo Canvas — authoritative screen power."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PixooCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Pixoo Canvas switches."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [PixooScreenPowerSwitch(coordinator, entry), PixooPageRotationSwitch(coordinator, entry)]
    )


class PixooScreenPowerSwitch(CoordinatorEntity[PixooCoordinator], SwitchEntity):
    """Screen power switch, authoritative via Channel/GetAllConf's LightSwitch."""

    _attr_has_entity_name = True
    _attr_translation_key = "screen_power"

    def __init__(self, coordinator: PixooCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_screen_power"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return the last known, authoritative screen power state."""
        return self.coordinator.data.light_switch

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the screen on."""
        await self.coordinator.client.set_screen_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the screen off."""
        await self.coordinator.client.set_screen_power(False)
        await self.coordinator.async_request_refresh()


class PixooPageRotationSwitch(SwitchEntity):
    """Enables/disables automatic page rotation.

    Its on/off preference is restored across restarts via PageRotator's own
    storage (see rotation.py), applied in __init__.py at setup time — not
    via RestoreEntity, whose shared hass-wide restore-state task can leave
    this waiting minutes behind on a busy install. By the time this entity
    is added, rotation has already resumed if it was on before, so is_on
    just reflects the rotator's live state.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "page_rotation"
    _attr_should_poll = False

    def __init__(self, coordinator: PixooCoordinator, entry: ConfigEntry) -> None:
        self._rotator = coordinator.rotator
        self._attr_unique_id = f"{entry.entry_id}_page_rotation"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return whether rotation is currently running."""
        return self._rotator.is_running

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start rotating through the configured pages."""
        await self._rotator.async_start()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop rotation, leaving the last rendered page on screen."""
        await self._rotator.async_disable()
        self.async_write_ha_state()
