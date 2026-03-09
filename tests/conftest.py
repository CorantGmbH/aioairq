import os

import pytest


def pytest_collection_modifyitems(session, config, items):
    """Skip all on-device tests when AIRQ_IP is not set."""
    if os.environ.get("AIRQ_IP"):
        return
    skip = pytest.mark.skip(reason="Set AIRQ_IP env var to run on-device tests")
    for item in items:
        if item.fspath.basename == "test_core_on_device.py":
            item.add_marker(skip)
