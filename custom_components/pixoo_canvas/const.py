"""Constants for the Pixoo Canvas integration."""

from homeassistant.const import Platform

DOMAIN = "pixoo_canvas"

PLATFORMS = [Platform.SWITCH, Platform.LIGHT, Platform.SENSOR]

CMD_GET_ALL_CONF = "Channel/GetAllConf"
CMD_ON_OFF_SCREEN = "Channel/OnOffScreen"
CMD_SET_BRIGHTNESS = "Channel/SetBrightness"

DEFAULT_SCAN_INTERVAL = 15
DEFAULT_TIMEOUT = 10
