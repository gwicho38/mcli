"""
Encryption utilities for storage backends.

Provides AES-256-CBC encryption/decryption matching lsh-framework implementation.
"""

import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from mcli.lib.logger import get_logger

logger = get_logger(__name__)


def derive_key(encryption_key: str) -> bytes:
    """
    Derive AES-256 key from encryption key using SHA-256.

    Matches lsh-framework implementation:
    const key = crypto.createHash('sha256').update(encryptionKey).digest();

    Args:
        encryption_key: Master encryption key string

    Returns:
        bytes: 32-byte AES-256 key
    """
    return hashlib.sha256(encryption_key.encode()).digest()


def encrypt_data(data: bytes, encryption_key: str) -> bytes:
    """
    Encrypt data using AES-256-CBC.

    Matches lsh-framework implementation:
    - Uses SHA-256 to derive key from encryption_key
    - Random 16-byte IV
    - AES-256-CBC mode
    - Returns: IV (hex) + ':' + encrypted data (hex)

    Args:
        data: Binary data to encrypt
        encryption_key: Master encryption key

    Returns:
        bytes: Encrypted data in format: IV:encrypted_data (both hex-encoded)

    Example:
        encrypted = encrypt_data(b"secret data", "my-password")
        # Returns: b"a1b2c3d4...:e5f6g7h8..."
    """
    try:
        # Derive key
        key = derive_key(encryption_key)

        # Generate random IV (16 bytes for AES)
        import os

        iv = os.urandom(16)

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Pad data to block size (128 bits = 16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()

        # Encrypt
        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Format: IV:encrypted (both hex-encoded)
        iv_hex = iv.hex()
        encrypted_hex = encrypted.hex()
        result = f"{iv_hex}:{encrypted_hex}".encode()

        logger.debug(f"Encrypted {len(data)} bytes → {len(result)} bytes")
        return result

    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def decrypt_data(encrypted_data: bytes, encryption_key: str) -> bytes:
    """
    Decrypt data using AES-256-CBC.

    Matches lsh-framework implementation:
    - Expects format: IV (hex) + ':' + encrypted data (hex)
    - Uses SHA-256 to derive key
    - AES-256-CBC decryption

    Args:
        encrypted_data: Encrypted data in format: IV:encrypted_data
        encryption_key: Master encryption key

    Returns:
        bytes: Decrypted binary data

    Raises:
        ValueError: If encrypted_data format is invalid
        Exception: If decryption fails

    Example:
        decrypted = decrypt_data(encrypted_bytes, "my-password")
        # Returns: b"secret data"
    """
    try:
        # Parse IV and encrypted data
        parts = encrypted_data.decode().split(":", 1)
        if len(parts) != 2:
            raise ValueError("Invalid encrypted data format: expected 'IV:data'")

        iv_hex, encrypted_hex = parts

        # Convert from hex
        iv = bytes.fromhex(iv_hex)
        encrypted = bytes.fromhex(encrypted_hex)

        # Derive key
        key = derive_key(encryption_key)

        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        # Decrypt
        padded_data = decryptor.update(encrypted) + decryptor.finalize()

        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()

        logger.debug(f"Decrypted {len(encrypted_data)} bytes → {len(data)} bytes")
        return data

    except ValueError as e:
        logger.error(f"Decryption failed - invalid format: {e}")
        raise
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise


def generate_encryption_key() -> str:
    """
    Generate a random encryption key for AES-256.

    Returns:
        str: Random 32-character hexadecimal string

    Example:
        key = generate_encryption_key()
        # Returns: "a1b2c3d4e5f6g7h8..."
    """
    import os

    random_bytes = os.urandom(32)
    return random_bytes.hex()
