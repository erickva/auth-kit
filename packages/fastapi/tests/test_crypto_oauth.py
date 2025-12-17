"""
Tests for OAuth token encryption (AES-256-GCM)
"""

import base64
import os
import pytest

from cryptography.exceptions import InvalidTag

from auth_kit_fastapi.core.crypto_oauth import (
    OAuthTokenEncryption,
    encrypt_token,
    decrypt_token,
    get_encryption,
    clear_encryption_cache,
)


# Generate a valid 32-byte key for tests
def generate_test_key() -> str:
    """Generate a valid base64-encoded 32-byte key."""
    return base64.b64encode(os.urandom(32)).decode("ascii")


class TestOAuthTokenEncryption:
    """Tests for OAuthTokenEncryption class."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypt then decrypt returns original plaintext."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        plaintext = "my_secret_access_token_12345"
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_empty_string(self):
        """Test encryption of empty string."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        plaintext = ""
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_unicode(self):
        """Test encryption of unicode strings."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        plaintext = "token_with_unicode_\u00e9\u00e8\u00ea_\U0001f600"
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_large_payload(self):
        """Test encryption of large payloads."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        # Simulate a large JWT token
        plaintext = "a" * 10000
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypted_format_has_v1_prefix(self):
        """Test that encrypted output has v1: prefix."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        encrypted = enc.encrypt("test")

        assert encrypted.startswith("v1:")

    def test_encrypted_is_base64_after_prefix(self):
        """Test that content after v1: is valid base64."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        encrypted = enc.encrypt("test")
        base64_part = encrypted[3:]  # Remove "v1:"

        # Should not raise
        decoded = base64.b64decode(base64_part)
        # Should be at least nonce (12 bytes) + some ciphertext
        assert len(decoded) > 12

    def test_different_encryptions_produce_different_output(self):
        """Test that encrypting same plaintext twice produces different ciphertext."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        plaintext = "same_token"
        encrypted1 = enc.encrypt(plaintext)
        encrypted2 = enc.encrypt(plaintext)

        # Different due to random nonce
        assert encrypted1 != encrypted2

        # But both decrypt to same plaintext
        assert enc.decrypt(encrypted1) == plaintext
        assert enc.decrypt(encrypted2) == plaintext

    def test_invalid_key_too_short(self):
        """Test that key shorter than 32 bytes raises ValueError."""
        short_key = base64.b64encode(os.urandom(16)).decode("ascii")  # 16 bytes

        with pytest.raises(ValueError) as exc_info:
            OAuthTokenEncryption(short_key)

        assert "must decode to 32 bytes" in str(exc_info.value)

    def test_invalid_key_too_long(self):
        """Test that key longer than 32 bytes raises ValueError."""
        long_key = base64.b64encode(os.urandom(64)).decode("ascii")  # 64 bytes

        with pytest.raises(ValueError) as exc_info:
            OAuthTokenEncryption(long_key)

        assert "must decode to 32 bytes" in str(exc_info.value)

    def test_invalid_key_not_base64(self):
        """Test that invalid base64 key raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            OAuthTokenEncryption("not-valid-base64!!!")

        assert "must be valid base64" in str(exc_info.value)

    def test_none_key_disables_encryption(self):
        """Test that None key creates instance but encryption returns None."""
        enc = OAuthTokenEncryption(None)

        assert enc.is_configured is False
        assert enc.encrypt("test") is None
        assert enc.decrypt("v1:test") is None

    def test_decrypt_wrong_key_raises_invalid_tag(self):
        """Test that decrypting with wrong key raises InvalidTag."""
        key1 = generate_test_key()
        key2 = generate_test_key()

        enc1 = OAuthTokenEncryption(key1)
        enc2 = OAuthTokenEncryption(key2)

        encrypted = enc1.encrypt("secret")

        with pytest.raises(InvalidTag):
            enc2.decrypt(encrypted)

    def test_decrypt_tampered_ciphertext_raises_invalid_tag(self):
        """Test that tampered ciphertext raises InvalidTag."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        encrypted = enc.encrypt("secret")

        # Tamper with one character
        encrypted_list = list(encrypted)
        # Find a character to modify in base64 portion
        idx = len(encrypted) - 1
        encrypted_list[idx] = "X" if encrypted_list[idx] != "X" else "Y"
        tampered = "".join(encrypted_list)

        with pytest.raises((InvalidTag, ValueError)):
            enc.decrypt(tampered)

    def test_decrypt_invalid_prefix_raises_value_error(self):
        """Test that invalid version prefix raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        with pytest.raises(ValueError) as exc_info:
            enc.decrypt("v2:someciphertext")

        assert "Unsupported encryption format" in str(exc_info.value)

    def test_decrypt_invalid_base64_raises_value_error(self):
        """Test that invalid base64 in encrypted value raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        with pytest.raises(ValueError) as exc_info:
            enc.decrypt("v1:not-valid-base64!!!")

        assert "Invalid base64" in str(exc_info.value)

    def test_decrypt_too_short_raises_value_error(self):
        """Test that ciphertext too short raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        # Only 8 bytes when decoded (less than nonce length)
        short = "v1:" + base64.b64encode(b"12345678").decode("ascii")

        with pytest.raises(ValueError) as exc_info:
            enc.decrypt(short)

        assert "too short" in str(exc_info.value)

    def test_encrypt_none_raises_value_error(self):
        """Test that encrypting None raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        with pytest.raises(ValueError) as exc_info:
            enc.encrypt(None)

        assert "Cannot encrypt None" in str(exc_info.value)

    def test_encrypt_non_string_raises_value_error(self):
        """Test that encrypting non-string raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        with pytest.raises(ValueError) as exc_info:
            enc.encrypt(12345)

        assert "must be a string" in str(exc_info.value)

    def test_decrypt_none_raises_value_error(self):
        """Test that decrypting None raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        with pytest.raises(ValueError) as exc_info:
            enc.decrypt(None)

        assert "Cannot decrypt None" in str(exc_info.value)

    def test_decrypt_non_string_raises_value_error(self):
        """Test that decrypting non-string raises ValueError."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        with pytest.raises(ValueError) as exc_info:
            enc.decrypt(12345)

        assert "must be a string" in str(exc_info.value)


class TestModuleFunctions:
    """Tests for module-level helper functions."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_encryption_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        clear_encryption_cache()
        # Clean up environment
        if "AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY" in os.environ:
            del os.environ["AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY"]

    def test_encrypt_token_with_explicit_key(self):
        """Test encrypt_token with explicit key."""
        key = generate_test_key()

        encrypted = encrypt_token("my_token", encryption_key=key)

        assert encrypted is not None
        assert encrypted.startswith("v1:")

    def test_decrypt_token_with_explicit_key(self):
        """Test decrypt_token with explicit key."""
        key = generate_test_key()

        encrypted = encrypt_token("my_token", encryption_key=key)
        decrypted = decrypt_token(encrypted, encryption_key=key)

        assert decrypted == "my_token"

    def test_encrypt_token_from_environment(self):
        """Test encrypt_token using environment variable."""
        key = generate_test_key()
        os.environ["AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY"] = key

        encrypted = encrypt_token("env_token")

        assert encrypted is not None
        assert encrypted.startswith("v1:")

    def test_decrypt_token_from_environment(self):
        """Test decrypt_token using environment variable."""
        key = generate_test_key()
        os.environ["AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY"] = key

        encrypted = encrypt_token("env_token")
        decrypted = decrypt_token(encrypted)

        assert decrypted == "env_token"

    def test_get_encryption_caches_instance(self):
        """Test that get_encryption caches the instance."""
        key = generate_test_key()
        os.environ["AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY"] = key

        enc1 = get_encryption()
        enc2 = get_encryption()

        assert enc1 is enc2

    def test_get_encryption_with_key_creates_new_instance(self):
        """Test that explicit key creates new instance."""
        key1 = generate_test_key()
        key2 = generate_test_key()

        enc1 = get_encryption(key1)
        enc2 = get_encryption(key2)

        assert enc1 is not enc2

    def test_clear_encryption_cache_works(self):
        """Test that clear_encryption_cache clears cached instance."""
        key = generate_test_key()
        os.environ["AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY"] = key

        enc1 = get_encryption()
        clear_encryption_cache()
        enc2 = get_encryption()

        assert enc1 is not enc2


class TestSecurityProperties:
    """Tests for security properties of the encryption."""

    def test_nonce_is_random(self):
        """Test that each encryption uses a different nonce."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        nonces = set()
        for _ in range(100):
            encrypted = enc.encrypt("test")
            base64_part = encrypted[3:]
            decoded = base64.b64decode(base64_part)
            nonce = decoded[:12]
            nonces.add(nonce)

        # All nonces should be unique
        assert len(nonces) == 100

    def test_ciphertext_does_not_contain_plaintext(self):
        """Test that encrypted output doesn't contain plaintext."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        plaintext = "super_secret_token_value"
        encrypted = enc.encrypt(plaintext)

        assert plaintext not in encrypted
        assert plaintext.encode() not in base64.b64decode(encrypted[3:])


class TestRealWorldScenarios:
    """Tests simulating real OAuth token scenarios."""

    def test_encrypt_oauth_access_token(self):
        """Test encrypting a realistic OAuth access token."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        # Realistic access token (JWT-like)
        access_token = (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0."
            "signature_here"
        )

        encrypted = enc.encrypt(access_token)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == access_token

    def test_encrypt_oauth_refresh_token(self):
        """Test encrypting a realistic OAuth refresh token."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        # Realistic refresh token (opaque)
        refresh_token = "1//0eKCRmSAg_random_chars_here_very_long_string"

        encrypted = enc.encrypt(refresh_token)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == refresh_token

    def test_encrypt_apple_id_token(self):
        """Test encrypting Apple ID token (JWT with user info)."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        # Apple ID tokens are JWTs containing user info
        id_token = (
            "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIiwic3ViIjoiMDAwMTIzLmFiY2RlZjEyMzQ1Ni4wMDAwIiwiZW1haWwiOiJ1c2VyQGV4YW1wbGUuY29tIn0."
            "signature"
        )

        encrypted = enc.encrypt(id_token)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == id_token

    def test_multiple_tokens_same_key(self):
        """Test encrypting multiple tokens with same key."""
        key = generate_test_key()
        enc = OAuthTokenEncryption(key)

        tokens = {
            "access": "access_token_12345",
            "refresh": "refresh_token_67890",
            "id": "id_token_abcde",
        }

        encrypted_tokens = {k: enc.encrypt(v) for k, v in tokens.items()}
        decrypted_tokens = {k: enc.decrypt(v) for k, v in encrypted_tokens.items()}

        assert decrypted_tokens == tokens
