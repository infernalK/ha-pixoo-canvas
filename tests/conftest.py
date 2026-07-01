"""Fixtures for Pixoo Canvas tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom_components/ during tests."""
    yield
