import ipaddress
import json
import re
from typing import TypedDict

import aiohttp

from aioairq.encrypt import AESCipher
from aioairq.exceptions import InvalidAirQResponse, InvalidInput


class DeviceInfo(TypedDict):
    """Container for device information"""

    id: str
    name: str | None
    model: str | None
    suggested_area: str | None
    sw_version: str | None
    hw_version: str | None


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
        This is merely a convenience function, relying on the exception being
        raised down the stack (namely by AESCipher.decode from within self.get)
        """
        await self.get("ping")

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
            k: (v[0] if v else None) if isinstance(v, list) else v
            for k, v in data.items()
        }

    async def get(self, subject: str) -> dict:
        """Return the given subject from the air-Q device"""
        if subject not in self._supported_routes:
            raise NotImplementedError(
                f"subject must be in {self._supported_routes}, got {subject}"
            )

        async with self._session.get(
            f"{self.anchor}/{subject}", timeout=self._timeout
        ) as response:
            html = await response.text()

        try:
            encoded_message = json.loads(html)["content"]
        except (json.JSONDecodeError, KeyError):
            raise InvalidAirQResponse(
                "AirQ.get() is currently limited to a set of requests, "
                f"returning a dict with a key 'content' (namely {self._supported_routes}). "
                f"AirQ.get({subject}) returned {html}"
            )

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
