"""Parsing helpers for the pages YAML stored in a config entry's options."""

from __future__ import annotations

from typing import Any

import yaml

from homeassistant.config_entries import ConfigEntry

from .const import CONF_PAGES_YAML


class PagesYamlError(Exception):
    """Raised when the stored pages YAML is missing, malformed, or has no match."""


def parse_pages(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Parse the config entry's stored pages YAML into a list of page dicts."""
    pages_yaml = entry.options.get(CONF_PAGES_YAML, "")
    try:
        return yaml.safe_load(pages_yaml) or []
    except yaml.YAMLError as err:
        raise PagesYamlError(f"Invalid pages YAML: {err}") from err


def get_page(entry: ConfigEntry, page_name: str) -> dict[str, Any]:
    """Look up a single named page, raising PagesYamlError if none matches."""
    for page in parse_pages(entry):
        if page.get("name") == page_name:
            return page
    raise PagesYamlError(f"No page named {page_name!r} configured")
