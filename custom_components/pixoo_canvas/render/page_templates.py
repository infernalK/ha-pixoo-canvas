"""Prebuilt page layouts (`page_type: pv`/`fuel`) built from existing components.

Unlike `page_type: components`, these page types don't take a `components`
list - just a handful of named fields - and are expanded here into the
equivalent `components` list before being handed to the normal render engine.
Field values are passed through as-is (raw or Jinja template strings): the
components they land on (`text.content`, `icon.value`, `progress_bar.value`)
already resolve either on their own, so no templating happens in this module.
"""

from __future__ import annotations

from typing import Any

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
