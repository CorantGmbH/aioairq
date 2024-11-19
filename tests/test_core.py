from unittest.mock import patch

import aiohttp
import pytest
import pytest_asyncio
from pytest import fixture

from aioairq import AirQ


@fixture
def ip():
    return "192.168.0.0"


@fixture
def mdns():
    return "a123f_air-q.local"


@fixture
def passw():
    return "password"


@pytest_asyncio.fixture
async def session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@fixture(params=["ip", "mdns"])
def valid_address(request, ip, mdns):
    return {"ip": ip, "mdns": mdns}[request.param]


@pytest.mark.asyncio
async def test_constructor(valid_address, passw, session):
    airq = AirQ(valid_address, passw, session)
    assert airq.anchor == "http://" + valid_address
    assert not airq._session.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "return_original_keys,data,expected",
    [
        (
            True,
            {"co2": [604.0, 68.1], "Status": "OK", "pm1": [0, 10], "pm2_5": [0, 10]},
            {"co2": [604.0, 68.1], "Status": "OK", "pm1": [0, 10], "pm2_5": [0, 10]},
        ),
        (
            False,
            {"co2": [604.0, 68.1], "Status": "OK", "pm1": [0, 10], "pm2_5": [0, 10]},
            {"co2": [604.0, 68.1], "Status": "OK", "pm1": [0, 10], "pm2_5": [0, 10]},
        ),
        (
            True,
            {
                "co2": [604.0, 68.1],
                "Status": "OK",
                "pm1_SPS30": [0, 10],
                "pm2_5_SPS30": [0, 10],
            },
            {
                "co2": [604.0, 68.1],
                "Status": "OK",
                "pm1_SPS30": [0, 10],
                "pm2_5_SPS30": [0, 10],
            },
        ),
        (
            False,
            {
                "co2": [604.0, 68.1],
                "Status": "OK",
                "pm1_SPS30": [0, 10],
                "pm2_5_SPS30": [0, 10],
            },
            {"co2": [604.0, 68.1], "Status": "OK", "pm1": [0, 10], "pm2_5": [0, 10]},
        ),
    ],
)
async def test_data_key_filtering(
    return_original_keys, data, expected, valid_address, passw, session
):
    airq = AirQ(valid_address, passw, session)
    with patch("aioairq.AirQ.get", return_value=data):
        actual = await airq.get_latest_data(
            return_uncertainties=True, return_original_keys=return_original_keys
        )
    assert actual == expected
