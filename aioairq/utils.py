import ipaddress
from datetime import datetime


def is_valid_ipv4_address(address: str) -> bool:
    """Checks if address is a valid IPv4 address."""

    try:
        ipaddress.IPv4Address(address)
        return True
    except ipaddress.AddressValueError:
        return False


def is_time_in_interval(start: str, end: str) -> bool:
    """
    Checks if the current time falls within a given time interval.

    Parameters:
        start (str): Start time in "%H:%M" format (e.g., "18:00").
        end (str): End time in "%H:%M" format (e.g., "07:00").

    Returns:
        bool: True if the current time is in the interval, False otherwise.
    """
    now = datetime.now().time()
    start_time = datetime.strptime(start, "%H:%M").time()
    end_time = datetime.strptime(end, "%H:%M").time()

    if start_time <= end_time:
        # Interval does not span midnight
        return start_time <= now <= end_time
    else:
        # Interval spans midnight
        return now >= start_time or now <= end_time
