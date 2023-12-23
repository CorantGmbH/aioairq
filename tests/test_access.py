import os

import aiohttp
import pytest
import pytest_asyncio

from aioairq import AirQ

SUBJECT = "ping"

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
    await airq.get(SUBJECT)
    if repeat_call:
        await airq.get(SUBJECT)
