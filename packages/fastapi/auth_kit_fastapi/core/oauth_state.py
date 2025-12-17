"""
OAuth state protection using signed JWT tokens.

Provides CSRF protection for OAuth flows by generating and validating
signed JWT state tokens with short expiration (10 minutes by default).

State JWT contains:
- type: "oauth_state" (identifies this as an OAuth state token)
- provider: OAuth provider name (google, github, apple)
- redirect_uri: Callback redirect URI
- mode: "login" or "link"
- cc: code_challenge (binds state to PKCE)
- link_user_id: User ID when linking (for mode="link")
- nonce: Random value for additional entropy
- iat: Issued at timestamp
- exp: Expiration timestamp (iat + 10 minutes)
"""

import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from jose import jwt, JWTError

logger = logging.getLogger(__name__)


class OAuthStateError(Exception):
    """Base exception for OAuth state errors."""
    pass


class OAuthStateExpiredError(OAuthStateError):
    """State token has expired."""
    pass


class OAuthStateInvalidError(OAuthStateError):
    """State token is invalid (tampered, malformed, or wrong type)."""
    pass


class OAuthStateMissingFieldError(OAuthStateError):
    """State token is missing required fields."""
    pass


def sign_state(
    provider: str,
    redirect_uri: str,
    mode: str,
    signing_key: str,
    code_challenge: Optional[str] = None,
    link_user_id: Optional[str] = None,
    expiry_seconds: int = 600,
    algorithm: str = "HS256",
) -> str:
    """
    Generate a signed JWT state token for OAuth flow.

    Args:
        provider: OAuth provider name (google, github, apple)
        redirect_uri: Callback redirect URI
        mode: "login" or "link"
        signing_key: Secret key for signing the JWT
        code_challenge: PKCE code challenge to bind to state
        link_user_id: User ID when linking an account (required for mode="link")
        expiry_seconds: Token expiration in seconds (default: 600 = 10 minutes)
        algorithm: JWT signing algorithm (default: HS256)

    Returns:
        Signed JWT state string

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if not provider:
        raise ValueError("provider is required")
    if not redirect_uri:
        raise ValueError("redirect_uri is required")
    if mode not in ("login", "link"):
        raise ValueError("mode must be 'login' or 'link'")
    if mode == "link" and not link_user_id:
        raise ValueError("link_user_id is required when mode='link'")

    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=expiry_seconds)

    payload = {
        "type": "oauth_state",
        "provider": provider,
        "redirect_uri": redirect_uri,
        "mode": mode,
        "nonce": secrets.token_urlsafe(16),
        "iat": now,
        "exp": exp,
    }

    if code_challenge:
        payload["cc"] = code_challenge

    if link_user_id:
        # Convert UUID to string if needed
        if isinstance(link_user_id, UUID):
            link_user_id = str(link_user_id)
        payload["link_user_id"] = link_user_id

    return jwt.encode(payload, signing_key, algorithm=algorithm)


def verify_state(
    state: str,
    signing_key: str,
    expected_provider: Optional[str] = None,
    expected_redirect_uri: Optional[str] = None,
    expected_mode: Optional[str] = None,
    algorithm: str = "HS256",
) -> Dict[str, Any]:
    """
    Verify and decode a signed JWT state token.

    Args:
        state: JWT state string to verify
        signing_key: Secret key for verifying the signature
        expected_provider: If provided, verify provider matches
        expected_redirect_uri: If provided, verify redirect_uri matches
        expected_mode: If provided, verify mode matches
        algorithm: JWT signing algorithm (default: HS256)

    Returns:
        Decoded state payload dictionary with keys:
        - provider: str
        - redirect_uri: str
        - mode: str ("login" or "link")
        - cc: Optional[str] (code_challenge)
        - link_user_id: Optional[str] (for link mode)
        - nonce: str
        - iat: datetime
        - exp: datetime

    Raises:
        OAuthStateExpiredError: If state has expired
        OAuthStateInvalidError: If state is tampered, malformed, or wrong type
        OAuthStateMissingFieldError: If required fields are missing
    """
    try:
        payload = jwt.decode(state, signing_key, algorithms=[algorithm])
    except JWTError as e:
        error_str = str(e).lower()
        if "expired" in error_str:
            logger.debug("OAuth state expired")
            raise OAuthStateExpiredError("OAuth state has expired")
        logger.debug(f"OAuth state decode failed: {type(e).__name__}")
        raise OAuthStateInvalidError("Invalid OAuth state token")

    # Verify token type
    if payload.get("type") != "oauth_state":
        logger.debug("OAuth state has wrong type claim")
        raise OAuthStateInvalidError("Invalid state token type")

    # Check required fields
    required_fields = ["provider", "redirect_uri", "mode"]
    for field in required_fields:
        if field not in payload:
            logger.debug(f"OAuth state missing required field: {field}")
            raise OAuthStateMissingFieldError(f"State missing required field: {field}")

    # Validate mode
    if payload["mode"] not in ("login", "link"):
        raise OAuthStateInvalidError("Invalid mode in state")

    # For link mode, require link_user_id
    if payload["mode"] == "link" and not payload.get("link_user_id"):
        raise OAuthStateMissingFieldError("State missing link_user_id for link mode")

    # Optional field matching
    if expected_provider and payload["provider"] != expected_provider:
        logger.debug(
            f"OAuth state provider mismatch: expected {expected_provider}, got {payload['provider']}"
        )
        raise OAuthStateInvalidError("State provider mismatch")

    if expected_redirect_uri and payload["redirect_uri"] != expected_redirect_uri:
        logger.debug("OAuth state redirect_uri mismatch")
        raise OAuthStateInvalidError("State redirect_uri mismatch")

    if expected_mode and payload["mode"] != expected_mode:
        logger.debug(f"OAuth state mode mismatch: expected {expected_mode}, got {payload['mode']}")
        raise OAuthStateInvalidError("State mode mismatch")

    return payload


def create_state_for_authorize(
    provider: str,
    redirect_uri: str,
    mode: str,
    code_challenge: str,
    signing_key: str,
    link_user_id: Optional[str] = None,
    expiry_seconds: int = 600,
) -> str:
    """
    Convenience function to create state for OAuth authorize endpoint.

    This is the primary function to use when starting an OAuth flow.

    Args:
        provider: OAuth provider name
        redirect_uri: Callback redirect URI
        mode: "login" or "link"
        code_challenge: PKCE code challenge
        signing_key: Secret key for signing
        link_user_id: User ID when linking (required for mode="link")
        expiry_seconds: Token expiration in seconds

    Returns:
        Signed JWT state string
    """
    return sign_state(
        provider=provider,
        redirect_uri=redirect_uri,
        mode=mode,
        signing_key=signing_key,
        code_challenge=code_challenge,
        link_user_id=link_user_id,
        expiry_seconds=expiry_seconds,
    )


def verify_state_for_callback(
    state: str,
    signing_key: str,
    expected_provider: str,
    expected_redirect_uri: str,
) -> Dict[str, Any]:
    """
    Convenience function to verify state in OAuth callback.

    This is the primary function to use when processing OAuth callback.

    Args:
        state: JWT state string from callback
        signing_key: Secret key for verification
        expected_provider: Provider that should match
        expected_redirect_uri: Redirect URI that should match

    Returns:
        Verified state payload

    Raises:
        OAuthStateExpiredError: If state has expired
        OAuthStateInvalidError: If state is invalid
        OAuthStateMissingFieldError: If required fields missing
    """
    return verify_state(
        state=state,
        signing_key=signing_key,
        expected_provider=expected_provider,
        expected_redirect_uri=expected_redirect_uri,
    )
