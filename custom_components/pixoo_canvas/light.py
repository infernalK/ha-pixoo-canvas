"""Light platform for Pixoo Canvas — brightness only, no on/off ambiguity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PixooCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Pixoo Canvas brightness light."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PixooBrightnessLight(coordinator, entry)])


class PixooBrightnessLight(CoordinatorEntity[PixooCoordinator], LightEntity):
    """Screen brightness control, decoupled from the power switch."""

    _attr_has_entity_name = True
    _attr_translation_key = "brightness"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: PixooCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_brightness"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.light_switch

    @property
    def brightness(self) -> int:
        # Device brightness is 0-100, HA's ATTR_BRIGHTNESS is 0-255.
        return round(self.coordinator.data.brightness * 255 / 100)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set brightness, or turn the screen on if no brightness given."""
        if ATTR_BRIGHTNESS in kwargs:
            device_brightness = round(kwargs[ATTR_BRIGHTNESS] * 100 / 255)
            await self.coordinator.client.set_brightness(device_brightness)
        else:
            await self.coordinator.client.set_screen_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the screen off."""
        await self.coordinator.client.set_screen_power(False)
        await self.coordinator.async_request_refresh()
