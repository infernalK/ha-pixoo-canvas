"""The Pixoo Canvas integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PixooApiError, PixooClient
from .const import DOMAIN, PLATFORMS
from .coordinator import PixooCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pixoo Canvas from a config entry."""
    session = async_get_clientsession(hass)
    client = PixooClient(session, entry.data[CONF_HOST])
    coordinator = PixooCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    # A fresh PixooClient always starts its local PicID counter at 0, but the
    # device's own counter (which gates SendHttpGif - see reset_gif_id's
    # docstring) survives an HA restart untouched. If the device's last-seen
    # PicID is higher than what this new client starts sending, it can
    # silently ignore every page push - no error, just a screen stuck on
    # whatever it last showed - until the local counter climbs back past
    # PIC_ID_MAX on its own. Resetting explicitly here keeps both sides in
    # sync from the first render after every restart/reload.
    try:
        await client.reset_gif_id()
    except PixooApiError as err:
        _LOGGER.warning("Could not reset the device's GIF id counter at startup: %s", err)

    await coordinator.rotator.async_restore()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry so a new host/scan_interval from options takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: PixooCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.rotator.async_stop()
        await async_unload_services(hass)
    return unloaded
