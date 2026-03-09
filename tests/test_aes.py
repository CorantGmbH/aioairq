import pytest

from aioairq.encrypt import AESCipher
from aioairq.exceptions import InvalidAuth

PASSWORD = "my-$ecur€-pa33w0rD"
DATA = (
    "any string, does not matter... "
    "encrypting it and decrypting it should result "
    "in the very string we started with ;-)"
)


def test_encrypted_decrypt():
    aes = AESCipher(PASSWORD)

    encrypted = aes.encode(DATA)
    decrypted = aes.decode(encrypted)

    assert decrypted == DATA


def test_decrypt_failure():
    encrypted = AESCipher(PASSWORD).encode(DATA)

    with pytest.raises(InvalidAuth):
        AESCipher("wrong-password").decode(encrypted)


class TestUnpadBytes:
    def test_valid_padding(self):
        payload = b"hello\x00\x00\x00"
        padded = payload + bytes([3] * 3)
        assert AESCipher._unpad_bytes(padded) == payload

    def test_full_block_padding(self):
        payload = b"A" * 16
        pad_len = 16
        padded = payload + bytes([pad_len] * pad_len)
        assert AESCipher._unpad_bytes(padded) == payload

    def test_single_byte_padding(self):
        payload = b"X" * 15
        padded = payload + bytes([1])
        assert AESCipher._unpad_bytes(padded) == payload

    def test_empty_data_raises(self):
        with pytest.raises(InvalidAuth):
            AESCipher._unpad_bytes(b"")

    def test_zero_padding_byte_raises(self):
        with pytest.raises(InvalidAuth):
            AESCipher._unpad_bytes(b"\x00" * 16)

    def test_padding_byte_too_large_raises(self):
        with pytest.raises(InvalidAuth):
            AESCipher._unpad_bytes(bytes([17] * 17))

    def test_inconsistent_padding_raises(self):
        payload = b"hello"
        bad_padded = payload + b"\x03\x03\x02"
        with pytest.raises(InvalidAuth):
            AESCipher._unpad_bytes(bad_padded)
