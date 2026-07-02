"""Tests for color resolution, including template-error resilience."""

from __future__ import annotations

from custom_components.pixoo_canvas.render.colors import resolve_color


async def test_resolve_color_literal_list(hass):
    """A literal [r, g, b] sequence is used as-is."""
    assert resolve_color([1, 2, 3], hass, None, default=(9, 9, 9)) == (1, 2, 3)


async def test_resolve_color_css_name(hass):
    """A CSS color name resolves via Pillow's ImageColor."""
    assert resolve_color("red", hass, None, default=(9, 9, 9)) == (255, 0, 0)


async def test_resolve_color_template(hass):
    """A Jinja2 template string is rendered before color resolution."""
    assert resolve_color("{{ 'blue' }}", hass, None, default=(9, 9, 9)) == (0, 0, 255)


async def test_resolve_color_template_error_falls_back_to_default(hass):
    """A template that fails to render (e.g. |int on an unavailable sensor) uses the default."""
    result = resolve_color(
        "{{ states('sensor.does_not_exist')|int }}", hass, None, default=(9, 9, 9)
    )

    assert result == (9, 9, 9)
