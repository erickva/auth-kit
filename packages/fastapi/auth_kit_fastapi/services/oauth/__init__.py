"""
OAuth services for social authentication.

This module provides OAuth provider implementations and utilities
for Google, GitHub, and Apple sign-in.
"""

from .providers import (
    OAuthProvider,
    OAuthProfile,
    OAuthTokens,
    GoogleProvider,
    GitHubProvider,
    AppleProvider,
    get_provider,
    get_available_providers,
)

__all__ = [
    "OAuthProvider",
    "OAuthProfile",
    "OAuthTokens",
    "GoogleProvider",
    "GitHubProvider",
    "AppleProvider",
    "get_provider",
    "get_available_providers",
]
