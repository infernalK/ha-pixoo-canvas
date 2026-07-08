"""Prebuilt page layouts (`page_type: pv`/`fuel`/`pihole`/`weather`/`battery`) built
from existing components.

Unlike `page_type: components`, these page types don't take a `components`
list - just a handful of named fields - and are expanded here into the
equivalent `components` list before being handed to the normal render engine.

Most fields are passed through as-is (raw or Jinja template strings): the
components they land on (`text.content`, `icon.value`, `progress_bar.value`)
already resolve either on their own, so no templating happens in this module
for those. The exception is any field that this module itself needs to
branch on synchronously (pick an icon, compute a derived angle, look up a
translated label) - `pihole`'s `status_entity`, and `weather`/`battery`'s
`entity`, are plain entity_ids rather than raw/template values, resolved here
via `hass.states.get(...)` instead of being deferred to the drawn component.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

_BG_COLOR = "black"
_TEXT_COLOR = "white"

_STORAGE_COLOR_THRESHOLDS = [
    {"value": 0, "color": "red"},
    {"value": 20, "color": "orange"},
    {"value": 50, "color": "green"},
]


def build_pv_components(page: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the components for a `page_type: pv` (solar/battery) page.

    Fields: `power`, `storage` (battery %), `discharge` (optional),
    `time` (optional, defaults to the current HH:MM).
    """
    power = page.get("power", "")
    storage = page.get("storage", "")
    discharge = page.get("discharge")
    time = page.get("time", "{{ now().strftime('%H:%M') }}")

    components: list[dict[str, Any]] = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": _BG_COLOR, "filled": True},
        {"type": "text", "position": [40, 2], "content": time, "color": "grey"},
        {"type": "icon", "icon": "mdi:solar-power", "position": [2, 2], "size": 16, "color": "orange"},
        {"type": "text", "position": [20, 8], "content": f"{power}W", "color": _TEXT_COLOR},
        {
            "type": "icon",
            "icon": "mdi:battery",
            "position": [2, 24],
            "size": 16,
            "value": storage,
            "color_thresholds": _STORAGE_COLOR_THRESHOLDS,
        },
        {"type": "text", "position": [20, 30], "content": f"{storage}%", "color": _TEXT_COLOR},
        {
            "type": "progress_bar",
            "position": [2, 46],
            "size": [60, 6],
            "orientation": "horizontal",
            "transition": "smooth",
            "min": 0,
            "max": 100,
            "value": storage,
            "background_color": [40, 40, 40],
            "color_thresholds": _STORAGE_COLOR_THRESHOLDS,
        },
    ]

    if discharge is not None:
        components.append(
            {"type": "icon", "icon": "mdi:transmission-tower", "position": [44, 24], "size": 16, "color": "cyan"}
        )
        components.append({"type": "text", "position": [44, 42], "content": f"{discharge}W", "color": "cyan"})

    return components


def build_fuel_components(page: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the components for a `page_type: fuel` (gas station) page.

    Fields: `title`, `name1`/`price1`, `name2`/`price2`, `name3`/`price3`
    (each pair optional), `status` (optional).
    """
    title = page.get("title", "")
    status = page.get("status")

    components: list[dict[str, Any]] = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": _BG_COLOR, "filled": True},
        {"type": "icon", "icon": "mdi:gas-station", "position": [2, 2], "size": 12, "color": "yellow"},
        {"type": "text", "position": [16, 4], "content": title, "color": "yellow"},
    ]

    rows = (
        (page.get("name1"), page.get("price1")),
        (page.get("name2"), page.get("price2")),
        (page.get("name3"), page.get("price3")),
    )
    y = 18
    for name, price in rows:
        if name is None and price is None:
            continue
        components.append({"type": "text", "position": [2, y], "content": str(name or ""), "color": _TEXT_COLOR})
        components.append({"type": "text", "position": [40, y], "content": str(price or ""), "color": _TEXT_COLOR})
        y += 10

    if status is not None:
        components.append({"type": "text", "position": [2, 54], "content": str(status), "color": "grey"})

    return components


_PIHOLE_COLOR_THRESHOLDS = [
    {"value": 0, "color": "red"},
    {"value": 10, "color": "orange"},
    {"value": 20, "color": "green"},
]

# Kept intentionally small (just the languages this integration's maintainer
# can vouch for) rather than a full translation framework - falls back to
# English for anything else. See build_pihole_components.
_PIHOLE_BLOCKED_LABEL = {
    "en": "blocked",
    "fr": "bloquées",
}
_PIHOLE_DEFAULT_LANGUAGE = "en"


def _pihole_blocked_label(hass: HomeAssistant) -> str:
    """The 'blocked' label in the HA instance's configured language (English fallback)."""
    language = (hass.config.language or "").split("-")[0].lower()
    return _PIHOLE_BLOCKED_LABEL.get(language, _PIHOLE_BLOCKED_LABEL[_PIHOLE_DEFAULT_LANGUAGE])


def build_pihole_components(page: dict[str, Any], hass: HomeAssistant) -> list[dict[str, Any]]:
    """Build the components for a `page_type: pihole` (ad-blocking dashboard) page.

    Fields: `blocked` (ads blocked today), `percentage` (blocking rate, 0-100),
    `queries` (DNS queries today, optional). `status_entity` (optional) is the
    only field that's an entity_id rather than a raw/template value: it's a
    binary_sensor reflecting whether Pi-hole is active, used to build the
    on/off shield icon+color switch (`is_state(...)`) here rather than asking
    the caller to hand-write that ternary themselves.

    Unlike `build_pv_components`/`build_fuel_components` (which never need a
    word at all - just icons and numbers/units like `W`/`%`), the ads-blocked
    count reads better with a short label next to it. That label is picked
    from `hass.config.language` rather than hardcoded, so it doesn't impose
    French (or any other language) on a differently-configured HA instance.
    """
    blocked = page.get("blocked", "")
    percentage = page.get("percentage", "")
    queries = page.get("queries")
    status_entity = page.get("status_entity")

    components: list[dict[str, Any]] = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": _BG_COLOR, "filled": True},
        {"type": "icon", "icon": "mdi:pi-hole", "position": [4, 2], "size": 16, "color": "#96060B"},
        {"type": "text", "position": [22, 4], "content": "Pi", "color": _TEXT_COLOR},
    ]

    if status_entity is not None:
        components.append(
            {
                "type": "icon",
                "position": [44, 2],
                "size": 16,
                "icon": f"{{{{ 'mdi:shield-check' if is_state('{status_entity}', 'on') else 'mdi:shield-off' }}}}",
                "color": f"{{{{ '#00FF00' if is_state('{status_entity}', 'on') else '#FF0000' }}}}",
            }
        )

    components.extend(
        [
            {"type": "text", "position": [32, 17], "align": "center", "content": f"{blocked}", "color": "#FF4444"},
            {
                "type": "text",
                "position": [32, 27],
                "align": "center",
                "content": _pihole_blocked_label(hass),
                "color": "#888888",
                "font": "matrix_chunky_6",
            },
            {
                "type": "progress_bar",
                "position": [4, 40],
                "size": [56, 6],
                "min": 0,
                "max": 50,
                "value": percentage,
                "background_color": [40, 40, 40],
                "color_thresholds": _PIHOLE_COLOR_THRESHOLDS,
            },
            {"type": "text", "position": [32, 49], "align": "center", "content": f"{percentage}%", "color": _TEXT_COLOR},
        ]
    )

    if queries is not None:
        components.append(
            {"type": "text", "position": [32, 57], "align": "center", "content": f"{queries} DNS", "color": "grey"}
        )

    return components


_WEATHER_ICON_BY_CONDITION = {
    "clear-night": "mdi:weather-night",
    "cloudy": "mdi:weather-cloudy",
    "exceptional": "mdi:alert-circle-outline",
    "fog": "mdi:weather-fog",
    "hail": "mdi:weather-hail",
    "lightning": "mdi:weather-lightning",
    "lightning-rainy": "mdi:weather-lightning-rainy",
    "partlycloudy": "mdi:weather-partly-cloudy",
    "pouring": "mdi:weather-pouring",
    "rainy": "mdi:weather-rainy",
    "snowy": "mdi:weather-snowy",
    "snowy-rainy": "mdi:weather-snowy-rainy",
    "sunny": "mdi:weather-sunny",
    "windy": "mdi:weather-windy",
    "windy-variant": "mdi:weather-windy-variant",
}
_WEATHER_COLOR_BY_CONDITION = {
    "clear-night": "#8899CC",
    "cloudy": "#AAAAAA",
    "exceptional": "#FF4444",
    "fog": "#AAAAAA",
    "hail": "#88CCFF",
    "lightning": "#FFCC00",
    "lightning-rainy": "#FFCC00",
    "partlycloudy": "#CCCCCC",
    "pouring": "#3399FF",
    "rainy": "#3399FF",
    "snowy": "#FFFFFF",
    "snowy-rainy": "#CCEEFF",
    "sunny": "#FFCC00",
    "windy": "#CCCCCC",
    "windy-variant": "#CCCCCC",
}
_WEATHER_DEFAULT_ICON = "mdi:weather-cloudy"
_WEATHER_DEFAULT_COLOR = "#AAAAAA"


def _format_number(value: Any) -> str:
    """`value` as a compact number string, or its plain str() if it isn't numeric."""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)


def build_weather_components(page: dict[str, Any], hass: HomeAssistant) -> list[dict[str, Any]]:
    """Build the components for a `page_type: weather` page.

    Field: `entity` (required) - a `weather.*` entity_id. Home Assistant's
    Weather platform guarantees `temperature`/`humidity` as state attributes
    on every weather entity regardless of integration, so condition,
    temperature and humidity are all read from that one entity - nothing
    else to configure for the common case. The condition keys match HA's own
    `ATTR_CONDITION_*` constants (`sunny`, `partlycloudy`, `rainy`, ...).
    """
    entity_id = page.get("entity")
    state = hass.states.get(entity_id) if entity_id else None
    condition = state.state if state is not None else None
    temperature = state.attributes.get("temperature") if state is not None else None
    humidity = state.attributes.get("humidity") if state is not None else None

    icon = _WEATHER_ICON_BY_CONDITION.get(condition or "", _WEATHER_DEFAULT_ICON)
    color = _WEATHER_COLOR_BY_CONDITION.get(condition or "", _WEATHER_DEFAULT_COLOR)

    components: list[dict[str, Any]] = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": _BG_COLOR, "filled": True},
        {"type": "icon", "icon": icon, "position": [16, 2], "size": 28, "color": color},
        {
            "type": "text",
            "position": [32, 34],
            "align": "center",
            "content": f"{_format_number(temperature)}°" if temperature is not None else "",
            "color": _TEXT_COLOR,
        },
    ]

    if humidity is not None:
        components.append({"type": "icon", "icon": "mdi:water-percent", "position": [2, 48], "size": 14, "color": "#3399FF"})
        components.append(
            {"type": "text", "position": [18, 51], "content": f"{_format_number(humidity)}%", "color": _TEXT_COLOR}
        )

    return components


_BATTERY_COLOR_THRESHOLDS = [
    {"value": 0, "color": "red"},
    {"value": 20, "color": "orange"},
    {"value": 50, "color": "green"},
]


def _read_percentage(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """The numeric state of `entity_id`, or None if missing/non-numeric."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def build_battery_components(page: dict[str, Any], hass: HomeAssistant) -> list[dict[str, Any]]:
    """Build the components for a `page_type: battery` (generic charge gauge) page.

    Field: `entity` (required) - any entity whose state is a 0-100 charge
    percentage (most battery sensors qualify - vacuum robots, phones synced
    via a companion app, standalone battery sensors...). `label` (optional,
    any language - it's caller-supplied, like fuel's `title`) - a short name
    shown under the gauge, e.g. "Robot".

    Unlike `pv`'s battery icon+bar, this draws a circular gauge with the
    `arc` component - a deliberate showcase now that `arc` exists (it postdates
    `pv`). `entity` is resolved here (not a raw/template value) because the
    gauge's swept angle is derived from the percentage in plain Python -
    doing that math in Jinja would mean embedding one template's output
    inside another, which isn't valid Jinja.
    """
    entity_id = page.get("entity")
    label = page.get("label")
    value = _read_percentage(hass, entity_id)
    end_angle = (value * 3.6) if value is not None else 0

    components: list[dict[str, Any]] = [
        {"type": "rectangle", "position": [0, 0], "size": [64, 64], "color": _BG_COLOR, "filled": True},
        {
            "type": "arc",
            "center": [32, 28],
            "radius": 20,
            "start_angle": 0,
            "end_angle": end_angle,
            "thickness": 4,
            "value": value,
            "color_thresholds": _BATTERY_COLOR_THRESHOLDS,
        },
        {
            "type": "text",
            "position": [32, 24],
            "align": "center",
            "content": f"{value:.0f}%" if value is not None else "",
            "color": _TEXT_COLOR,
        },
    ]

    if label is not None:
        components.append(
            {"type": "text", "position": [32, 54], "align": "center", "content": str(label), "color": "grey"}
        )

    return components
