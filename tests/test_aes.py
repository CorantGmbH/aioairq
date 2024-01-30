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
