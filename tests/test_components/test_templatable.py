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


async def test_expand_parses_list_wrapped_in_stray_whitespace(hass):
    """A multi-block template ({% set %}/{% for %} before the final {{ }}) still parses.

    HA only auto-converts a render to a native list when the whole template
    is one bare {{ }} expression; any {% %} block tags before it leave
    newlines in the rendered string, which is exactly the shape of our
    real-world templatable pages (macros + loops building up a namespace
    list before a trailing {{ ns.list }}).
    """
    component = {
        "type": "templatable",
        "template": (
            "{% set ns = namespace(list=[]) %}\n"
            "{% for i in [1, 2] %}\n"
            "  {% set ns.list = ns.list + "
            "[{'type': 'rectangle', 'position': [i, 0], 'size': [1, 1]}] %}\n"
            "{% endfor %}\n"
            "{{ ns.list }}"
        ),
    }

    result = await templatable.expand(component, hass, None)

    assert result == [
        {"type": "rectangle", "position": [1, 0], "size": [1, 1]},
        {"type": "rectangle", "position": [2, 0], "size": [1, 1]},
    ]


async def test_expand_returns_empty_list_on_template_error(hass):
    """A template that fails to render (e.g. |int on an unavailable sensor) is skipped, not raised."""
    component = {
        "type": "templatable",
        "template": "{{ states('sensor.does_not_exist')|int <= 1 }}",
    }

    result = await templatable.expand(component, hass, None)

    assert result == []
