"""Templatable component: expands a Jinja2 template into a list of components."""

from __future__ import annotations

import ast
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

    if isinstance(rendered, list):
        return rendered

    # HA only auto-converts a render to a native list when the *entire*
    # template is one bare `{{ }}` expression. A template built from
    # `{% set %}`/`{% for %}` blocks before the final `{{ ns.list }}` (as
    # ours all are) can leave stray whitespace around it, so the result
    # stays a string even though it's valid Python list syntax. Try parsing
    # it ourselves before giving up.
    if isinstance(rendered, str):
        try:
            parsed = ast.literal_eval(rendered.strip())
        except (ValueError, SyntaxError):
            pass
        else:
            if isinstance(parsed, list):
                return parsed

    _LOGGER.warning("templatable component did not render to a list, skipping")
    return []
