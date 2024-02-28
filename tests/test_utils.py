import pytest

from aioairq.utils import is_valid_ipv4_address


@pytest.mark.parametrize(
    "valid_address",
    [
        "0.0.0.0",
        "1.2.3.4",
        "11.22.33.44",
        "111.9.66.222",
        "252.253.254.255",
        "192.168.178.1",
    ],
)
def test_valid_ipv4_address(valid_address):
    assert is_valid_ipv4_address(valid_address)


@pytest.mark.parametrize(
    "invalid_address",
    [
        "",
        "1234",
        "1.2.3.256",
        "-1.2.3.255",
        "a.b.c.d",
        "1.2.3.4.5",
        "1.2.3",
        "bullshit",
        "1.2.3 .4",
        " 1.2.3.4",
        "1.2.3.4 ",
        "::1",
        "7f000001",
        "0x7f000001",
        "60.70.80.90/20",
    ],
)
def test_invalid_ipv4_address(invalid_address):
    assert not is_valid_ipv4_address(invalid_address)
