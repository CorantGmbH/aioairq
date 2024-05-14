class InvalidAuth(Exception):
    """Error to indicate an authentication failure."""


class InvalidAirQResponse(Exception):
    """Error to indicate incorrect / unexpected response from the device"""


class InvalidIpAddress(Exception):
    """Error to indicate in invalid IP address. air-Q only supports IPv4 addresses."""


class APIAccessDenied(Exception):
    """Raised at an attempt to access air-Q Science API without the subscription."""


class APIAccessError(Exception):
    """Unspecific error reported by the air-Q API."""
