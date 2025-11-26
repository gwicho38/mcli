"""Unit tests for storage encryption module."""

import pytest

from mcli.storage.encryption import decrypt_data, derive_key, encrypt_data, generate_encryption_key


class TestDeriveKey:
    """Tests for derive_key function."""

    def test_derive_key_returns_32_bytes(self):
        """Test that derive_key returns 32-byte key for AES-256."""
        key = derive_key("test-password")
        assert len(key) == 32

    def test_derive_key_consistent(self):
        """Test that same input produces same key."""
        key1 = derive_key("my-secret")
        key2 = derive_key("my-secret")
        assert key1 == key2

    def test_derive_key_different_inputs(self):
        """Test that different inputs produce different keys."""
        key1 = derive_key("password1")
        key2 = derive_key("password2")
        assert key1 != key2


class TestEncryptDecrypt:
    """Tests for encrypt_data and decrypt_data functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that data can be encrypted and decrypted."""
        original = b"Hello, World!"
        password = "test-password"

        encrypted = encrypt_data(original, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == original

    def test_encrypt_produces_different_ciphertext(self):
        """Test that encryption uses random IV (different ciphertext each time)."""
        data = b"test data"
        password = "password"

        encrypted1 = encrypt_data(data, password)
        encrypted2 = encrypt_data(data, password)

        # Different IV means different ciphertext
        assert encrypted1 != encrypted2

    def test_encrypt_format(self):
        """Test that encrypted data has correct format (IV:ciphertext)."""
        encrypted = encrypt_data(b"test", "password")
        decoded = encrypted.decode()

        assert ":" in decoded
        parts = decoded.split(":")
        assert len(parts) == 2

        # IV should be 32 hex chars (16 bytes)
        assert len(parts[0]) == 32

    def test_decrypt_wrong_password_fails(self):
        """Test that decryption with wrong password fails."""
        data = b"secret data"
        encrypted = encrypt_data(data, "correct-password")

        with pytest.raises(Exception):
            decrypt_data(encrypted, "wrong-password")

    def test_decrypt_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            decrypt_data(b"invalid-no-colon", "password")

    def test_encrypt_empty_data(self):
        """Test encryption of empty data."""
        encrypted = encrypt_data(b"", "password")
        decrypted = decrypt_data(encrypted, "password")
        assert decrypted == b""

    def test_encrypt_large_data(self):
        """Test encryption of larger data."""
        data = b"x" * 10000
        password = "password"

        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == data

    def test_encrypt_binary_data(self):
        """Test encryption of binary data with null bytes."""
        data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        password = "password"

        encrypted = encrypt_data(data, password)
        decrypted = decrypt_data(encrypted, password)

        assert decrypted == data


class TestGenerateEncryptionKey:
    """Tests for generate_encryption_key function."""

    def test_generates_64_char_hex(self):
        """Test that generated key is 64 hex characters (32 bytes)."""
        key = generate_encryption_key()
        assert len(key) == 64
        # Should be valid hex
        int(key, 16)

    def test_generates_unique_keys(self):
        """Test that each call generates a unique key."""
        keys = [generate_encryption_key() for _ in range(10)]
        assert len(set(keys)) == 10
