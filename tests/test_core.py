import asyncio
import json
import time
import zlib
from dataclasses import asdict
from math import isclose
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
from aiohttp.client_exceptions import ClientConnectionError
import pytest
import pytest_asyncio
from pytest import approx, fixture

from aioairq import AirQ
from aioairq.core import ComparisonSummary, identify_warming_up_sensors
from aioairq.encrypt import AESCipher

TIMEOUT_MAX = 5
HOST_OR_DEVID = "ca1fe"  # ambiguity: is it a hostname or device ID?


@fixture
def ip():
    return "192.168.0.0"


@fixture
def mdns():
    return "a123f_air-q.local"


@fixture
def device_id():
    return "a123f"


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
async def test_constructor_uses_address_as_is(passw, session):
    """__init__ must never rewrite the address, even if it looks like a device ID."""
    airq = AirQ(HOST_OR_DEVID, passw, session)
    assert airq.address == HOST_OR_DEVID
    assert airq.anchor == "http://" + HOST_OR_DEVID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device_id_input,expected_address",
    [
        ("b4bca", "b4bca_air-q.local"),
        ("A1B2C", "a1b2c_air-q.local"),
    ],
)
async def test_from_device_id(device_id_input, expected_address, passw, session):
    airq = AirQ.from_device_id(device_id_input, passw, session)
    assert airq.address == expected_address
    assert airq.anchor == "http://" + expected_address


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_device_id",
    [
        "192.168.0.1",
        "b4bca_air-q.local",
        "abcdef1234",
        "xyz",
        "ghijk",
    ],
)
async def test_from_device_id_rejects_invalid(bad_device_id, passw, session):
    with pytest.raises(ValueError, match="expected 5 hexadecimal"):
        AirQ.from_device_id(bad_device_id, passw, session)


def _fake_get_json_and_decode(reachable_address):
    """Return a side-effect for ``_get_json_and_decode`` that simulates DNS.

    Only requests whose ``self.address`` equals *reachable_address*
    succeed (returning an empty dict); all others raise
    ``ClientConnectionError``, as if the hostname didn't resolve.
    """

    async def _impl(self, relative_url):
        if self.address != reachable_address:
            raise ClientConnectionError(f"Cannot connect to {self.address}")
        return {}

    return _impl


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "true_address,passed_address,expected_call_number",
    [
        (HOST_OR_DEVID, HOST_OR_DEVID, 2),  # is a true hostname
        (f"{HOST_OR_DEVID}_air-q.local", HOST_OR_DEVID, 1),  # is the device 5 hex ID
    ],
)
async def test_connect_with_device_id_falls_back_to_raw_hostname(
    true_address, passed_address, expected_call_number, passw, session
):
    """connect(HOST_OR_DEVID) tries mDNS first, then falls back to HOST_OR_DEVID.

    The fake ``_get_json_and_decode`` only allows true_address to connect.
    """
    with patch.object(
        AirQ,
        "_get_json_and_decode",
        autospec=True,
        side_effect=_fake_get_json_and_decode(true_address),
    ) as mock:
        airq = await AirQ.connect(passed_address, passw, session, timeout=2)

    assert airq.address == true_address
    assert mock.call_count == expected_call_number


@pytest.mark.asyncio
async def test_connect_with_ip(valid_address, passw, session):
    """connect() with a non-device-ID address skips the mDNS detour."""
    with patch.object(
        AirQ,
        "_get_json_and_decode",
        autospec=True,
        side_effect=_fake_get_json_and_decode(valid_address),
    ) as mock:
        airq = await AirQ.connect(valid_address, passw, session, timeout=2)

    assert airq.address == valid_address
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_connect_both_unreachable(passw, session):
    """connect(HOST_OR_DEVID) raises ClientConnectionError when nothing is reachable."""
    with patch.object(
        AirQ,
        "_get_json_and_decode",
        autospec=True,
        side_effect=_fake_get_json_and_decode("__nothing__"),
    ):
        with pytest.raises(ClientConnectionError):
            await AirQ.connect(HOST_OR_DEVID, passw, session, timeout=2)


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "device_name",
    [
        "FW D\u00f6v Ind. \U0001f601",  # "FW Döv Ind. 😁" — contains non-BMP emoji
        "Schr\u00f6dinger \U0001f408\u200d\u2b1b",  # "Schrödinger 🐈‍⬛"
    ],
)
async def test_set_device_name_no_surrogates(
    valid_address, passw, session, device_name
):
    """Verify that setting the device name does not produce UTF-16 surrogate escapes.

    json.dumps with ensure_ascii=True (the default) encodes non-BMP characters
    like emoji as surrogate pairs (e.g. \\ud83d\\ude01). If the device firmware
    does a naive JSON parse, these surrogates get stored as-is, corrupting the name.
    """
    airq = AirQ(valid_address, passw, session)
    aes = AESCipher(passw)

    captured_data = {}

    mock_response = AsyncMock()
    mock_response.text = AsyncMock(
        return_value=json.dumps({"content": aes.encode('"OK"')})
    )

    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_cm.__aexit__ = AsyncMock(return_value=False)

    def fake_post(*args, **kwargs):
        captured_data["payload"] = kwargs.get(
            "data", args[1] if len(args) > 1 else None
        )
        return mock_post_cm

    with patch.object(session, "post", side_effect=fake_post):
        await airq.set_device_name(device_name)

    # Decrypt the payload to get the raw JSON string sent to the device
    encrypted = captured_data["payload"].removeprefix("request=")
    raw_json = aes.decode(encrypted)

    # The raw JSON must not contain surrogate escapes like \ud83d\ude01
    assert (
        "\\ud" not in raw_json.lower()
    ), f"Surrogate escape found in JSON sent to device: {raw_json!r}"
    # Verify the name round-trips correctly through the JSON
    parsed = json.loads(raw_json)
    assert parsed["devicename"] == device_name


@pytest_asyncio.fixture
async def hanging_server():
    """
    TCP server that accepts connections but never sends data.
    This makes HTTP clients wait forever for the status line / headers.
    """
    hang_for_seconds = TIMEOUT_MAX * 10

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            # Keep the connection open; don't read or write HTTP data.
            await asyncio.sleep(hang_for_seconds)
        finally:
            try:
                # Ask asyncio to close the underlying transport...
                writer.close()
                # ...then wait for it to do so
                await writer.wait_closed()
                # Also, ignore any possible edge case during this teardown
            except Exception:
                pass

    # pick any free ephemeral port on localhost and bind the server to it
    server = await asyncio.start_server(handler, host="127.0.0.1", port=0)
    # get the actual selected port
    port = server.sockets[0].getsockname()[1]
    try:
        yield ("127.0.0.1", port)
    finally:
        server.close()
        server.wait_closed()


@pytest.mark.asyncio
async def test_hanging_response_triggers_total_timeout(hanging_server, session):
    """Test that AirQ respects its timeout when querying a hanging server.

    Hanging server will acknowledge the connection but won't respond to read request.
    This test checks that the airq respects the timeout that was specified to it.
    """

    timeout_expected = TIMEOUT_MAX / 10
    host, port = hanging_server
    airq = AirQ(f"{host}:{port}", "dummy_password", session, timeout=timeout_expected)

    started = time.perf_counter()

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(airq.get("ping"), TIMEOUT_MAX)

    elapsed = time.perf_counter() - started

    assert isclose(
        elapsed, timeout_expected, abs_tol=0.1, rel_tol=0.1
    ), f"Elapsed {elapsed:.3f}s suggests no read/total timeout was enforced"


# ---------------------------------------------------------------------------
# Helpers for historical data tests
# ---------------------------------------------------------------------------


def _make_get_side_effect(responses: list[str]):
    """Return a side_effect function that feeds session.get() calls one by one."""
    it = iter(responses)

    def fake_get(*args, **kwargs):
        text = next(it)
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value=text)
        mock_response.raise_for_status = Mock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        return mock_cm

    return fake_get


def _make_raw_file_by_route(route_to_response: dict[str, str]):
    """Return a side_effect for ``_get_raw_file`` that dispatches by route."""

    async def fake(path, route="file"):
        if route in route_to_response:
            return route_to_response[route]
        raise AssertionError(f"Unexpected route: {route}")

    return fake


SAMPLE_RECORDS = [
    {"timestamp": 1715000000000, "co2": [604.0, 68.1], "Status": "OK"},
    {"timestamp": 1715000120000, "co2": [610.0, 70.0], "Status": "OK"},
]


# ---------------------------------------------------------------------------
# get_historical_files_list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_historical_files_list_root_filters_non_numeric(
    valid_address, passw, session
):
    """Root listing should only return numeric year entries."""
    airq = AirQ(valid_address, passw, session)

    all_entries = ["2023", "2024", "2025", ".zlib", ".uncrypt", "logs", "proc", "csv"]
    encrypted = airq.aes.encode(json.dumps(all_entries))

    with patch.object(session, "get", side_effect=_make_get_side_effect([encrypted])):
        result = await airq.get_historical_files_list()

    assert result == ["2023", "2024", "2025"]


@pytest.mark.asyncio
async def test_historical_files_list_subpath_returns_all(valid_address, passw, session):
    """Sub-path listings should be returned as-is."""
    airq = AirQ(valid_address, passw, session)

    months = ["1", "2", "3", "12"]
    encrypted = airq.aes.encode(json.dumps(months))

    with patch.object(session, "get", side_effect=_make_get_side_effect([encrypted])):
        result = await airq.get_historical_files_list("2024")

    assert result == months


# ---------------------------------------------------------------------------
# _parse_historical_lines
#
# Pure method: no I/O, no mocking. Tested directly to cover line format
# variations (plain JSON, AES-encrypted) and edge cases (empty input,
# trailing blank lines) without routing through the full fetch pipeline.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lines,expected",
    [
        # plain JSON lines
        (
            [json.dumps(r) for r in SAMPLE_RECORDS],
            SAMPLE_RECORDS,
        ),
        # empty input
        ([], []),
        # blank lines are filtered out
        (
            [json.dumps(SAMPLE_RECORDS[0]), "", "", json.dumps(SAMPLE_RECORDS[1]), ""],
            SAMPLE_RECORDS,
        ),
    ],
)
def test_parse_historical_lines_plain_json(
    valid_address, passw, session, lines, expected
):
    """Plain JSON lines (unencrypted storage) are parsed directly."""
    airq = AirQ(valid_address, passw, session)
    assert airq._parse_historical_lines(lines) == expected


def test_parse_historical_lines_encrypted(valid_address, passw, session):
    """AES-encrypted lines are decrypted before JSON parsing."""
    airq = AirQ(valid_address, passw, session)
    encrypted_lines = [airq.aes.encode(json.dumps(r)) for r in SAMPLE_RECORDS]
    assert airq._parse_historical_lines(encrypted_lines) == SAMPLE_RECORDS


# ---------------------------------------------------------------------------
# _fetch_compressed_lines
#
# Tests the three possible outcomes of requesting /file_zlib:
# success (returns lines), HTTP 404 (returns None to signal fallback),
# invalid zlib payload (returns None). Non-404 HTTP errors must propagate.
# Patching is done at _get_raw_file level — one layer above the network.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_compressed_lines_success(valid_address, passw, session):
    """Happy path: /file_zlib returns a valid zlib blob."""
    airq = AirQ(valid_address, passw, session)
    text = "\n".join(json.dumps(r) for r in SAMPLE_RECORDS)
    compressed = zlib.compress(text.encode("utf-8"))
    encrypted = airq.aes.encode_bytes(compressed)

    with patch.object(
        airq,
        "_get_raw_file",
        side_effect=_make_raw_file_by_route({"file_zlib": encrypted}),
    ):
        lines = await airq._fetch_compressed_lines("2024/5/12/1715000000")

    assert lines is not None
    assert airq._parse_historical_lines(lines) == SAMPLE_RECORDS


@pytest.mark.asyncio
async def test_fetch_compressed_lines_404(valid_address, passw, session):
    """HTTP 404 from /file_zlib returns None (signal to fall back)."""
    airq = AirQ(valid_address, passw, session)

    async def raise_404(path, route="file"):
        raise aiohttp.ClientResponseError(
            request_info=Mock(real_url=f"{airq.anchor}/file_zlib"),
            history=(),
            status=404,
            message="Not Found",
        )

    with patch.object(airq, "_get_raw_file", side_effect=raise_404):
        result = await airq._fetch_compressed_lines("2024/5/12/1715000000")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_compressed_lines_bad_zlib(valid_address, passw, session):
    """Invalid zlib payload returns None (signal to fall back)."""
    airq = AirQ(valid_address, passw, session)
    bad_zlib = airq.aes.encode("this is not zlib data")

    with patch.object(
        airq,
        "_get_raw_file",
        side_effect=_make_raw_file_by_route({"file_zlib": bad_zlib}),
    ):
        result = await airq._fetch_compressed_lines("2024/5/12/1715000000")

    assert result is None


@pytest.mark.asyncio
async def test_fetch_compressed_lines_non_404_error_propagates(
    valid_address, passw, session
):
    """Non-404 HTTP errors (e.g. 500) must not be swallowed."""
    airq = AirQ(valid_address, passw, session)

    async def raise_500(path, route="file"):
        raise aiohttp.ClientResponseError(
            request_info=Mock(real_url=f"{airq.anchor}/file_zlib"),
            history=(),
            status=500,
            message="Internal Server Error",
        )

    with patch.object(airq, "_get_raw_file", side_effect=raise_500):
        with pytest.raises(aiohttp.ClientResponseError, match="500"):
            await airq._fetch_compressed_lines("2024/5/12/1715000000")


# ---------------------------------------------------------------------------
# get_historical_file (orchestrator)
#
# The orchestrator's job is call routing: try compressed, fall back to plain,
# parse. The fallback logic itself is tested above in _fetch_compressed_lines.
# Here we patch the private fetch methods to verify the orchestration contract
# without duplicating zlib/HTTP concerns.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_historical_file_uses_compressed_when_available(
    valid_address, passw, session
):
    """compressed=True and compressed data available: only _fetch_compressed_lines is called."""
    airq = AirQ(valid_address, passw, session)
    sample_lines = [json.dumps(r) for r in SAMPLE_RECORDS]

    with (
        patch.object(
            airq, "_fetch_compressed_lines", return_value=sample_lines
        ) as mock_compressed,
        patch.object(airq, "_fetch_plain_lines") as mock_plain,
    ):
        result = await airq.get_historical_file("2024/5/12/1715000000")

    mock_compressed.assert_awaited_once_with("2024/5/12/1715000000")
    mock_plain.assert_not_awaited()
    assert result == SAMPLE_RECORDS


@pytest.mark.asyncio
async def test_get_historical_file_falls_back_to_plain(valid_address, passw, session):
    """compressed=True but compressed unavailable: falls back to _fetch_plain_lines."""
    airq = AirQ(valid_address, passw, session)
    sample_lines = [json.dumps(r) for r in SAMPLE_RECORDS]

    with (
        patch.object(
            airq, "_fetch_compressed_lines", return_value=None
        ) as mock_compressed,
        patch.object(
            airq, "_fetch_plain_lines", return_value=sample_lines
        ) as mock_plain,
    ):
        result = await airq.get_historical_file("2024/5/12/1715000000")

    mock_compressed.assert_awaited_once_with("2024/5/12/1715000000")
    mock_plain.assert_awaited_once_with("2024/5/12/1715000000")
    assert result == SAMPLE_RECORDS


@pytest.mark.asyncio
async def test_get_historical_file_skips_compressed_when_disabled(
    valid_address, passw, session
):
    """compressed=False: skips _fetch_compressed_lines entirely."""
    airq = AirQ(valid_address, passw, session)
    sample_lines = [json.dumps(r) for r in SAMPLE_RECORDS]

    with (
        patch.object(airq, "_fetch_compressed_lines") as mock_compressed,
        patch.object(
            airq, "_fetch_plain_lines", return_value=sample_lines
        ) as mock_plain,
    ):
        result = await airq.get_historical_file(
            "2024/5/12/1715000000", compressed=False
        )

    mock_compressed.assert_not_awaited()
    mock_plain.assert_awaited_once_with("2024/5/12/1715000000")
    assert result == SAMPLE_RECORDS
