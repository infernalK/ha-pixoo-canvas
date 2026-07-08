"""Constants for the Pixoo Canvas integration."""

from homeassistant.const import Platform

DOMAIN = "pixoo_canvas"

PLATFORMS = [Platform.SWITCH, Platform.LIGHT, Platform.SENSOR, Platform.SELECT, Platform.BUTTON]

CMD_GET_ALL_CONF = "Channel/GetAllConf"
CMD_GET_CHANNEL = "Channel/GetIndex"
CMD_SET_CHANNEL = "Channel/SetIndex"
CMD_ON_OFF_SCREEN = "Channel/OnOffScreen"
CMD_SET_BRIGHTNESS = "Channel/SetBrightness"
CMD_SEND_HTTP_GIF = "Draw/SendHttpGif"
CMD_RESET_HTTP_GIF_ID = "Draw/ResetHttpGifId"
CMD_SET_ROTATION_ANGLE = "Device/SetScreenRotationAngle"
CMD_SEND_HTTP_TEXT = "Draw/SendHttpText"
CMD_CLEAR_HTTP_TEXT = "Draw/ClearHttpText"
CMD_COMMAND_LIST = "Draw/CommandList"
CMD_SET_CLOCK = "Channel/SetClockSelectId"
CMD_SET_CUSTOM_PAGE = "Channel/SetCustomPageIndex"
CMD_SET_VISUALIZER = "Channel/SetEqPosition"
CMD_PLAY_BUZZER = "Device/PlayBuzzer"
CMD_SET_NOISE_STATUS = "Tools/SetNoiseStatus"
CMD_SYS_REBOOT = "Device/SysReboot"
CMD_SET_MIRROR_MODE = "Device/SetMirrorMode"
CMD_SET_TIMER = "Tools/SetTimer"
CMD_SET_STOPWATCH = "Tools/SetStopWatch"
# NOT "Device/SetAlarm" (what an earlier, since-corrected version of this
# integration used, copied from kmplngj/pixoo-ha without hardware
# verification): confirmed on real hardware to be accepted (the device
# flashes a generic "Save Setting" screen) but never actually rings.
# "Alarm/Set" is the command name found in Divoom's decompiled APK/firmware
# command list (alongside Alarm/Get, Alarm/Del, Alarm/DelAll, Alarm/Change),
# and IS validated by the device - confirmed on real hardware to reject a
# Status/Hour/Minute payload with error_code "Request data illegal json for
# Alarm/Set", rather than accepting it blindly like Device/SetAlarm did.
# _alarm_payload's current EnableFlag/AlarmTime ("HH:MM" string) shape,
# guessed from the field names in github.com/Grayda/pixoo_api's setAlarm()
# (which sends Alarm/Set to Divoom's authenticated *cloud* API, not the
# local device this integration talks to - AlarmTime there is a Unix
# timestamp, adapted to "HH:MM" here since nothing else in this local API
# uses timestamps), is UNVERIFIED and may also be rejected - no known
# source documents this command's real local payload shape; even
# divoom.2a03.party/api/app.html (a community Divoom API reference) lists
# Alarm/Set as a wholly undocumented endpoint.
CMD_SET_ALARM = "Alarm/Set"

DEFAULT_SCAN_INTERVAL = 15
DEFAULT_TIMEOUT = 10

CONF_PAGES_YAML = "pages_yaml"
CONF_DEFAULT_PAGE_DURATION = "default_page_duration"

DEFAULT_PAGE_TYPE = "components"
# Page types that switch the device to a built-in Divoom screen instead of
# pushing a buffer composed by our render engine.
NATIVE_CHANNEL_PAGE_TYPES = frozenset({"clock", "channel", "visualizer"})

PIC_WIDTH = 64
PIC_ID_MAX = 30
DEFAULT_PIC_SPEED_MS = 1000

# Channel/SetIndex,GetIndex's SelectIndex values: the device's 4 top-level channels.
CHANNEL_FACES = 0
CHANNEL_CLOUD = 1
CHANNEL_VISUALIZER = 2
CHANNEL_CUSTOM = 3
CHANNEL_NAMES = {
    CHANNEL_FACES: "Faces",
    CHANNEL_CLOUD: "Cloud",
    CHANNEL_VISUALIZER: "Visualizer",
    CHANNEL_CUSTOM: "Custom",
}

SERVICE_RENDER_PAGE = "render_page"
SERVICE_PLAY_BUZZER = "play_buzzer"
SERVICE_REBOOT_DEVICE = "reboot_device"
SERVICE_START_TIMER = "start_timer"
SERVICE_STOP_TIMER = "stop_timer"
SERVICE_START_STOPWATCH = "start_stopwatch"
SERVICE_STOP_STOPWATCH = "stop_stopwatch"
SERVICE_PAUSE_STOPWATCH = "pause_stopwatch"
SERVICE_RESET_STOPWATCH = "reset_stopwatch"
SERVICE_START_VISUALIZER = "start_visualizer"
SERVICE_STOP_VISUALIZER = "stop_visualizer"
SERVICE_START_SOUND_METER = "start_sound_meter"
SERVICE_STOP_SOUND_METER = "stop_sound_meter"
SERVICE_SET_ALARM = "set_alarm"
SERVICE_STOP_ALARM = "stop_alarm"

DEFAULT_BUZZER_ACTIVE_TIME_MS = 500
DEFAULT_BUZZER_OFF_TIME_MS = 500
DEFAULT_BUZZER_TOTAL_TIME_MS = 3000

DEFAULT_PAGE_DURATION = 15
MIN_PAGE_DURATION = 1
ROTATION_IDLE_POLL_INTERVAL = 10

# Gives the device a moment to actually switch into "drawing mode" after a
# SendHttpGif push before sending a SendHttpText overlay - Divoom's own doc
# says the latter is silently ignored unless the device is already showing
# a custom image, and firmware acknowledging the HTTP request isn't the same
# as it having finished the internal frame swap.
SCROLL_TEXT_SETTLE_DELAY = 0.3
