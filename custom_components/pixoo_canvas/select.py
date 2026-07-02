"""Select platform for Pixoo Canvas — physical screen mounting orientation."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PixooCoordinator

# Device/SetScreenRotationAngle's Mode parameter: 0=0°, 1=90°, 2=180°, 3=270°.
_MODE_TO_OPTION = {0: "0", 1: "90", 2: "180", 3: "270"}
_OPTION_TO_MODE = {option: mode for mode, option in _MODE_TO_OPTION.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Pixoo Canvas screen orientation select."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PixooScreenOrientationSelect(coordinator, entry)])


class PixooScreenOrientationSelect(CoordinatorEntity[PixooCoordinator], SelectEntity):
    """Physical screen mounting orientation, authoritative via GetAllConf's GyrateAngle."""

    _attr_has_entity_name = True
    _attr_translation_key = "screen_orientation"
    _attr_options = list(_MODE_TO_OPTION.values())

    def __init__(self, coordinator: PixooCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_screen_orientation"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the last known, authoritative screen orientation."""
        return _MODE_TO_OPTION.get(self.coordinator.data.gyrate_angle)

    async def async_select_option(self, option: str) -> None:
        """Set the screen orientation to match how the frame is physically mounted."""
        await self.coordinator.client.set_rotation_angle(_OPTION_TO_MODE[option])
        await self.coordinator.async_request_refresh()
