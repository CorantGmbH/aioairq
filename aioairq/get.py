"""Functions for retrieving data from the air-Q device."""

import json

import aiohttp

from aioairq.common import decode_message


async def get(subject: str, url: str, password: str) -> dict:
    """Returns the given subject from the air-Q device."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://{url}/{subject}") as response:
            html = await response.text()
            encoded_message = json.loads(html)["content"]
            return decode_message(encoded_message, password)


async def data(url: str, password: str) -> dict:
    """Returns the latest data point from the air-Q device."""
    return await get("data", url, password)


async def average(url: str, password: str) -> dict:
    """Returns the average data point from the air-Q device."""
    return await get("average", url, password)


async def config(url: str, password: str) -> dict:
    """Returns the configuration from the air-Q device."""
    return await get("config", url, password)
