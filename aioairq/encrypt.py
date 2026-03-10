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

    def decode_to_bytes(self, encrypted: str) -> bytes:
        """Decrypt and return raw bytes, without UTF-8 decoding.

        Needed for payloads containing binary data (e.g. zlib-compressed).
        """
        decoded = base64.b64decode(encrypted)
        iv = decoded[: self._bs]
        cipher = AES.new(self._key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(decoded[self._bs :])
        try:
            return self._unpad_bytes(decrypted)
        except ValueError as exc:
            raise InvalidAuth("Failed to decrypt. Incorrect password?") from exc

    def decode(self, encrypted: str) -> str:
        unpadded = self.decode_to_bytes(encrypted)
        try:
            return unpadded.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidAuth("Failed to decrypt. Incorrect password?") from exc

    @staticmethod
    def _pad(data: bytes) -> bytes:
        length = 16 - (len(data) % 16)
        return data + bytes(chr(length) * length, "utf-8")

    @staticmethod
    def _unpad_bytes(data: bytes) -> bytes:
        if not data:
            raise ValueError("empty data")
        pad_len = data[-1]
        if pad_len < 1 or pad_len > AES.block_size:
            raise ValueError(f"invalid padding byte {pad_len!r}")
        if data[-pad_len:] != bytes([pad_len] * pad_len):
            raise ValueError("padding bytes are inconsistent")
        return data[:-pad_len]

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
