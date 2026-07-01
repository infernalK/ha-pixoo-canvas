"""Tests for the templatable render component."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.components import templatable


async def test_expand_returns_rendered_list(hass):
    """A template rendering to a Jinja-native list yields that list of components."""
    component = {
        "type": "templatable",
        "template": "{{ [{'type': 'rectangle', 'position': [0, 0], 'size': [1, 1]}] }}",
    }

    result = await templatable.expand(component, hass, None)

    assert result == [{"type": "rectangle", "position": [0, 0], "size": [1, 1]}]


async def test_expand_returns_empty_list_when_not_a_list(hass):
    """A template that doesn't render to a list is treated as producing nothing."""
    component = {"type": "templatable", "template": "{{ 'not a list' }}"}

    result = await templatable.expand(component, hass, None)

    assert result == []


async def test_expand_uses_variables(hass):
    """Variables passed to expand() are available inside the template."""
    component = {
        "type": "templatable",
        "template": "{{ [{'type': 'rectangle', 'position': [my_x, 0], 'size': [1, 1]}] }}",
    }

    result = await templatable.expand(component, hass, {"my_x": 7})

    assert result[0]["position"] == [7, 0]
