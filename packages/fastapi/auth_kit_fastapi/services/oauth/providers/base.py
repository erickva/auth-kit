"""
Base OAuth provider interface and common models.

All OAuth providers must implement this interface to ensure consistent
behavior across Google, GitHub, and Apple OAuth flows.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlencode


@dataclass
class OAuthProfile:
    """
    Normalized user profile from OAuth provider.

    All providers must return this consistent structure regardless
    of their underlying API response format.
    """
    provider: str
    provider_user_id: str
    email: Optional[str]
    username: Optional[str] = None
    id_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "provider": self.provider,
            "provider_user_id": self.provider_user_id,
            "email": self.email,
            "username": self.username,
        }


@dataclass
class OAuthTokens:
    """
    OAuth tokens returned from token exchange.

    Contains all token data needed for storage and API calls.
    """
    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {
            "access_token": self.access_token,
            "token_type": self.token_type,
        }
        if self.refresh_token:
            result["refresh_token"] = self.refresh_token
        if self.id_token:
            result["id_token"] = self.id_token
        if self.scope:
            result["scope"] = self.scope
        if self.expires_in:
            result["expires_in"] = self.expires_in
        if self.expires_at:
            result["expires_at"] = self.expires_at.isoformat()
        return result


class OAuthProviderError(Exception):
    """Base exception for OAuth provider errors."""

    def __init__(self, message: str, provider: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class OAuthTokenExchangeError(OAuthProviderError):
    """Error during token exchange."""
    pass


class OAuthProfileError(OAuthProviderError):
    """Error fetching user profile."""
    pass


class OAuthProvider(ABC):
    """
    Abstract base class for OAuth providers.

    All OAuth providers (Google, GitHub, Apple) must implement this interface
    to ensure consistent behavior across the OAuth flow.

    Typical flow:
    1. Client calls build_authorize_url() to get redirect URL
    2. User authorizes and is redirected back with code
    3. Server calls exchange_token() with code and verifier
    4. Server calls fetch_profile() to get user info
    """

    # Provider identifier (e.g., "google", "github", "apple")
    provider_name: str

    # OAuth endpoints
    authorize_url: str
    token_url: str

    # Default scopes for this provider
    default_scopes: list[str]

    def __init__(
        self,
        client_id: str,
        client_secret: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the provider with credentials.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret (optional for some providers)
            **kwargs: Provider-specific configuration
        """
        self.client_id = client_id
        self.client_secret = client_secret

    def build_authorize_url(
        self,
        redirect_uri: str,
        code_challenge: str,
        state: str,
        scope: Optional[str] = None,
    ) -> str:
        """
        Build the authorization URL for the OAuth flow.

        Args:
            redirect_uri: URL to redirect back to after authorization
            code_challenge: PKCE code challenge (base64url(SHA256(verifier)))
            state: State parameter for CSRF protection
            scope: Optional scope override (defaults to provider default)

        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": scope or " ".join(self.default_scopes),
        }

        # Allow providers to add custom parameters
        params.update(self._get_extra_authorize_params())

        return f"{self.authorize_url}?{urlencode(params)}"

    def _get_extra_authorize_params(self) -> Dict[str, str]:
        """
        Get provider-specific authorization parameters.

        Override in subclasses to add custom parameters.
        """
        return {}

    @abstractmethod
    async def exchange_token(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier (original random string)
            redirect_uri: Must match the redirect_uri used in authorize

        Returns:
            OAuthTokens containing access_token and optionally refresh_token

        Raises:
            OAuthTokenExchangeError: If token exchange fails
        """
        pass

    @abstractmethod
    async def fetch_profile(self, tokens: OAuthTokens) -> OAuthProfile:
        """
        Fetch user profile using access token.

        Args:
            tokens: OAuth tokens from exchange_token()

        Returns:
            Normalized OAuthProfile with user information

        Raises:
            OAuthProfileError: If profile fetch fails
        """
        pass

    async def get_user_identity(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> tuple[OAuthTokens, OAuthProfile]:
        """
        Complete OAuth flow: exchange token and fetch profile.

        Convenience method that combines exchange_token and fetch_profile.

        Args:
            code: Authorization code from OAuth callback
            code_verifier: PKCE code verifier
            redirect_uri: Redirect URI used in authorization

        Returns:
            Tuple of (tokens, profile)
        """
        tokens = await self.exchange_token(code, code_verifier, redirect_uri)
        profile = await self.fetch_profile(tokens)
        return tokens, profile
