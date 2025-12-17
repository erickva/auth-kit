"""
Apple OAuth provider implementation.

Uses Sign in with Apple with PKCE S256 and ES256 JWT client_secret.
Endpoints:
- Authorize: https://appleid.apple.com/auth/authorize
- Token: https://appleid.apple.com/auth/token

Apple is unique:
- client_secret is a JWT signed with ES256 using Apple's private key
- User profile comes from id_token, not a separate API endpoint
- Email may only be provided on first authorization
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx
from jose import jwt
from jose.exceptions import JWTError
from cryptography.hazmat.primitives import serialization

from .base import (
    OAuthProvider,
    OAuthProfile,
    OAuthTokens,
    OAuthTokenExchangeError,
    OAuthProfileError,
)


class AppleProvider(OAuthProvider):
    """
    Apple Sign In provider with ES256 JWT client_secret.

    Apple requires generating a client_secret JWT on each token request,
    signed with the private key downloaded from Apple Developer Console.
    """

    provider_name = "apple"
    authorize_url = "https://appleid.apple.com/auth/authorize"
    token_url = "https://appleid.apple.com/auth/token"

    default_scopes = [
        "openid",
        "email",
        "name",
    ]
    jwks_url = "https://appleid.apple.com/auth/keys"
    jwks_cache_ttl_seconds = 3600
    _jwks_cache: Optional[Dict[str, Any]] = None
    _jwks_cached_at: float = 0.0

    def __init__(
        self,
        client_id: str,
        team_id: str,
        key_id: str,
        private_key: str,
        timeout: float = 30.0,
        **kwargs
    ):
        """
        Initialize Apple OAuth provider.

        Args:
            client_id: Apple Service ID (e.g., com.example.app.web)
            team_id: Apple Team ID from Developer Console
            key_id: Key ID of the private key
            private_key: PEM-formatted private key content
            timeout: HTTP request timeout in seconds
        """
        super().__init__(client_id, None, **kwargs)
        self.team_id = team_id
        self.key_id = key_id
        self.private_key = private_key
        self.timeout = timeout

    def _get_extra_authorize_params(self) -> Dict[str, str]:
        """Add Apple-specific authorization parameters."""
        return {
            "response_mode": "query",
        }

    def _generate_client_secret(self) -> str:
        """
        Generate Apple client_secret JWT.

        Apple requires a JWT signed with ES256 algorithm using the
        private key from Apple Developer Console.

        Returns:
            JWT string to use as client_secret
        """
        now = int(time.time())

        headers = {
            "alg": "ES256",
            "kid": self.key_id,
        }

        payload = {
            "iss": self.team_id,
            "iat": now,
            "exp": now + 86400 * 180,  # Max 6 months validity
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
        }

        return jwt.encode(
            payload,
            self.private_key,
            algorithm="ES256",
            headers=headers,
        )

    async def exchange_token(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for Apple tokens.

        Args:
            code: Authorization code from Apple callback
            code_verifier: PKCE code verifier
            redirect_uri: Redirect URI used in authorization

        Returns:
            OAuthTokens with access_token, refresh_token, and id_token

        Raises:
            OAuthTokenExchangeError: If token exchange fails
        """
        if not code_verifier:
            raise OAuthTokenExchangeError(
                "PKCE code_verifier is required for Apple OAuth",
                provider=self.provider_name,
            )

        try:
            client_secret = self._generate_client_secret()
        except Exception as e:
            raise OAuthTokenExchangeError(
                f"Failed to generate Apple client_secret: {str(e)}",
                provider=self.provider_name,
            )

        payload = {
            "client_id": self.client_id,
            "client_secret": client_secret,
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
                        f"Apple token exchange failed: {error_data.get('error_description', response.text)}",
                        provider=self.provider_name,
                        details=error_data,
                    )

                data = response.json()

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                f"HTTP error during Apple token exchange: {str(e)}",
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
            expires_in=expires_in,
            expires_at=expires_at,
        )

    async def fetch_profile(self, tokens: OAuthTokens) -> OAuthProfile:
        """
        Extract user profile from Apple id_token.

        Apple doesn't have a userinfo endpoint - all user data comes
        from decoding the id_token JWT.

        Args:
            tokens: OAuth tokens from exchange_token()

        Returns:
            Normalized OAuthProfile with Apple user information

        Raises:
            OAuthProfileError: If profile extraction fails
        """
        if not tokens.id_token:
            raise OAuthProfileError(
                "Apple tokens missing id_token",
                provider=self.provider_name,
            )

        try:
            id_token_data = await self._verify_id_token(tokens.id_token)
        except OAuthProfileError:
            raise
        except Exception as e:
            raise OAuthProfileError(
                f"Failed to verify Apple id_token: {str(e)}",
                provider=self.provider_name,
            )

        # Apple uses 'sub' as the unique user identifier
        provider_user_id = id_token_data.get("sub")
        if not provider_user_id:
            raise OAuthProfileError(
                "Apple id_token missing 'sub'",
                provider=self.provider_name,
                details=id_token_data,
            )

        # Email might be in id_token
        email = id_token_data.get("email")
        email_verified = id_token_data.get("email_verified")
        if isinstance(email_verified, str):
            email_verified = email_verified.lower() == "true"

        # Note: Apple only sends name in the first authorization
        # It's included in the 'user' POST parameter, not the id_token
        # The frontend should capture and send this separately

        return OAuthProfile(
            provider=self.provider_name,
            provider_user_id=provider_user_id,
            email=email,
            username=None,  # Apple doesn't provide username
            email_verified=email_verified if isinstance(email_verified, bool) else None,
            id_token=tokens.id_token,
        )

    async def _get_apple_jwks(self) -> Dict[str, Any]:
        """Fetch and cache Apple's JWKS."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cached_at) < self.jwks_cache_ttl_seconds:
            return self._jwks_cache

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.jwks_url)
        except httpx.HTTPError as e:
            raise OAuthProfileError(
                f"Failed to fetch Apple JWKS: {str(e)}",
                provider=self.provider_name,
            )

        if response.status_code != 200:
            raise OAuthProfileError(
                f"Apple JWKS fetch failed: {response.text}",
                provider=self.provider_name,
            )

        data = response.json()
        keys = data.get("keys")
        if not keys:
            raise OAuthProfileError(
                "Apple JWKS response missing keys",
                provider=self.provider_name,
            )

        self._jwks_cache = {"keys": keys}
        self._jwks_cached_at = now
        return self._jwks_cache

    async def _verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Apple id_token signature and claims."""
        try:
            header = jwt.get_unverified_header(id_token)
        except JWTError as e:
            raise OAuthProfileError(
                f"Invalid Apple id_token header: {str(e)}",
                provider=self.provider_name,
            )

        alg = header.get("alg")
        kid = header.get("kid")
        if alg != "RS256" or not kid:
            raise OAuthProfileError(
                "Apple id_token header missing required 'kid' or unsupported alg",
                provider=self.provider_name,
            )

        jwks = await self._get_apple_jwks()
        keys = jwks.get("keys", [])
        key = next((k for k in keys if k.get("kid") == kid), None)
        if not key:
            raise OAuthProfileError(
                "Apple JWKS does not contain matching key",
                provider=self.provider_name,
            )

        try:
            return jwt.decode(
                id_token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer="https://appleid.apple.com",
            )
        except JWTError as e:
            raise OAuthProfileError(
                f"Apple id_token verification failed: {str(e)}",
                provider=self.provider_name,
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
        try:
            client_secret = self._generate_client_secret()
        except Exception as e:
            raise OAuthTokenExchangeError(
                f"Failed to generate Apple client_secret: {str(e)}",
                provider=self.provider_name,
            )

        payload = {
            "client_id": self.client_id,
            "client_secret": client_secret,
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
                        f"Apple token refresh failed: {error_data.get('error_description', response.text)}",
                        provider=self.provider_name,
                        details=error_data,
                    )

                data = response.json()

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                f"HTTP error during Apple token refresh: {str(e)}",
                provider=self.provider_name,
            )

        expires_at = None
        expires_in = data.get("expires_in")
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return OAuthTokens(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            refresh_token=data.get("refresh_token", refresh_token),
            id_token=data.get("id_token"),
            expires_in=expires_in,
            expires_at=expires_at,
        )

    @staticmethod
    def validate_private_key(private_key: str) -> bool:
        """
        Validate that the private key can be loaded.

        Args:
            private_key: PEM-formatted private key string

        Returns:
            True if valid, raises exception otherwise
        """
        try:
            serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
            )
            return True
        except Exception as e:
            raise ValueError(f"Invalid Apple private key: {str(e)}")
