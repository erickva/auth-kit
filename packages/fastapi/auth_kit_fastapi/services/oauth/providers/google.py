"""
Google OAuth provider implementation.

Uses Google OAuth 2.0 with PKCE S256 for secure authorization.
Endpoints:
- Authorize: https://accounts.google.com/o/oauth2/v2/auth
- Token: https://oauth2.googleapis.com/token
- UserInfo: https://openidconnect.googleapis.com/v1/userinfo
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx

from .base import (
    OAuthProvider,
    OAuthProfile,
    OAuthTokens,
    OAuthTokenExchangeError,
    OAuthProfileError,
)


class GoogleProvider(OAuthProvider):
    """
    Google OAuth 2.0 provider with PKCE support.

    Implements the standard OAuth 2.0 flow with PKCE S256 code challenge.
    Fetches user profile from Google's OpenID Connect userinfo endpoint.
    """

    provider_name = "google"
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"

    default_scopes = [
        "openid",
        "email",
        "profile",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        timeout: float = 30.0,
        **kwargs
    ):
        """
        Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth Client ID
            client_secret: Google OAuth Client Secret
            timeout: HTTP request timeout in seconds
        """
        super().__init__(client_id, client_secret, **kwargs)
        self.timeout = timeout

    def _get_extra_authorize_params(self) -> Dict[str, str]:
        """Add Google-specific authorization parameters."""
        return {
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Always show consent screen for refresh token
        }

    async def exchange_token(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for Google tokens.

        Args:
            code: Authorization code from Google callback
            code_verifier: PKCE code verifier
            redirect_uri: Redirect URI used in authorization

        Returns:
            OAuthTokens with access_token, refresh_token, and id_token

        Raises:
            OAuthTokenExchangeError: If token exchange fails
        """
        if not code_verifier:
            raise OAuthTokenExchangeError(
                "PKCE code_verifier is required for Google OAuth",
                provider=self.provider_name,
            )

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise OAuthTokenExchangeError(
                        f"Google token exchange failed: {error_data.get('error_description', response.text)}",
                        provider=self.provider_name,
                        details=error_data,
                    )

                data = response.json()

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                f"HTTP error during Google token exchange: {str(e)}",
                provider=self.provider_name,
            )

        # Calculate expiration time
        expires_at = None
        expires_in = data.get("expires_in")
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return OAuthTokens(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            refresh_token=data.get("refresh_token"),
            id_token=data.get("id_token"),
            scope=data.get("scope"),
            expires_in=expires_in,
            expires_at=expires_at,
        )

    async def fetch_profile(self, tokens: OAuthTokens) -> OAuthProfile:
        """
        Fetch user profile from Google userinfo endpoint.

        Args:
            tokens: OAuth tokens from exchange_token()

        Returns:
            Normalized OAuthProfile with Google user information

        Raises:
            OAuthProfileError: If profile fetch fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {tokens.access_token}"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise OAuthProfileError(
                        f"Google profile fetch failed: {response.text}",
                        provider=self.provider_name,
                        details=error_data,
                    )

                data = response.json()

        except httpx.HTTPError as e:
            raise OAuthProfileError(
                f"HTTP error fetching Google profile: {str(e)}",
                provider=self.provider_name,
            )

        # Google returns 'sub' as the unique user ID
        provider_user_id = data.get("sub")
        if not provider_user_id:
            raise OAuthProfileError(
                "Google profile missing 'sub' (user ID)",
                provider=self.provider_name,
                details=data,
            )

        email_verified = data.get("email_verified")
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() == "true"

        return OAuthProfile(
            provider=self.provider_name,
            provider_user_id=provider_user_id,
            email=data.get("email"),
            username=data.get("name"),
            email_verified=email_verified if isinstance(email_verified, bool) else None,
            id_token=tokens.id_token,
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token from previous token exchange

        Returns:
            New OAuthTokens with fresh access_token

        Raises:
            OAuthTokenExchangeError: If refresh fails
        """
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.token_url,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise OAuthTokenExchangeError(
                        f"Google token refresh failed: {error_data.get('error_description', response.text)}",
                        provider=self.provider_name,
                        details=error_data,
                    )

                data = response.json()

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                f"HTTP error during Google token refresh: {str(e)}",
                provider=self.provider_name,
            )

        expires_at = None
        expires_in = data.get("expires_in")
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return OAuthTokens(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            refresh_token=data.get("refresh_token", refresh_token),  # May not return new refresh token
            id_token=data.get("id_token"),
            scope=data.get("scope"),
            expires_in=expires_in,
            expires_at=expires_at,
        )
