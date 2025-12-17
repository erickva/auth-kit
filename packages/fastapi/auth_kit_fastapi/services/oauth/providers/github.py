"""
GitHub OAuth provider implementation.

Uses GitHub OAuth 2.0 with PKCE S256 for secure authorization.
Endpoints:
- Authorize: https://github.com/login/oauth/authorize
- Token: https://github.com/login/oauth/access_token
- User: https://api.github.com/user
- Emails: https://api.github.com/user/emails
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx

from .base import (
    OAuthProvider,
    OAuthProfile,
    OAuthTokens,
    OAuthTokenExchangeError,
    OAuthProfileError,
)


class GitHubProvider(OAuthProvider):
    """
    GitHub OAuth 2.0 provider with PKCE support.

    GitHub requires special handling:
    - Token endpoint returns JSON when Accept header is set
    - User profile comes from /user endpoint
    - Email may need separate /user/emails call if not public
    """

    provider_name = "github"
    authorize_url = "https://github.com/login/oauth/authorize"
    token_url = "https://github.com/login/oauth/access_token"
    user_url = "https://api.github.com/user"
    emails_url = "https://api.github.com/user/emails"

    default_scopes = [
        "read:user",
        "user:email",
    ]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        timeout: float = 30.0,
        **kwargs
    ):
        """
        Initialize GitHub OAuth provider.

        Args:
            client_id: GitHub OAuth App Client ID
            client_secret: GitHub OAuth App Client Secret
            timeout: HTTP request timeout in seconds
        """
        super().__init__(client_id, client_secret, **kwargs)
        self.timeout = timeout

    async def exchange_token(
        self,
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for GitHub tokens.

        Args:
            code: Authorization code from GitHub callback
            code_verifier: PKCE code verifier
            redirect_uri: Redirect URI used in authorization

        Returns:
            OAuthTokens with access_token (GitHub doesn't provide refresh tokens)

        Raises:
            OAuthTokenExchangeError: If token exchange fails
        """
        if not code_verifier:
            raise OAuthTokenExchangeError(
                "PKCE code_verifier is required for GitHub OAuth",
                provider=self.provider_name,
            )

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.token_url,
                    data=payload,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )

                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    raise OAuthTokenExchangeError(
                        f"GitHub token exchange failed: {response.text}",
                        provider=self.provider_name,
                        details=error_data,
                    )

                data = response.json()

                # GitHub returns error in JSON body with 200 status
                if "error" in data:
                    raise OAuthTokenExchangeError(
                        f"GitHub token exchange failed: {data.get('error_description', data['error'])}",
                        provider=self.provider_name,
                        details=data,
                    )

        except httpx.HTTPError as e:
            raise OAuthTokenExchangeError(
                f"HTTP error during GitHub token exchange: {str(e)}",
                provider=self.provider_name,
            )

        access_token = data.get("access_token")
        if not access_token:
            raise OAuthTokenExchangeError(
                "GitHub response missing access_token",
                provider=self.provider_name,
                details=data,
            )

        # GitHub tokens don't expire by default (unless using GitHub Apps)
        # Parse expires_in if present
        expires_at = None
        expires_in = data.get("expires_in")
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        return OAuthTokens(
            access_token=access_token,
            token_type=data.get("token_type", "bearer"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
            expires_in=expires_in,
            expires_at=expires_at,
        )

    async def fetch_profile(self, tokens: OAuthTokens) -> OAuthProfile:
        """
        Fetch user profile from GitHub API.

        Fetches from /user endpoint and optionally /user/emails
        if the user's email is not public.

        Args:
            tokens: OAuth tokens from exchange_token()

        Returns:
            Normalized OAuthProfile with GitHub user information

        Raises:
            OAuthProfileError: If profile fetch fails
        """
        headers = {
            "Authorization": f"Bearer {tokens.access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Fetch user profile
                response = await client.get(self.user_url, headers=headers)

                if response.status_code != 200:
                    raise OAuthProfileError(
                        f"GitHub user fetch failed: {response.text}",
                        provider=self.provider_name,
                    )

                user_data = response.json()

                # Fetch primary verified email from /user/emails
                email, email_verified = await self._fetch_primary_email(client, headers)

                # Fall back to public email if email list is unavailable
                if not email:
                    email = user_data.get("email")
                    email_verified = None

        except httpx.HTTPError as e:
            raise OAuthProfileError(
                f"HTTP error fetching GitHub profile: {str(e)}",
                provider=self.provider_name,
            )

        # GitHub uses 'id' as the unique user identifier
        provider_user_id = str(user_data.get("id"))
        if not provider_user_id:
            raise OAuthProfileError(
                "GitHub profile missing 'id'",
                provider=self.provider_name,
                details=user_data,
            )

        return OAuthProfile(
            provider=self.provider_name,
            provider_user_id=provider_user_id,
            email=email,
            username=user_data.get("login"),
            email_verified=email_verified,
        )

    async def _fetch_primary_email(
        self,
        client: httpx.AsyncClient,
        headers: Dict[str, str]
    ) -> tuple[Optional[str], Optional[bool]]:
        """
        Fetch user's primary email from /user/emails endpoint.

        Args:
            client: httpx AsyncClient
            headers: Authorization headers

        Returns:
            Tuple of (email, verified) or (None, None) if not found
        """
        try:
            response = await client.get(self.emails_url, headers=headers)

            if response.status_code != 200:
                return None, None

            emails: List[Dict] = response.json()

            # Find primary verified email
            for email_entry in emails:
                if email_entry.get("primary") and email_entry.get("verified"):
                    return email_entry.get("email"), True

            # Fallback to any verified email
            for email_entry in emails:
                if email_entry.get("verified"):
                    return email_entry.get("email"), True

            # Fallback to primary email even if unverified
            for email_entry in emails:
                if email_entry.get("primary"):
                    return email_entry.get("email"), False

            return None, None

        except Exception:
            # Don't fail the whole flow if email fetch fails
            return None, None
