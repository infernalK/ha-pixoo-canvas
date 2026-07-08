"""Tests for the pv/fuel/pihole prebuilt page layout builders."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.page_templates import (
    build_fuel_components,
    build_pihole_components,
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


def test_build_pihole_components_includes_blocked_and_percentage(hass):
    """The generated components reference the page's blocked/percentage fields."""
    components = build_pihole_components({"blocked": 10501, "percentage": 16.5}, hass)

    types = [c["type"] for c in components]
    assert "rectangle" in types
    assert "progress_bar" in types
    assert any(c["type"] == "text" and c["content"] == "10501" for c in components)
    assert any(c["type"] == "progress_bar" and c.get("value") == 16.5 for c in components)


def test_build_pihole_components_omits_status_icon_when_absent(hass):
    """No status shield icon is generated without a status_entity field."""
    components = build_pihole_components({"blocked": 0, "percentage": 0}, hass)

    shield_icons = [c for c in components if c["type"] == "icon" and "shield" in str(c.get("icon", ""))]
    assert shield_icons == []


def test_build_pihole_components_status_icon_templates_the_entity(hass):
    """A status_entity field builds an is_state() ternary for icon and color."""
    components = build_pihole_components(
        {"blocked": 0, "percentage": 0, "status_entity": "binary_sensor.pi_hole_status"}, hass
    )

    shield = next(c for c in components if c["type"] == "icon" and "shield" in str(c.get("icon", "")))
    assert "is_state('binary_sensor.pi_hole_status', 'on')" in shield["icon"]
    assert "is_state('binary_sensor.pi_hole_status', 'on')" in shield["color"]


def test_build_pihole_components_omits_queries_when_absent(hass):
    """No DNS queries text is generated when the field isn't provided."""
    components = build_pihole_components({"blocked": 0, "percentage": 0}, hass)

    assert not any(c["type"] == "text" and "DNS" in str(c.get("content", "")) for c in components)


def test_build_pihole_components_includes_queries_when_present(hass):
    """A queries field adds its own text component."""
    components = build_pihole_components({"blocked": 0, "percentage": 0, "queries": 63392}, hass)

    assert any(c["type"] == "text" and c["content"] == "63392 DNS" for c in components)


def test_build_pihole_components_label_follows_french_language(hass):
    """The blocked-count label is French when the HA instance is configured for French."""
    hass.config.language = "fr"
    components = build_pihole_components({"blocked": 0, "percentage": 0}, hass)

    assert any(c["type"] == "text" and c["content"] == "bloquées" for c in components)


def test_build_pihole_components_label_falls_back_to_english(hass):
    """An unsupported language falls back to the English label rather than raising."""
    hass.config.language = "de"
    components = build_pihole_components({"blocked": 0, "percentage": 0}, hass)

    assert any(c["type"] == "text" and c["content"] == "blocked" for c in components)
