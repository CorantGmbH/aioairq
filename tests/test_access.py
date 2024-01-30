import os
import re

import aiohttp
import pytest
import pytest_asyncio

from aioairq import AirQ

PASS = os.environ.get("AIRQ_PASS", "placeholder_password")
IP = os.environ.get("AIRQ_IP", "192.168.0.0")
MDNS = os.environ.get("AIRQ_MDNS", "a123f_air-q.local")
HOSTNAME = os.environ.get("AIRQ_HOSTNAME", "air-q")


@pytest_asyncio.fixture()
async def session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("address", [IP, HOSTNAME])
@pytest.mark.parametrize("repeat_call", [False, True])
async def test_dns_caching_by_repeated_calls(address, repeat_call, session):
    """Test if a repeated .get request results in a timeout
    when DNS needs to be resolved / looked up from a cache.
    """
    airq = AirQ(address, PASS, session, timeout=5)

    await airq.get("ping")
    if repeat_call:
        await airq.get("ping")


@pytest.mark.asyncio
async def test_blink(session):
    """Test the /blink endpoint and whether it returns the device ID."""
    airq = AirQ(IP, PASS, session, timeout=5)
    device_id = await airq.blink()

    assert re.fullmatch("[0-9a-f]+", device_id) is not None


@pytest.mark.asyncio
async def test_device_name(session):
    """Test getting and setting the device name."""
    airq = AirQ(IP, PASS, session, timeout=5)
    previous_device_name = await airq.get_device_name()

    new_device_name = "just-testing"
    await airq.set_device_name(new_device_name)

    device_name_after_setting = await airq.get_device_name()

    await airq.set_device_name(previous_device_name)
    device_name_after_resetting = await airq.get_device_name()

    assert device_name_after_setting == new_device_name
    assert device_name_after_resetting == previous_device_name
