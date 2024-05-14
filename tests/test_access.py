import os
import re

import aiohttp
import pytest
import pytest_asyncio

from aioairq import AirQ, DeviceLedTheme, DeviceLedThemePatch, NightMode

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


@pytest.mark.asyncio
async def test_log(session):
    """Test getting the log. It should be a list."""
    airq = AirQ(IP, PASS, session, timeout=5)
    log = await airq.get_log()

    assert isinstance(log, list)


@pytest.mark.asyncio
async def test_config(session):
    """Test getting the config. It should be a big dictionary."""
    airq = AirQ(IP, PASS, session, timeout=5)
    config = await airq.get_config()

    keys_expected = {
        "HotspotChannel",
        "TimeServer",
        "cloudUpload",
        "id",
        "logging",
        "sensors",
    }
    keys_found = set(config.keys())

    assert isinstance(config, dict)
    assert len(config) > 40
    assert not keys_expected.difference(keys_found)


@pytest.mark.asyncio
async def test_possible_led_themes(session):
    """Test getting the possible LED themes."""
    airq = AirQ(IP, PASS, session, timeout=5)
    possible_led_themes = await airq.get_possible_led_themes()

    expected = {"standard", "VOC", "Humidity"}

    assert not expected.difference(possible_led_themes)


@pytest.mark.asyncio
async def test_get_led_theme(session):
    """Test getting the current LED theme."""
    airq = AirQ(IP, PASS, session, timeout=5)
    led_theme = await airq.get_led_theme()

    assert isinstance(led_theme["left"], str)
    assert isinstance(led_theme["right"], str)


@pytest_asyncio.fixture()
async def async_airq(session):
    # Setup
    airq = AirQ(IP, PASS, session, timeout=5)
    previous_led_theme = await airq.get_led_theme()

    yield airq

    await airq.set_led_theme(previous_led_theme)
    led_theme_after_reset = await airq.get_led_theme()
    assert led_theme_after_reset == previous_led_theme


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target_sides",
    [["left"], ["right"], ["left", "right"]],
)
async def test_setting_led_theme(async_airq, target_sides):
    previous_led_theme: DeviceLedTheme = await async_airq.get_led_theme()
    possible_led_themes = await async_airq.get_possible_led_themes()
    unused_led_themes = set(possible_led_themes).difference(
        set(previous_led_theme.values())
    )
    target_theme = dict(zip(target_sides, unused_led_themes))
    await async_airq.set_led_theme(DeviceLedThemePatch(**target_theme))
    led_theme_after_setting = await async_airq.get_led_theme()

    for side, theme in led_theme_after_setting.items():
        assert theme == target_theme.get(side, previous_led_theme[side])


@pytest.mark.asyncio
async def test_cloud_remote(session):
    """Test setting and getting the "cloud remote" setting."""
    airq = AirQ(IP, PASS, session, timeout=5)
    previous_value = await airq.get_cloud_remote()

    # on
    await airq.set_cloud_remote(True)
    value_after_on = await airq.get_cloud_remote()

    # off
    await airq.set_cloud_remote(False)
    value_after_off = await airq.get_cloud_remote()

    # reset
    await airq.set_cloud_remote(previous_value)
    value_after_reset = await airq.get_cloud_remote()

    assert value_after_on
    assert not value_after_off
    assert value_after_reset == previous_value


@pytest.mark.asyncio
async def test_time_server(session):
    """Test setting and getting the time server."""
    airq = AirQ(IP, PASS, session, timeout=5)
    previous_value = await airq.get_time_server()

    await airq.set_time_server("127.0.0.1")
    value_after_change = await airq.get_time_server()

    await airq.set_time_server(previous_value)
    value_after_reset = await airq.get_time_server()

    assert value_after_change == "127.0.0.1"
    assert value_after_reset == previous_value


@pytest.mark.asyncio
async def test_night_mode(session):
    """Test setting and getting the night mode settings."""
    airq = AirQ(IP, PASS, session, timeout=5)
    previous_values = await airq.get_night_mode()

    new_values1 = NightMode(
        activated=True,
        start_day="03:47",
        start_night="19:12",
        brightness_day=19.7,
        brightness_night=2.3,
        fan_night_off=True,
        wifi_night_off=False,  # Hint: Don't disable Wi-Fi when testing ;-)
        alarm_night_off=True,
    )
    await airq.set_night_mode(new_values1)
    values_after_change1 = await airq.get_night_mode()

    new_values2 = NightMode(
        activated=False,
        start_day="00:00",
        start_night="23:59",
        brightness_day=17.0,
        brightness_night=4.7,
        fan_night_off=False,
        wifi_night_off=True,
        alarm_night_off=False,
    )
    await airq.set_night_mode(new_values2)
    values_after_change2 = await airq.get_night_mode()

    await airq.set_night_mode(previous_values)
    values_after_reset = await airq.get_night_mode()

    assert values_after_change1 == new_values1
    assert values_after_change2 == new_values2
    assert values_after_reset == previous_values
