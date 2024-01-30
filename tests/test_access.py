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

    keys_expected = {"HotspotChannel", "TimeServer", "cloudUpload", "id", "logging", "sensors"}
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


@pytest.mark.asyncio
async def test_set_led_theme(session):
    """Test setting the current LED theme."""
    airq = AirQ(IP, PASS, session, timeout=5)
    previous_led_theme = await airq.get_led_theme()

    # left only
    await airq.set_led_theme_left("CO2")
    led_theme_after_left = await airq.get_led_theme()

    # right only
    await airq.set_led_theme_right("Noise")
    led_theme_after_right = await airq.get_led_theme()

    # both
    await airq.set_led_theme_both("VOC", "PM2.5")
    led_theme_after_both = await airq.get_led_theme()

    # reset
    await airq.set_led_theme_both(previous_led_theme["left"], previous_led_theme["right"])
    led_theme_after_reset = await airq.get_led_theme()

    # asserts
    assert led_theme_after_left["left"] == "CO2"
    assert led_theme_after_left["right"] == previous_led_theme["right"]

    assert led_theme_after_right["left"] == "CO2"
    assert led_theme_after_right["right"] == "Noise"

    assert led_theme_after_both["left"] == "VOC"
    assert led_theme_after_both["right"] == "PM2.5"

    assert led_theme_after_reset["left"] == previous_led_theme["left"]
    assert led_theme_after_reset["right"] == previous_led_theme["right"]
