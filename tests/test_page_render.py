"""Tests for the page_type dispatcher (components/clock/channel/visualizer/pv/fuel)."""

from __future__ import annotations

from custom_components.pixoo_canvas.page_render import render_configured_page

_RECTANGLE_COMPONENTS = [{"type": "rectangle", "position": [0, 0], "size": [1, 1], "color": "red"}]


class _FakeClient:
    """Records every native/buffer call without touching the network."""

    def __init__(self) -> None:
        self.send_page_calls = 0
        self.clock_calls: list[int] = []
        self.channel_calls: list[int] = []
        self.visualizer_calls: list[int] = []

    async def send_page(self, width: int, rgb_bytes: bytes, scroll_texts=None) -> None:
        self.send_page_calls += 1

    async def set_clock(self, clock_id: int) -> None:
        self.clock_calls.append(clock_id)

    async def set_custom_channel(self, index: int) -> None:
        self.channel_calls.append(index)

    async def set_visualizer(self, position: int) -> None:
        self.visualizer_calls.append(position)


async def test_default_page_type_renders_components(hass):
    """A page with no page_type (or page_type: components) goes through the render engine."""
    client = _FakeClient()

    await render_configured_page(hass, client, {"name": "A", "components": _RECTANGLE_COMPONENTS})

    assert client.send_page_calls == 1


async def test_explicit_components_page_type_renders_components(hass):
    """page_type: components behaves identically to the implicit default."""
    client = _FakeClient()

    await render_configured_page(
        hass, client, {"name": "A", "page_type": "components", "components": _RECTANGLE_COMPONENTS}
    )

    assert client.send_page_calls == 1


async def test_clock_page_type_calls_set_clock(hass):
    """page_type: clock resolves `id` and calls client.set_clock, no buffer push."""
    client = _FakeClient()

    await render_configured_page(hass, client, {"name": "Horloge", "page_type": "clock", "id": 182})

    assert client.clock_calls == [182]
    assert client.send_page_calls == 0


async def test_channel_page_type_calls_set_custom_channel(hass):
    """page_type: channel resolves `id` and calls client.set_custom_channel."""
    client = _FakeClient()

    await render_configured_page(hass, client, {"name": "Chan", "page_type": "channel", "id": 0})

    assert client.channel_calls == [0]


async def test_visualizer_page_type_calls_set_visualizer(hass):
    """page_type: visualizer resolves `id` and calls client.set_visualizer."""
    client = _FakeClient()

    await render_configured_page(hass, client, {"name": "Viz", "page_type": "visualizer", "id": 2})

    assert client.visualizer_calls == [2]


async def test_native_page_id_supports_jinja_template(hass):
    """A native page's `id` can be a Jinja template, resolved at render time."""
    client = _FakeClient()

    await render_configured_page(
        hass, client, {"name": "Horloge", "page_type": "clock", "id": "{{ 100 + 82 }}"}
    )

    assert client.clock_calls == [182]


async def test_native_page_missing_id_is_skipped(hass):
    """A clock/channel/visualizer page without `id` logs a warning and makes no call."""
    client = _FakeClient()

    await render_configured_page(hass, client, {"name": "Horloge", "page_type": "clock"})

    assert client.clock_calls == []
    assert client.send_page_calls == 0


async def test_native_page_invalid_template_is_skipped(hass):
    """A clock/channel/visualizer page whose `id` template fails to render is skipped."""
    client = _FakeClient()

    await render_configured_page(
        hass, client, {"name": "Horloge", "page_type": "clock", "id": "{{ 1 / 0 }}"}
    )

    assert client.clock_calls == []


async def test_pv_page_type_renders_generated_components(hass):
    """page_type: pv builds a components list internally and pushes it."""
    client = _FakeClient()

    await render_configured_page(
        hass, client, {"name": "Solaire", "page_type": "pv", "power": 1200, "storage": 80}
    )

    assert client.send_page_calls == 1


async def test_fuel_page_type_renders_generated_components(hass):
    """page_type: fuel builds a components list internally and pushes it."""
    client = _FakeClient()

    await render_configured_page(
        hass,
        client,
        {"name": "Essence", "page_type": "fuel", "title": "Total", "name1": "Diesel", "price1": "1.75"},
    )

    assert client.send_page_calls == 1


async def test_unknown_page_type_is_skipped(hass):
    """An unrecognized page_type logs a warning and makes no call at all."""
    client = _FakeClient()

    await render_configured_page(hass, client, {"name": "???", "page_type": "not_a_real_type"})

    assert client.send_page_calls == 0
    assert client.clock_calls == []
    assert client.channel_calls == []
    assert client.visualizer_calls == []
