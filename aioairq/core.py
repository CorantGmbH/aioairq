import json
from typing import TypedDict

import aiohttp

from aioairq.encrypt import AESCipher


class DeviceInfo(TypedDict):
    """Container for device information"""

    id: str
    name: str
    model: str
    room_type: str
    sw_version: str
    hw_version: str


class AirQ:
    def __init__(self, airq_ip: str, passw: str, session: aiohttp.ClientSession):
        """Class representing the API for a single AirQ device

        The class holds the AESCipher object, responsible for message decoding,
        as well as the anchor of the http address to base further requests on

        Parameters
        ----------
        airq_ip : str
            According to the documentation can represent either the IP or mDNS name.
            Device's IP might be a more robust option (across the variety of routers)
        passw : str
            Device's password
        """

        self.airq_ip = airq_ip
        self.anchor = f"http://{airq_ip}"
        self.aes = AESCipher(passw)
        self._session = session

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
        return f"AirQ(id={self.airq_ip})"

    async def fetch_device_info(self) -> DeviceInfo:
        """Fetch condensed device description"""
        config = await self.get("config")
        return DeviceInfo(
            id=config["id"],
            name=config["devicename"],
            model=config["type"],
            room_type=config["RoomType"].replace("-", " ").title(),
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
        async with self._session.get(f"{self.anchor}/{subject}") as response:
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
