"""Button platform for Pixoo Canvas — one-shot device actions."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PixooCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Pixoo Canvas buttons."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PixooRebootButton(coordinator, entry)])


class PixooRebootButton(ButtonEntity):
    """Reboots the device (Device/SysReboot).

    A button, not a switch: rebooting has no meaningful persistent on/off
    state to reflect, just a momentary action - same command as the
    pixoo_canvas.reboot_device service.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "reboot"
    _attr_icon = "mdi:restart"

    def __init__(self, coordinator: PixooCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_reboot"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        """Reboot the device."""
        await self._coordinator.client.reboot()
