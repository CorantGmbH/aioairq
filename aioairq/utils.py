import ipaddress


def is_valid_ipv4_address(address: str) -> bool:
    """Checks if address is a valid IPv4 address."""

    try:
        ipaddress.IPv4Address(address)
        return True
    except ipaddress.AddressValueError:
        return False
