class InvalidAuth(Exception):
    """Error to indicate an authentication failure."""


class InvalidInput(Exception):
    """Error to indicate the device ID / IP is invalid."""


class InvalidAirQResponse(Exception):
    """Error to indicate incorrect / unexpected response from the device"""
