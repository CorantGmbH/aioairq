"""Module concerned with encryption of the data"""
import base64

from Crypto import Random
from Crypto.Cipher import AES


class AESCipher:

    _bs = AES.block_size  # 16

    def __init__(self, passw: str):
        """Class responsible for decryption of AirQ responses

        Main idea of the class is to expose a convenience method
        ``decode`` while the decryption key is stored as an attribute,
        conveniently computed from the password upon initialisation
        of the class' instance

        Parameters
        ----------
        passw : str
            Device's password
        """
        self.key = self._pass2aes(passw)

    def decode(self, encrypted: bytes) -> str:
        decoded = base64.b64decode(encrypted)
        iv = decoded[: self._bs]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(decoded[self._bs :])
        return self._unpad(decrypted.decode("utf-8"))

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
