from __future__ import annotations

import json
from typing import Any, List, Literal, TypedDict

import aiohttp

from aioairq.encrypt import AESCipher
from aioairq.exceptions import InvalidAirQResponse, InvalidIpAddress
from aioairq.utils import is_valid_ipv4_address


class DeviceInfo(TypedDict):
    """Container for device information"""

    id: str
    name: str | None
    model: str | None
    suggested_area: str | None
    sw_version: str | None
    hw_version: str | None

class LedTheme(TypedDict):
    """Container holding the LED themes"""
    left: str
    right: str

class AirQ:
    _supported_routes = ["config", "log", "data", "average", "ping"]

    def __init__(
        self,
        address: str,
        passw: str,
        session: aiohttp.ClientSession,
        timeout: float = 15,
    ):
        """Class representing the API for a single AirQ device

        The class holds the AESCipher object, responsible for message decoding,
        as well as the anchor of the http address to base further requests on

        Parameters
        ----------
        address : str
            Either the IP address of the device, or its mDNS.
            Device's IP might be a more robust option (across the variety of routers)
        passw : str
            Device's password
        session : aiohttp.ClientSession
            Session used to communicate to the device. Should be managed by the user
        timeout : float
            Maximum time in seconds used by `session.get` to connect to the device
            before `aiohttp.ServerTimeoutError` is raised. Default: 15 seconds.
            Hitting the timeout be an indication that the device and the host are not
            on the same WiFi
        """

        self.address = address
        self.anchor = "http://" + self.address
        self.aes = AESCipher(passw)
        self._session = session
        self._timeout = aiohttp.ClientTimeout(connect=timeout)

    async def blink(self) -> str:
        """Let the device blink in rainbow colors for a short amount of time.

        Returns the device's ID.
        This function can be used to identify a device, when you have multiple devices.
        """
        json_data = await self._get_json("/blink")

        return json_data["id"]

    async def validate(self) -> None:
        """Test if the password provided to the constructor is valid.

        Raises InvalidAuth if the password is not correct.
        This is merely a convenience function, relying on the exception being
        raised down the stack (namely by AESCipher.decode from within self.get)
        """
        await self.get("ping")

    async def restart(self) -> None:
        """Restarts the device."""
        post_json_data = {"reset": True}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: reset command received: will reset device after all setting changes have been applied."

    async def shutdown(self) -> None:
        """Shuts the device down."""
        post_json_data = {"shutdown": True}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: shutdown command received: will shutdown device after all setting changes have been applied."

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.address})"

    async def fetch_device_info(self) -> DeviceInfo:
        """Fetch condensed device description"""
        config: dict = await self.get("config")
        room_type = config.get("RoomType")

        try:
            # The only required field. Should not really be missing, just a precaution
            device_id = config["id"]
        except KeyError:
            raise InvalidAirQResponse

        return DeviceInfo(
            id=device_id,
            name=config.get("devicename"),
            model=config.get("type"),
            suggested_area=room_type.replace("-", " ").title() if room_type else None,
            sw_version=config.get("air-Q-Software-Version"),
            hw_version=config.get("air-Q-Hardware-Version"),
        )

    @staticmethod
    def drop_uncertainties_from_data(data: dict) -> dict:
        """Filter returned dict and substitute [value, uncertainty] with the value.

        The device attempts to estimate the uncertainty, or error, of certain readings.
        These readings are returned as tuples of (value, uncertainty). Often, the latter
        is not desired, and this is a convenience method to homogenise the dict a little
        """
        # `if v else None` is a precaution for the case of v being an empty list
        # (which ought not to happen really...)
        return {
            k: (v[0] if v else None) if isinstance(v, (list, tuple)) else v
            for k, v in data.items()
        }

    @staticmethod
    def clip_negative_values(data: dict) -> dict:
        def clip(value):
            if isinstance(value, list):
                return [max(0, value[0]), value[1]]
            elif isinstance(value, (float, int)):
                return max(0, value)
            else:
                return value

        return {k: clip(v) for k, v in data.items()}

    async def get_latest_data(
        self,
        return_average=True,
        clip_negative_values=True,
        return_uncertainties=False,
    ):
        data = await self.get("average" if return_average else "data")
        if clip_negative_values:
            data = self.clip_negative_values(data)
        if not return_uncertainties:
            data = self.drop_uncertainties_from_data(data)
        return data

    async def get(self, subject: str) -> dict:
        """Return the given subject from the air-Q device.

        This function only works on a limited set of subject specified in _supported_routes.
        Prefer using more specialized functions."""
        if subject not in self._supported_routes:
            raise NotImplementedError(
                "AirQ.get() is currently limited to a set of requests, returning "
                f"a dict with a key 'content' (namely {self._supported_routes})."
            )

        return await self._get_json_and_decode("/" + subject)

    async def _get_json(self, relative_url: str) -> dict:
        """Executes a GET request to the air-Q device with the configured timeout
        and returns JSON data as a dictionary.

        relative_url is expected to start with a slash."""

        async with self._session.get(
                f"{self.anchor}{relative_url}", timeout=self._timeout
        ) as response:
            json_string = await response.text()

        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            raise InvalidAirQResponse(
                "_get_json() must only be used to query endpoints returning JSON data. "
                f"{relative_url} returned {json_string}."
            )

    async def _get_json_and_decode(self, relative_url: str) -> Any:
        """Executes a GET request to the air-Q device with the configured timeout
        decodes the response and returns JSON data.

        relative_url is expected to start with a slash."""

        json_data = await self._get_json(relative_url)

        encoded_message = json_data["content"]
        decoded_json_data = self.aes.decode(encoded_message)

        return json.loads(decoded_json_data)

    async def _post_json_and_decode(self, relative_url: str, post_json_data: dict) -> Any:
        """Executes a POST request to the air-Q device with the configured timeout,
        decodes the response and returns JSON data.

        relative_url is expected to start with a slash."""

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        post_data = "request=" + self.aes.encode(json.dumps(post_json_data))

        async with self._session.post(
                f"{self.anchor}{relative_url}",
                headers=headers, data=post_data, timeout=self._timeout
        ) as response:
            json_string = await response.text()

        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError:
            raise InvalidAirQResponse(
                "_post_json() must only be used to query endpoints returning JSON data. "
                f"{relative_url} returned {json_string}."
            )

        encoded_message = json_data["content"]
        decoded_json_data = self.aes.decode(encoded_message)

        return json.loads(decoded_json_data)

    @property
    async def data(self):
        return await self.get("data")

    @property
    async def average(self):
        return await self.get("average")

    @property
    async def config(self):
        """Deprecated. Use get_config() instead."""
        return await self.get("config")

    async def set_ifconfig_static(self, ip: str, subnet: str, gateway: str, dns: str):
        """Configures the interface to use a static IP setup.

        Notice: The air-Q only supports IPv4. After calling this function,
        you should call restart() to apply the settings."""
        if not is_valid_ipv4_address(ip):
            raise InvalidIpAddress(f"Invalid IP address: {ip}")
        if not is_valid_ipv4_address(subnet):
            raise InvalidIpAddress(f"Invalid subnet address: {subnet}")
        if not is_valid_ipv4_address(gateway):
            raise InvalidIpAddress(f"Invalid gateway address: {gateway}")
        if not is_valid_ipv4_address(dns):
            raise InvalidIpAddress(f"Invalid DNS server address: {dns}")

        post_json_data = {"ifconfig": {
            "ip": ip,
            "subnet": subnet,
            "gateway": gateway,
            "dns": dns
        }}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: new setting saved for key 'ifconfig': {'ip': '192.168.0.42', 'gateway': '192.168.0.1', 'subnet': '255.255.255.0', 'dns': '192.168.0.1'}\n"

    async def set_ifconfig_dhcp(self):
        """Configures the interface to use DHCP.

        Notice: After calling this function, you should call restart() to apply the settings."""
        post_json_data = {"DeleteKey": "ifconfig"}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: Key 'ifconfig' removed from user config setting. Default setting activated.\n"

    async def get_time_server(self):
        return (await self.get_config())["TimeServer"]

    async def set_time_server(self, time_server):
        post_json_data = {"TimeServer": time_server}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: new setting saved for key 'TimeServer': 192.168.0.1\n"

    async def get_device_name(self):
        return (await self.get_config())["devicename"]

    async def set_device_name(self, device_name):
        post_json_data = {"devicename": device_name}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: new setting saved for key 'devicename'"

    async def get_cloud_remote(self) -> bool:
        return (await self._get_json_and_decode("/config"))["cloudRemote"]

    async def set_cloud_remote(self, value: bool):
        post_json_data = {"cloudRemote": value}

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: new setting saved for key 'cloudRemote': False\n"

    async def get_log(self) -> List[str]:
        return await self._get_json_and_decode("/log")

    async def get_config(self) -> dict:
        return await self._get_json_and_decode("/config")

    async def get_possible_led_themes(self) -> List[str]:
        return (await self._get_json_and_decode("/config"))["possibleLedTheme"]

    async def get_led_theme(self) -> LedTheme:
        led_theme = (await self._get_json_and_decode("/config"))["ledTheme"]

        return LedTheme(left=led_theme["left"], right=led_theme["right"])

    async def set_led_theme_left(self, theme: str):
        await self._set_led_theme_on_one_side_only("left", theme)

    async def set_led_theme_right(self, theme: str):
        await self._set_led_theme_on_one_side_only("right", theme)

    async def set_led_theme_both(self, left: str, right: str):
        post_json_data = {
            "ledTheme": {
                "left": left,
                "right": right
            }
        }

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: new setting saved for key 'ledTheme': {'left': 'CO2', 'right': 'standard'}\n"

    async def _set_led_theme_on_one_side_only(self, side: Literal["left", "right"], theme: str):
        # air-Q does not support setting only one side.
        # If you do this, the API will answer a misleading error like
        #
        # ```
        # Error: unsupported option for key 'ledTheme' - can be ['standard', 'standard (contrast)', ...]
        # ```
        #
        # Therefore, we first read both sides, so we may set both sides at once.
        led_theme = await self.get_led_theme()

        post_json_data = {
            "ledTheme": {
                "left": theme if side == "left" else led_theme["left"],
                "right": theme if side == "right" else led_theme["right"]
            }
        }

        json_data = await self._post_json_and_decode("/config", post_json_data)
        # json_data will be a string like
        # "Success: new setting saved for key 'ledTheme': {'left': 'CO2', 'right': 'standard'}\n"
