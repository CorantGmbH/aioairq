"""air-Q library."""
__author__ = "Daniel Lehmann"
__credits__ = "Corant GmbH"
__email__ = "daniel.lehmann@corant.de"
__url__ = "https://www.air-q.com"
__license__ = "Apache License 2.0"
__version__ = "0.4.0"
__all__ = [
    "AirQ",
    "DeviceInfo",
    "NightMode",
    "InvalidAirQResponse",
    "InvalidAuth",
    "InvalidIpAddress",
]

from aioairq.core import AirQ, DeviceInfo, NightMode
from aioairq.exceptions import InvalidAirQResponse, InvalidAuth, InvalidIpAddress
