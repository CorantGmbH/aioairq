class InvalidAuth(Exception):
    """Error to indicate an authentication failure."""


class InvalidAirQResponse(Exception):
    """Error to indicate incorrect / unexpected response from the device"""


class InvalidIpAddress(Exception):
    """Error to indicate in invalid IP address. air-Q only supports IPv4 addresses."""
