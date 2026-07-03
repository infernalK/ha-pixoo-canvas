"""Parsing helpers for the pages YAML stored in a config entry's options."""

from __future__ import annotations

from typing import Any

import yaml

from homeassistant.config_entries import ConfigEntry

from .const import CONF_PAGES_YAML, DEFAULT_PAGE_TYPE, NATIVE_CHANNEL_PAGE_TYPES


class PagesYamlError(Exception):
    """Raised when the stored pages YAML is missing, malformed, or has no match."""


def is_valid_page_shape(page: Any) -> bool:
    """Validate a page dict's structure for its `page_type` (not its `name`).

    `components` (the default, for full backward compatibility) requires a
    `components` list. `clock`/`channel`/`visualizer` instead switch the
    device to one of its built-in screens and require an `id` instead.
    `pv`/`fuel` are prebuilt layouts with their own optional fields - no
    structural requirement here, same as we don't validate `components` list
    contents.
    """
    if not isinstance(page, dict):
        return False

    page_type = str(page.get("page_type", DEFAULT_PAGE_TYPE)).lower()
    if page_type in NATIVE_CHANNEL_PAGE_TYPES:
        return "id" in page
    if page_type == DEFAULT_PAGE_TYPE:
        return isinstance(page.get("components"), list)
    return True


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
