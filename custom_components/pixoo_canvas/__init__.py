"""The Pixoo Canvas integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PixooClient
from .const import DOMAIN, PLATFORMS
from .coordinator import PixooCoordinator
from .services import async_setup_services, async_unload_services


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pixoo Canvas from a config entry."""
    session = async_get_clientsession(hass)
    client = PixooClient(session, entry.data[CONF_HOST])
    coordinator = PixooCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: PixooCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.rotator.async_stop()
        await async_unload_services(hass)
    return unloaded
