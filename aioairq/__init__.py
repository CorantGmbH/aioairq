"""air-Q library."""
__author__ = "Daniel Lehmann"
__credits__ = "Corant GmbH"
__email__ = "daniel.lehmann@corant.de"
__url__ = "https://www.air-q.com"
__license__ = "Apache License 2.0"
__version__ = "0.2.0"
__all__ = ["AirQ", "DeviceInfo", "InvalidAuth"]

from aioairq.core import AirQ, DeviceInfo, InvalidAuth
