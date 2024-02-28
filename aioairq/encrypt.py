"""Module concerned with encryption of the data"""
import base64

from Crypto.Cipher import AES
from Crypto import Random

from aioairq.exceptions import InvalidAuth


class AESCipher:
    _bs = AES.block_size  # 16

    def __init__(self, passw: str):
        """Class responsible for decryption of AirQ responses

        Main idea of the class is to expose convenience methods
        ``encode`` and ``decode`` while the key is stored as a private attribute,
        conveniently computed from the password upon initialisation
        of the class' instance

        Parameters
        ----------
        passw : str
            Device's password
        """
        self._key = self._pass2aes(passw)

    def encode(self, data: str) -> str:
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self._key, AES.MODE_CBC, iv)

        encoded = data.encode("utf-8")
        encrypted = iv + cipher.encrypt(self._pad(encoded))

        return base64.b64encode(encrypted).decode("utf-8")

    def decode(self, encrypted: str) -> str:
        decoded = base64.b64decode(encrypted)
        iv = decoded[: self._bs]
        cipher = AES.new(self._key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(decoded[self._bs :])
        try:
            # Currently the device does not support proper authentication.
            # The success or failure of the authentication based on the ability
            # to decode the response from the device.
            decoded = decrypted.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidAuth(
                "Failed to decode a message. Incorrect password"
            ) from None
        return self._unpad(decoded)

    @staticmethod
    def _pad(data: bytes) -> bytes:
        length = 16 - (len(data) % 16)
        return data + bytes(chr(length) * length, "utf-8")

    @staticmethod
    def _unpad(data: str) -> str:
        return data[: -ord(data[-1])]

    @staticmethod
    def _pass2aes(passw: str) -> str:
        """Derive the key for AES256 from the device password

        The key for AES256 is derived from the password by appending
        zeros to a total key length of 32.
        """
        key = passw.encode("utf-8")
        if len(key) < 32:
            key += b"0" * (32 - len(key))
        elif len(key) > 32:
            key = key[:32]
        return key
