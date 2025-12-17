"""
OAuth provider implementations for Google, GitHub, and Apple.
"""

from .base import OAuthProvider, OAuthProfile, OAuthTokens
from .google import GoogleProvider
from .github import GitHubProvider
from .apple import AppleProvider
from .factory import get_provider, get_available_providers

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
