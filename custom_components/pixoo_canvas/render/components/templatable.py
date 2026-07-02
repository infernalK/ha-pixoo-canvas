"""Templatable component: expands a Jinja2 template into a list of components."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.template import Template

_LOGGER = logging.getLogger(__name__)


async def expand(
    component: dict[str, Any],
    hass: HomeAssistant,
    variables: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Render a component's `template` field and return the resulting component list."""
    template_str = str(component.get("template", "[]"))
    try:
        rendered = Template(template_str, hass).async_render(variables=variables)
    except TemplateError as err:
        _LOGGER.warning("templatable component's template failed to render, skipping: %s", err)
        return []
    if not isinstance(rendered, list):
        _LOGGER.warning("templatable component did not render to a list, skipping")
        return []
    return rendered
