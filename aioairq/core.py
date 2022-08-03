import json

import aiohttp

from aioairq.encrypt import AESCipher


class AirQ:
    def __init__(self, airq_ip: str, passw: str):
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

    async def test_authentication(self) -> bool:
        """Test if the password provided to the constructor matches.

        Returns True or False depending on the ability to authenticate

        This method is a kludge, as currently the device does not support
        authentication. This module infers the success of failure of the
        authentication based on the ability to decode the response from the device.
        """
        try:
            await self.get("ping")
        except UnicodeDecodeError:
            return False
        return True

    def __repr__(self) -> str:
        return f"AirQ(id={self.airq_ip})"

    @staticmethod
    def drop_errors_from_data(data: dict) -> dict:
        return {k: v[0] if isinstance(v, list) else v for k, v in data.items()}

    async def get(self, subject: str) -> dict:
        """Returns the given subject from the air-Q device"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.anchor}/{subject}") as response:
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
