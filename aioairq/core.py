import ipaddress
import json
import re
from typing import TypedDict

import aiohttp

from aioairq.encrypt import AESCipher


class DeviceInfo(TypedDict):
    """Container for device information"""

    id: str
    name: str
    model: str
    sw_version: str
    hw_version: str


class AirQ:
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

        self.__class__._validate_address(address)
        self.address = address
        self.anchor = "http://" + self.address
        self.aes = AESCipher(passw)
        self._session = session
        self._timeout = aiohttp.ClientTimeout(connect=timeout)

    @classmethod
    def _validate_address(cls, address: str) -> None:
        """Raise an error if address is not a valid IP or mDNS."""
        if not re.match(r"^[a-f0-9]{5}_air-q\..+$", address):
            try:
                ipaddress.ip_address(address)
            except ValueError:
                raise InvalidInput(
                    f"{address} does not appear to be a valid IP address "
                    "or a 5-digit device ID"
                )

    async def validate(self) -> None:
        """Test if the password provided to the constructor is valid.

        Raises InvalidAuth if the password is not correct.

        This method is a workaround, as currently the device does not support
        authentication. This module infers the success of failure of the
        authentication based on the ability to decode the response from the device.
        """
        try:
            await self.get("ping")
        except UnicodeDecodeError:
            raise InvalidAuth

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.address})"

    async def fetch_device_info(self) -> DeviceInfo:
        """Fetch condensed device description"""
        config = await self.get("config")
        return DeviceInfo(
            id=config["id"],
            name=config["devicename"],
            model=config["type"],
            sw_version=config["air-Q-Software-Version"],
            hw_version=config["air-Q-Hardware-Version"],
        )

    @staticmethod
    def drop_uncertainties_from_data(data: dict) -> dict:
        """Filter returned dict and substitute (value, uncertainty) with the value.

        The device attempts to estimate the uncertainty, or error, of certain readings.
        These readings are returned as tuples of (value, uncertainty). Often, the latter
        is not desired, and this is a convenience method to homogenise the dict a little
        """
        return {k: v[0] if isinstance(v, list) else v for k, v in data.items()}

    async def get(self, subject: str) -> dict:
        """Return the given subject from the air-Q device"""
        async with self._session.get(
            f"{self.anchor}/{subject}", timeout=self._timeout
        ) as response:
            html = await response.text()
            encoded_message = json.loads(html)["content"]
            return json.loads(self.aes.decode(encoded_message))

    @property
    async def data(self):
        return await self.get("data")

    @property
    async def average(self):
        return await self.get("average")

    @property
    async def config(self):
        return await self.get("config")


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class InvalidInput(Exception):
    """Error to indicate there is invalid auth."""
