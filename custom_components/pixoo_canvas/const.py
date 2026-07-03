"""Constants for the Pixoo Canvas integration."""

from homeassistant.const import Platform

DOMAIN = "pixoo_canvas"

PLATFORMS = [Platform.SWITCH, Platform.LIGHT, Platform.SENSOR, Platform.SELECT]

CMD_GET_ALL_CONF = "Channel/GetAllConf"
CMD_ON_OFF_SCREEN = "Channel/OnOffScreen"
CMD_SET_BRIGHTNESS = "Channel/SetBrightness"
CMD_SEND_HTTP_GIF = "Draw/SendHttpGif"
CMD_RESET_HTTP_GIF_ID = "Draw/ResetHttpGifId"
CMD_SET_ROTATION_ANGLE = "Device/SetScreenRotationAngle"
CMD_SEND_HTTP_TEXT = "Draw/SendHttpText"
CMD_CLEAR_HTTP_TEXT = "Draw/ClearHttpText"

DEFAULT_SCAN_INTERVAL = 15
DEFAULT_TIMEOUT = 10

CONF_PAGES_YAML = "pages_yaml"

PIC_WIDTH = 64
PIC_ID_MAX = 30
DEFAULT_PIC_SPEED_MS = 1000

SERVICE_RENDER_PAGE = "render_page"

DEFAULT_PAGE_DURATION = 15
MIN_PAGE_DURATION = 1
ROTATION_IDLE_POLL_INTERVAL = 10
