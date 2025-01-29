from unittest.mock import patch
from dataclasses import asdict

import aiohttp
import pytest
import pytest_asyncio
from pytest import fixture, approx

from aioairq import AirQ
from aioairq.core import identify_warming_up_sensors, ComparisonSummary


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


@pytest.mark.parametrize(
    "data,expected",
    [
        (
            {
                "timestamp": 1621223828000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": [63.0, 4.0],
                "temperature": [18.9, 0.6],
            },
            {"co", "o3"},
        ),
        (
            # The following is a strange looking data set but I have seen it.
            # Expected behaviour: consider co & o3 as warming up
            {
                "timestamp": 16212.084000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 1 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 1 s",
                },
                "humidity": [63.26, 4.27],
                "temperature": [18.92, 0.6],
                "co": [0.916, 0.22],
                "o3": [27.17, 2.32],
            },
            {"co", "o3"},
        ),
        (
            {
                "timestamp": 1621226746000,
                "Status": "OK",
                "humidity": [64.0, 4.0],
                "temperature": [18.8, 0.6],
                "co": [0.92, 0.22],
                "o3": [27.228, 2.31],
            },
            set(),
        ),
    ],
)
def test_warmup_sensor_identification(data, expected):
    actual = identify_warming_up_sensors(data)
    assert actual == expected


@pytest.mark.parametrize(
    "previous,current,expected",
    [
        (
            {
                "timestamp": 1621223828000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": [63.0, 4.0],
                "temperature": [18.9, 0.6],
            },
            {
                "timestamp": 1621223838000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": [64.0, 4.0],
                "temperature": [17.9, 0.7],
            },
            ComparisonSummary(
                warming_up={"co", "o3"},
                difference={
                    "timestamp": 10_000,
                    "humidity": [1.0, 0.0],
                    "temperature": [-1.0, 0.1],
                },
            ),
        ),
        # dropped uncertainties
        (
            {
                "timestamp": 1621223828000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": 63.0,
                "temperature": 18.9,
            },
            {
                "timestamp": 1621223838000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": 64.0,
                "temperature": 17.9,
            },
            ComparisonSummary(
                warming_up={"co", "o3"},
                difference={"timestamp": 10_000, "humidity": 1.0, "temperature": -1.0},
            ),
        ),
        # emulate a reboot
        (
            {
                "timestamp": 1621226746000,
                "Status": "OK",
                "humidity": [64.0, 4.0],
                "temperature": [18.8, 0.6],
                "co": [0.9, 0.2],
                "o3": [27.3, 2.3],
            },
            {
                "timestamp": 1621226796000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": [60.0, 4.0],
                "temperature": [10.8, 0.6],
            },
            ComparisonSummary(
                missing_keys={"co", "o3"},
                warming_up={"co", "o3"},
                difference={
                    "timestamp": 50_000,
                    "humidity": [-4.0, 0.0],
                    "temperature": [-8.0, 0.0],
                },
            ),
        ),
        # emulate a disappearance of a sensor
        (
            {
                "timestamp": 1621226746000,
                "Status": "OK",
                "humidity": [64.0, 4.0],
                "temperature": [18.8, 0.6],
                "co": [0.9, 0.2],
                "o3": [27.3, 2.3],
            },
            {
                "timestamp": 1621226796000,
                "Status": {
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": [60.0, 4.0],
                "temperature": [10.8, 0.6],
            },
            ComparisonSummary(
                missing_keys={"co", "o3"},
                warming_up={"o3"},
                unaccountably_missing_keys={"co"},
                difference={
                    "timestamp": 50_000,
                    "humidity": [-4.0, 0.0],
                    "temperature": [-8.0, 0.0],
                },
            ),
        ),
        # emulate a new sensor appearing
        (
            {
                "timestamp": 1621226746000,
                "Status": "OK",
                "humidity": [64.0, 4.0],
                "temperature": [18.8, 0.6],
                "o3": [27.3, 2.3],
            },
            {
                "timestamp": 1621226796000,
                "Status": {
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "co": [0.9, 0.2],
                "humidity": [60.0, 4.0],
                "temperature": [10.8, 0.6],
            },
            ComparisonSummary(
                missing_keys={"o3"},
                warming_up={"o3"},
                new_values={"co": [0.9, 0.2]},
                difference={
                    "timestamp": 50_000,
                    "humidity": [-4.0, 0.0],
                    "temperature": [-8.0, 0.0],
                },
            ),
        ),
        # The following is a strange looking data set but I have seen it.
        # Expected behaviour: consider co & o3 as warming up
        (
            {
                "timestamp": 1621223828000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": 63.0,
                "temperature": 18.9,
            },
            {
                "timestamp": 1621223838000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 1 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 1 s",
                },
                "humidity": 64.0,
                "temperature": 17.9,
                "co": [0.9, 0.2],
                "o3": [27.3, 2.3],
            },
            ComparisonSummary(
                warming_up={"co", "o3"},
                new_values={"co": [0.9, 0.2], "o3": [27.3, 2.3]},
                difference={"timestamp": 10_000, "humidity": 1.0, "temperature": -1.0},
            ),
        ),
        # Sensors completed their warmup
        (
            {
                "timestamp": 1621223828000,
                "Status": {
                    "co": "co sensor still in warm up phase; waiting time = 90 s",
                    "o3": "o3 sensor still in warm up phase; waiting time = 90 s",
                },
                "humidity": 63.0,
                "temperature": 18.9,
            },
            {
                "timestamp": 1621223928000,
                "Status": "OK",
                "humidity": 64.0,
                "temperature": 17.9,
                "co": [0.9, 0.2],
                "o3": [27.3, 2.3],
            },
            ComparisonSummary(
                new_values={"co": [0.9, 0.2], "o3": [27.3, 2.3]},
                difference={"timestamp": 100_000, "humidity": 1.0, "temperature": -1.0},
            ),
        ),
    ],
)
def test_data_comparison(previous, current, expected):
    actual_dict = asdict(ComparisonSummary.compare(current, previous))
    expected_dict = asdict(expected)
    actual_difference = actual_dict.pop("difference")
    expected_difference = expected_dict.pop("difference")
    assert actual_dict == expected_dict
    for sensor_name, actual_diff in actual_difference.items():
        assert actual_diff == approx(expected_difference[sensor_name])
