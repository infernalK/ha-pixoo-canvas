"""Switch platform for Pixoo Canvas — authoritative screen power."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CHANNEL_CLOUD,
    CHANNEL_CUSTOM,
    CHANNEL_FACES,
    CHANNEL_VISUALIZER,
    DOMAIN,
)
from .coordinator import PixooCoordinator


@dataclass(frozen=True, kw_only=True)
class PixooChannelSwitchDescription:
    """Describes one of the device's 4 top-level channel switches."""

    key: str
    translation_key: str
    icon: str
    channel: int


CHANNEL_SWITCH_DESCRIPTIONS = (
    PixooChannelSwitchDescription(
        key="channel_faces", translation_key="channel_faces", icon="mdi:clock-outline", channel=CHANNEL_FACES
    ),
    PixooChannelSwitchDescription(
        key="channel_cloud", translation_key="channel_cloud", icon="mdi:cloud-outline", channel=CHANNEL_CLOUD
    ),
    PixooChannelSwitchDescription(
        key="channel_visualizer",
        translation_key="channel_visualizer",
        icon="mdi:equalizer",
        channel=CHANNEL_VISUALIZER,
    ),
    PixooChannelSwitchDescription(
        key="channel_custom", translation_key="channel_custom", icon="mdi:image-multiple-outline", channel=CHANNEL_CUSTOM
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Pixoo Canvas switches."""
    coordinator: PixooCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PixooScreenPowerSwitch(coordinator, entry),
            PixooPageRotationSwitch(coordinator, entry),
            PixooMirrorModeSwitch(coordinator, entry),
        ]
        + [
            PixooChannelSwitch(coordinator, entry, description)
            for description in CHANNEL_SWITCH_DESCRIPTIONS
        ]
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


class PixooMirrorModeSwitch(CoordinatorEntity[PixooCoordinator], SwitchEntity):
    """Horizontal mirror mode, authoritative via Channel/GetAllConf's MirrorFlag."""

    _attr_has_entity_name = True
    _attr_translation_key = "mirror_mode"

    def __init__(self, coordinator: PixooCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_mirror_mode"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return the last known, authoritative mirror mode state."""
        return self.coordinator.data.mirror_flag

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mirror the screen horizontally."""
        await self.coordinator.client.set_mirror_mode(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the horizontal mirror."""
        await self.coordinator.client.set_mirror_mode(False)
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


class PixooChannelSwitch(CoordinatorEntity[PixooCoordinator], SwitchEntity):
    """One of the device's 4 top-level channels (Faces/Cloud/Visualizer/Custom).

    Radio-button-like: only one channel is ever active on real hardware, and
    there's no "no channel" state to turn off into. is_on reads
    PixooState.manual_channel, NOT the live Channel/GetIndex-polled
    `channel` field (see that field's docstring for why: most rotation
    pages settle back on the Custom channel, which would make
    switch.pixoo_channel_custom read "on" almost permanently regardless of
    whether it was ever actually used).

    turn_on switches to this channel (Channel/SetIndex), pauses page
    rotation - same rationale as start_timer/start_stopwatch: rotation ticks
    on its own schedule regardless of what's on screen, and would otherwise
    overwrite this channel at its next scheduled page - and marks this
    channel as the manual override, which also turns the other 3 channel
    switches off (mutually exclusive). turn_off sends no device command
    (there's no "no channel" state to switch to instead), clears the manual
    override, and resumes rotation if this switch's turn_on had paused it.
    """

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PixooCoordinator, entry: ConfigEntry, description: PixooChannelSwitchDescription
    ) -> None:
        super().__init__(coordinator)
        self._channel = description.channel
        self._attr_translation_key = description.translation_key
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return whether this channel is the current manual override."""
        return self.coordinator.data.manual_channel == self._channel

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the device to this channel, pausing page rotation."""
        await self.coordinator.rotator.async_pause_for_tool()
        await self.coordinator.client.set_channel(self._channel)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, manual_channel=self._channel)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Resume page rotation if this switch's turn_on had paused it.

        Sends no device command: there's no "no channel" state to switch to
        instead.
        """
        await self.coordinator.rotator.async_resume_after_tool()
        self.coordinator.async_set_updated_data(replace(self.coordinator.data, manual_channel=None))
