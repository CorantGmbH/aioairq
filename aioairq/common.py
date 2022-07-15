"""Common functions for the aioairq module"""

import base64
import json
from Crypto.Cipher import AES


def unpad(data: str) -> str:
    """Unpad the given data"""
    return data[: -ord(data[-1:])]


def decode_message(message: bytes, password: str) -> dict:
    """
    Decode the given message from base64 to plain text.
    The key for AES256 is derived from the password by appending
    zeros to a total key length of 32.
    Then the decoded message is AES256 decrypted in CBC mode using the key.
    The decoded message is unpadded and json decoded.
    """
    # first step decode base64
    msg = base64.b64decode(message)

    # second step derive key from password
    key = password.encode("utf-8")
    if len(key) < 32:
        for _ in range(32 - len(key)):
            key += b"0"
    elif len(key) > 32:
        key = key[:32]

    # third step decrypt message
    cipher = AES.new(key=key, mode=AES.MODE_CBC, IV=msg[:16])

    # fourth step unpad and decode json
    unpaded = unpad(cipher.decrypt(msg[16:]).decode("utf-8"))
    decoded_object = json.loads(unpaded)
    return decoded_object
