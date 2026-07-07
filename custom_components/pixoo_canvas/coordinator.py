"""DataUpdateCoordinator polling the Pixoo device's authoritative state."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PixooApiError, PixooClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .rotation import PageRotator

_LOGGER = logging.getLogger(__name__)


@dataclass
class PixooState:
    """Parsed device state, from Channel/GetAllConf."""

    light_switch: bool
    brightness: int
    rotation_flag: bool
    mirror_flag: bool
    cur_clock_id: int
    # Physical screen mounting orientation (0=0°, 1=90°, 2=180°, 3=270°),
    # set via Device/SetScreenRotationAngle. Distinct from `rotation_flag`
    # above, whose exact meaning is unconfirmed (likely gallery auto-cycle,
    # not screen orientation, based on its position next to Gallery* fields
    # in GetAllConf's response).
    gyrate_angle: int
    # Device's top-level channel (0=Faces, 1=Cloud, 2=Visualizer, 3=Custom),
    # from Channel/GetIndex - a separate call from GetAllConf above.
    channel: int


class PixooCoordinator(DataUpdateCoordinator[PixooState]):
    """Coordinator polling Channel/GetAllConf for the authoritative device state."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: PixooClient) -> None:
        # Not user-configurable: how often the integration reads the
        # device's authoritative state is an internal implementation
        # detail, unrelated to how long pages stay on screen (see
        # rotation.py's CONF_DEFAULT_PAGE_DURATION for the user-facing knob).
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({entry.title})",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        # DataUpdateCoordinator declares this Optional (a coordinator need not
        # be tied to a config entry) - ours always is, so narrow it here once
        # instead of every caller having to assert/guard against None.
        self.config_entry: ConfigEntry = entry
        self.rotator = PageRotator(hass, entry, client)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Pixoo 64",
            manufacturer="Divoom",
            model="Pixoo 64",
        )

    async def _async_update_data(self) -> PixooState:
        try:
            raw = await self.client.get_all_conf()
            channel = await self.client.get_channel()
            state = PixooState(
                light_switch=bool(raw["LightSwitch"]),
                brightness=int(raw["Brightness"]),
                rotation_flag=bool(raw.get("RotationFlag", 0)),
                mirror_flag=bool(raw.get("MirrorFlag", 0)),
                cur_clock_id=int(raw.get("CurClockId", -1)),
                gyrate_angle=int(raw.get("GyrateAngle", 0)),
                channel=channel,
            )
        except PixooApiError as err:
            raise UpdateFailed(str(err)) from err
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(f"Unexpected response from device: {err}") from err

        _LOGGER.debug("Pixoo state updated: %s", state)
        return state
