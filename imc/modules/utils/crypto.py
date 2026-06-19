"""Script to handle encryption/decryption."""

# Standard imports
import base64
import os

from typing import Union

# Third party imports
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# Internal imports
from imc.modules.utils import custom_logs


logger = custom_logs.getLogger(__name__)


class EncryptDecrypt:
    """Utility class for encoding, decoding, encrypting, and decrypting data."""

    @staticmethod
    def _derive_key(secret_key: str, salt: bytes, iterations: int = 100000) -> bytes:
        """
        Derive a byte key from a string secret key using PBKDF2HMAC.

        :param secret_key: Secret key in string format.
        :type secret_key: str
        :param salt: Salt for the key derivation.
        :type salt: bytes
        :param iterations: Number of iterations for the derivation. Default is 100000.
        :type iterations: int
        :return: Derived key in bytes.
        :rtype: bytes
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )
        return kdf.derive(secret_key.encode())

    @staticmethod
    def encode_base64(data: Union[str, bytes]) -> str:
        """
        Encode data to base64 format.

        :param data: Data to be encoded.
        :type data: Union[str, bytes]
        :return: Base64 encoded data.
        :rtype: str
        """
        try:
            if isinstance(data, str):
                data = data.encode("utf-8")
            encoded = base64.b64encode(data).decode("utf-8")
            logger.info("Data successfully encoded.")
            return encoded
        except Exception as e:
            logger.error(f"Error encoding data: {e}")
            raise

    @staticmethod
    def decode_base64(encoded_data: str) -> str:
        """
        Decode data from base64 format.

        :param encoded_data: Base64 encoded data.
        :type encoded_data: str
        :return: Decoded data.
        :rtype: str
        """
        try:
            decoded = base64.b64decode(encoded_data).decode("utf-8")
            logger.info("Data successfully decoded.")
            return decoded
        except Exception as e:
            logger.error(f"Error decoding data: {e}")
            raise

    @staticmethod
    def encrypt_secret_key(data: Union[str, bytes], secret_key: str) -> bytes:
        """
        Encrypt data using AES encryption with the provided secret key string.

        :param data: Data to be encrypted.
        :type data: Union[str, bytes]
        :param secret_key: Secret key string for encryption.
        :type secret_key: str
        :return: Encrypted data.
        :rtype: bytes
        """
        try:
            salt = os.urandom(16)
            key = EncryptDecrypt._derive_key(secret_key, salt)

            if isinstance(data, str):
                data = data.encode("utf-8")

            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()

            cipher = Cipher(
                algorithms.AES(key), modes.CBC(salt), backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(padded_data) + encryptor.finalize()

            logger.info("Data successfully encrypted.")
            return salt + encrypted  # Prepend salt to encrypted data for decryption
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise

    @staticmethod
    def decrypt_secret_key(encrypted_data: bytes, secret_key: str) -> str:
        """
        Decrypt data using AES decryption with the provided secret key string.

        :param encrypted_data: Data to be decrypted, including the salt.
        :type encrypted_data: bytes
        :param secret_key: Secret key string for decryption.
        :type secret_key: str
        :return: Decrypted data.
        :rtype: str
        """
        try:
            salt = encrypted_data[:16]  # Extract salt
            encrypted_data = encrypted_data[16:]  # Actual encrypted data
            key = EncryptDecrypt._derive_key(secret_key, salt)

            cipher = Cipher(
                algorithms.AES(key), modes.CBC(salt), backend=default_backend()
            )
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

            logger.info("Data successfully decrypted.")
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
