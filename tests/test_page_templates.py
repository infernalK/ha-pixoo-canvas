"""Tests for the pv/fuel prebuilt page layout builders."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.page_templates import (
    build_fuel_components,
    build_pv_components,
)


def test_build_pv_components_includes_power_and_storage():
    """The generated components reference the page's power/storage fields."""
    components = build_pv_components({"power": 1200, "storage": 80})

    types = [c["type"] for c in components]
    assert "rectangle" in types
    assert "progress_bar" in types
    assert any(c["type"] == "text" and c["content"] == "1200W" for c in components)
    assert any(c["type"] == "icon" and c.get("value") == 80 for c in components)
    assert any(c["type"] == "progress_bar" and c.get("value") == 80 for c in components)


def test_build_pv_components_omits_discharge_when_absent():
    """No discharge icon/text is generated when the field isn't provided."""
    components = build_pv_components({"power": 100, "storage": 50})

    assert not any(c["type"] == "icon" and c.get("icon") == "mdi:transmission-tower" for c in components)


def test_build_pv_components_includes_discharge_when_present():
    """A discharge field adds its own icon + text."""
    components = build_pv_components({"power": 100, "storage": 50, "discharge": 300})

    assert any(c["type"] == "icon" and c.get("icon") == "mdi:transmission-tower" for c in components)
    assert any(c["type"] == "text" and c["content"] == "300W" for c in components)


def test_build_fuel_components_includes_title_and_rows():
    """The generated components include the title and each filled name/price row."""
    components = build_fuel_components(
        {"title": "Total", "name1": "Diesel", "price1": "1.75", "name2": "SP95", "price2": "1.89"}
    )

    assert any(c["type"] == "text" and c["content"] == "Total" for c in components)
    assert any(c["type"] == "text" and c["content"] == "Diesel" for c in components)
    assert any(c["type"] == "text" and c["content"] == "1.75" for c in components)
    assert any(c["type"] == "text" and c["content"] == "SP95" for c in components)


def test_build_fuel_components_skips_empty_rows():
    """A name2/price2 pair that's entirely absent doesn't generate a row."""
    components = build_fuel_components({"title": "Total", "name1": "Diesel", "price1": "1.75"})

    assert not any(c["type"] == "text" and c["content"] == "SP95" for c in components)


def test_build_fuel_components_includes_status_when_present():
    """A status field adds its own text component."""
    components = build_fuel_components({"title": "Total", "status": "Ouvert"})

    assert any(c["type"] == "text" and c["content"] == "Ouvert" for c in components)
