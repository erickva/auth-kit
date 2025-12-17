"""
AES-256-GCM encryption utilities for OAuth tokens.

Provides secure encryption/decryption for storing OAuth tokens at rest.
Uses AES-256-GCM with 12-byte random nonce and stores in format:
    v1:<base64(nonce || ciphertext)>

Key must be 32 bytes (256 bits) provided as base64 via OAUTH_TOKEN_ENCRYPTION_KEY.
"""

import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


class OAuthTokenEncryption:
    """
    AES-256-GCM encryption for OAuth tokens.

    Usage:
        encryption = OAuthTokenEncryption(base64_key)
        encrypted = encryption.encrypt("my_secret_token")
        decrypted = encryption.decrypt(encrypted)
    """

    VERSION_PREFIX = "v1:"
    NONCE_LENGTH = 12  # 96 bits as recommended for GCM
    KEY_LENGTH = 32    # 256 bits for AES-256

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with a base64-encoded 32-byte key.

        Args:
            encryption_key: Base64-encoded 32-byte key. If None, encryption
                          operations will return None/raise appropriately.

        Raises:
            ValueError: If key is not valid base64 or not exactly 32 bytes.
        """
        self._aesgcm: Optional[AESGCM] = None

        if encryption_key is not None:
            try:
                key_bytes = base64.b64decode(encryption_key)
            except Exception as e:
                raise ValueError(
                    f"OAUTH_TOKEN_ENCRYPTION_KEY must be valid base64: {e}"
                )

            if len(key_bytes) != self.KEY_LENGTH:
                raise ValueError(
                    f"OAUTH_TOKEN_ENCRYPTION_KEY must decode to {self.KEY_LENGTH} bytes "
                    f"for AES-256-GCM, got {len(key_bytes)}"
                )

            self._aesgcm = AESGCM(key_bytes)

    @property
    def is_configured(self) -> bool:
        """Check if encryption is properly configured."""
        return self._aesgcm is not None

    def encrypt(self, plaintext: str) -> Optional[str]:
        """
        Encrypt a plaintext string using AES-256-GCM.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Encrypted string in format "v1:<base64(nonce||ciphertext)>",
            or None if encryption is not configured.

        Raises:
            ValueError: If plaintext is None or not a string.
        """
        if not self.is_configured:
            return None

        if plaintext is None:
            raise ValueError("Cannot encrypt None value")

        if not isinstance(plaintext, str):
            raise ValueError("Plaintext must be a string")

        # Generate random 12-byte nonce
        nonce = os.urandom(self.NONCE_LENGTH)

        # Encrypt (no associated data)
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = self._aesgcm.encrypt(nonce, plaintext_bytes, None)

        # Combine nonce + ciphertext and base64 encode
        combined = nonce + ciphertext
        encoded = base64.b64encode(combined).decode("ascii")

        return f"{self.VERSION_PREFIX}{encoded}"

    def decrypt(self, encrypted: str) -> Optional[str]:
        """
        Decrypt a string encrypted with this class.

        Args:
            encrypted: Encrypted string in format "v1:<base64(nonce||ciphertext)>".

        Returns:
            Decrypted plaintext string, or None if encryption is not configured.

        Raises:
            ValueError: If encrypted format is invalid or version is unsupported.
            InvalidTag: If decryption fails (tampered or wrong key).
        """
        if not self.is_configured:
            return None

        if encrypted is None:
            raise ValueError("Cannot decrypt None value")

        if not isinstance(encrypted, str):
            raise ValueError("Encrypted value must be a string")

        # Check version prefix
        if not encrypted.startswith(self.VERSION_PREFIX):
            raise ValueError(
                f"Unsupported encryption format. Expected '{self.VERSION_PREFIX}' prefix."
            )

        # Extract base64 portion
        encoded = encrypted[len(self.VERSION_PREFIX):]

        try:
            combined = base64.b64decode(encoded)
        except Exception as e:
            raise ValueError(f"Invalid base64 in encrypted value: {e}")

        # Split nonce and ciphertext
        if len(combined) < self.NONCE_LENGTH + 1:
            raise ValueError("Encrypted value too short (missing nonce or ciphertext)")

        nonce = combined[:self.NONCE_LENGTH]
        ciphertext = combined[self.NONCE_LENGTH:]

        # Decrypt (raises InvalidTag if tampered or wrong key)
        plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext_bytes.decode("utf-8")


# Module-level helper functions for convenience

_encryption_instance: Optional[OAuthTokenEncryption] = None


def get_encryption(encryption_key: Optional[str] = None) -> OAuthTokenEncryption:
    """
    Get or create an OAuthTokenEncryption instance.

    If encryption_key is provided, creates a new instance.
    Otherwise returns a cached instance or creates one from environment.

    Args:
        encryption_key: Optional base64-encoded 32-byte key.

    Returns:
        OAuthTokenEncryption instance.
    """
    global _encryption_instance

    if encryption_key is not None:
        return OAuthTokenEncryption(encryption_key)

    if _encryption_instance is None:
        # Try to get from environment
        env_key = os.environ.get("AUTH_KIT_OAUTH_TOKEN_ENCRYPTION_KEY")
        _encryption_instance = OAuthTokenEncryption(env_key)

    return _encryption_instance


def encrypt_token(plaintext: str, encryption_key: Optional[str] = None) -> Optional[str]:
    """
    Encrypt a token string.

    Args:
        plaintext: The token to encrypt.
        encryption_key: Optional base64-encoded 32-byte key.
                       If not provided, uses cached instance or environment.

    Returns:
        Encrypted string in format "v1:<base64(nonce||ciphertext)>",
        or None if encryption is not configured.
    """
    enc = get_encryption(encryption_key)
    return enc.encrypt(plaintext)


def decrypt_token(encrypted: str, encryption_key: Optional[str] = None) -> Optional[str]:
    """
    Decrypt a token string.

    Args:
        encrypted: Encrypted string in format "v1:<base64(nonce||ciphertext)>".
        encryption_key: Optional base64-encoded 32-byte key.
                       If not provided, uses cached instance or environment.

    Returns:
        Decrypted plaintext string, or None if encryption is not configured.
    """
    enc = get_encryption(encryption_key)
    return enc.decrypt(encrypted)


def clear_encryption_cache() -> None:
    """Clear the cached encryption instance. Useful for testing."""
    global _encryption_instance
    _encryption_instance = None
