"""Functions for retrieving data from the air-Q device."""

import json

import aiohttp

from aioairq.common import decode_message


async def get(subject: str, url: str, password: str) -> dict:
    """Returns the given subject from the air-Q device."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://{url}/{subject}") as response:

            content = {}
            content["status"] = response.status
            content["content-type"] = response.headers["content-type"]

            html = await response.text()

            encoded_message = json.loads(html)["content"]
            content["content"] = decode_message(encoded_message, password)

            return content


async def data(url: str, password: str) -> dict:
    """Returns the latest data point from the air-Q device."""
    return await get("data", url, password)


async def average(url: str, password: str) -> dict:
    """Returns the average data point from the air-Q device."""
    return await get("average", url, password)


async def config(url: str, password: str) -> dict:
    """Returns the configuration from the air-Q device."""
    return await get("config", url, password)
