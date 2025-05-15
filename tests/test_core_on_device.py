"""Collection of tests meant to run on a physical device.

Device credentials are specified via the environment variables AIRQ_{IP,PASS,HOSTNAME}.
"""

import os
import re

import aiohttp
import pytest
import pytest_asyncio
from aioairq import AirQ, DeviceLedTheme, DeviceLedThemePatch, NightMode
from aioairq.exceptions import APIAccessDenied
from aioairq.utils import is_time_in_interval

PASS = os.environ.get("AIRQ_PASS", "placeholder_password")
IP = os.environ.get("AIRQ_IP", "192.168.0.0")
HOSTNAME = os.environ.get("AIRQ_HOSTNAME", "")
BR_SET = {"brightness_day": 5, "brightness_night": 0}
BR_NEW = {"brightness_day": 6, "brightness_night": 1}


@pytest_asyncio.fixture()
async def session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest_asyncio.fixture()
async def airq(session):
    return AirQ(IP, PASS, session, timeout=5)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "address",
    [
        IP,
        pytest.param(
            HOSTNAME,
            marks=pytest.mark.skipif(
                not HOSTNAME, reason="AIRQ_HOSTNAME not specified"
            ),
        ),
    ],
)
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
async def test_blink(airq):
    """Test the /blink endpoint and whether it returns the device ID."""
    device_id = await airq.blink()

    assert re.fullmatch("[0-9a-f]+", device_id) is not None


@pytest.mark.asyncio
async def test_device_name(airq):
    """Test getting and setting the device name."""
    previous_device_name = await airq.get_device_name()

    new_device_name = "just-testing"
    await airq.set_device_name(new_device_name)

    device_name_after_setting = await airq.get_device_name()

    await airq.set_device_name(previous_device_name)
    device_name_after_resetting = await airq.get_device_name()

    assert device_name_after_setting == new_device_name
    assert device_name_after_resetting == previous_device_name


@pytest.mark.asyncio
async def test_log(airq):
    """Test getting the log. It should be a list."""
    log = await airq.get_log()

    assert isinstance(log, list)


@pytest.mark.asyncio
async def test_config(airq):
    """Test getting the config. It should be a big dictionary."""
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
async def test_possible_led_themes(airq):
    """Test getting the possible LED themes."""
    possible_led_themes = await airq.get_possible_led_themes()

    expected = {"standard", "VOC", "Humidity"}

    assert not expected.difference(possible_led_themes)


@pytest.mark.asyncio
async def test_get_led_theme(airq):
    """Test getting the current LED theme."""
    led_theme = await airq.get_led_theme()

    assert isinstance(led_theme["left"], str)
    assert isinstance(led_theme["right"], str)


@pytest_asyncio.fixture()
async def airq_automatically_restoring_led_theme(airq):
    # Setup
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
async def test_setting_led_theme(airq_automatically_restoring_led_theme, target_sides):
    previous_led_theme: DeviceLedTheme = (
        await airq_automatically_restoring_led_theme.get_led_theme()
    )
    possible_led_themes = (
        await airq_automatically_restoring_led_theme.get_possible_led_themes()
    )
    unused_led_themes = set(possible_led_themes).difference(
        set(previous_led_theme.values())
    )
    target_theme = dict(zip(target_sides, unused_led_themes))
    await airq_automatically_restoring_led_theme.set_led_theme(
        DeviceLedThemePatch(**target_theme)
    )
    led_theme_after_setting = (
        await airq_automatically_restoring_led_theme.get_led_theme()
    )

    for side, theme in led_theme_after_setting.items():
        assert theme == target_theme.get(side, previous_led_theme[side])


@pytest.mark.asyncio
async def test_cloud_remote(airq):
    """Test setting and getting the "cloud remote" setting."""
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
async def test_time_server_exception(airq):
    """Test setting and getting the time server."""
    if await airq.has_api_access():
        pytest.skip("Test device has API access, not testing for its failure.")
    with pytest.raises(APIAccessDenied):
        await airq.set_time_server("127.0.0.1")


@pytest.mark.asyncio
async def test_time_server(airq):
    """Test setting and getting the time server."""
    if not (await airq.has_api_access()):
        pytest.skip("Cannot test time server setting without API access.")
    previous_value = await airq.get_time_server()

    await airq.set_time_server("127.0.0.1")
    value_after_change = await airq.get_time_server()

    await airq.set_time_server(previous_value)
    value_after_reset = await airq.get_time_server()

    assert value_after_change == "127.0.0.1"
    assert value_after_reset == previous_value


@pytest.mark.asyncio
async def test_night_mode(airq):
    """Test setting and getting the night mode settings."""
    previous_values = await airq.get_night_mode()

    new_values1 = NightMode(
        activated=True,
        start_day="03:47",
        start_night="19:12",
        brightness_day=9.7,
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
        brightness_day=7.0,
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


@pytest_asyncio.fixture(params=[True, False])
async def airq_automatically_restoring_night_mode(airq, request):
    # Store the original
    previous_night_mode = await airq.get_night_mode()

    # Pre-configure
    night_mode_activated = request.param
    await airq.set_night_mode(
        previous_night_mode | BR_SET | {"activated": night_mode_activated}
    )

    yield airq

    await airq.set_night_mode(previous_night_mode)
    restored_night_mode = await airq.get_night_mode()
    assert restored_night_mode == previous_night_mode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "targets",
    [["default"], ["night"], ["default", "night"]],
)
async def test_setting_brightness_config(
    airq_automatically_restoring_night_mode: AirQ, targets: list[str]
):
    _key_map = {"default": "brightness_day", "night": "brightness_night"}
    previous_night_mode = await airq_automatically_restoring_night_mode.get_night_mode()
    # the foolowing is the dictionary to be passed to set_brightness_config
    # and thus has default and/or night as keys
    requested_brightness_config = {
        target: BR_NEW[_key_map[target]] for target in targets
    }
    # ...while this dict "patch" needs to have different keys,
    # i.e. brightness_{day,night}
    expected_night_mode = previous_night_mode | {
        _key_map[target]: BR_NEW[_key_map[target]] for target in targets
    }

    await airq_automatically_restoring_night_mode.set_brightness_config(
        **requested_brightness_config
    )
    updated_night_mode = await airq_automatically_restoring_night_mode.get_night_mode()
    assert updated_night_mode == expected_night_mode


@pytest.mark.asyncio
async def test_setting_current_brightness(
    airq_automatically_restoring_night_mode: AirQ,
):
    br: float = await airq_automatically_restoring_night_mode.get_current_brightness()
    br_new = (br + 1) % 10
    await airq_automatically_restoring_night_mode.set_current_brightness(br_new)
    night_mode = await airq_automatically_restoring_night_mode.get_night_mode()

    if night_mode["activated"] and is_time_in_interval(
        start=night_mode["start_night"], end=night_mode["start_day"]
    ):
        target_key = "brightness_night"
    else:
        target_key = "brightness_day"
    assert night_mode[target_key] == br_new


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, 11, "5.0"])
async def test_setting_current_brightness_wrongly(
    airq_automatically_restoring_night_mode: AirQ, value
):
    with pytest.raises(ValueError):
        await airq_automatically_restoring_night_mode.set_current_brightness(value)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, 11, "5.0"])
@pytest.mark.parametrize(
    "targets",
    [["default"], ["night"], ["default", "night"]],
)
async def test_setting_brightness_config_wrongly(
    airq_automatically_restoring_night_mode: AirQ, value, targets
):
    with pytest.raises(ValueError):
        await airq_automatically_restoring_night_mode.set_brightness_config(
            **{target: value for target in targets}
        )
