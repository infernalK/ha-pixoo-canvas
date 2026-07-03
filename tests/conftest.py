"""Fixtures for Pixoo Canvas tests."""

import pytest

# aiohttp (used by our api.py, via HA's async_get_clientsession) resolves DNS
# through aiodns/pycares, a required homeassistant dependency. The first
# pycares.Channel() ever constructed in the process starts a singleton daemon
# thread that then lives for the rest of the run - harmless, but
# pytest-homeassistant-custom-component snapshots threads before/after each
# test and fails whichever test happens to be the first to trigger it (varies
# with test selection/order). Constructing one here, at collection time
# before any test's snapshot is taken, makes the thread already present for
# every test.
try:
    import pycares

    pycares.Channel()
except ImportError:
    pass


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom_components/ during tests."""
    yield
