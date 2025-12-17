"""
Tests for OAuth state JWT signing and verification.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from jose import jwt

from auth_kit_fastapi.core.oauth_state import (
    sign_state,
    verify_state,
    create_state_for_authorize,
    verify_state_for_callback,
    OAuthStateError,
    OAuthStateExpiredError,
    OAuthStateInvalidError,
    OAuthStateMissingFieldError,
)


TEST_SIGNING_KEY = "test-secret-key-for-oauth-state"


class TestSignState:
    """Tests for sign_state function."""

    def test_sign_state_login_mode(self):
        """Test signing state for login mode."""
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        assert state is not None
        assert isinstance(state, str)

        # Verify it's a valid JWT
        payload = jwt.decode(state, TEST_SIGNING_KEY, algorithms=["HS256"])
        assert payload["type"] == "oauth_state"
        assert payload["provider"] == "google"
        assert payload["redirect_uri"] == "http://localhost:3000/callback"
        assert payload["mode"] == "login"
        assert "nonce" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_sign_state_link_mode(self):
        """Test signing state for link mode requires link_user_id."""
        user_id = str(uuid4())

        state = sign_state(
            provider="github",
            redirect_uri="http://localhost:3000/callback",
            mode="link",
            signing_key=TEST_SIGNING_KEY,
            link_user_id=user_id,
        )

        payload = jwt.decode(state, TEST_SIGNING_KEY, algorithms=["HS256"])
        assert payload["mode"] == "link"
        assert payload["link_user_id"] == user_id

    def test_sign_state_link_mode_requires_user_id(self):
        """Test that link mode requires link_user_id."""
        with pytest.raises(ValueError) as exc_info:
            sign_state(
                provider="google",
                redirect_uri="http://localhost:3000/callback",
                mode="link",
                signing_key=TEST_SIGNING_KEY,
            )

        assert "link_user_id is required" in str(exc_info.value)

    def test_sign_state_with_code_challenge(self):
        """Test signing state with PKCE code challenge."""
        code_challenge = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"

        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
            code_challenge=code_challenge,
        )

        payload = jwt.decode(state, TEST_SIGNING_KEY, algorithms=["HS256"])
        assert payload["cc"] == code_challenge

    def test_sign_state_expiry(self):
        """Test state expiration is set correctly."""
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
            expiry_seconds=300,  # 5 minutes
        )

        payload = jwt.decode(state, TEST_SIGNING_KEY, algorithms=["HS256"])

        # Check expiry is roughly 5 minutes from now
        exp = payload["exp"]
        iat = payload["iat"]
        assert exp - iat == 300

    def test_sign_state_missing_provider(self):
        """Test that provider is required."""
        with pytest.raises(ValueError) as exc_info:
            sign_state(
                provider="",
                redirect_uri="http://localhost:3000/callback",
                mode="login",
                signing_key=TEST_SIGNING_KEY,
            )

        assert "provider is required" in str(exc_info.value)

    def test_sign_state_missing_redirect_uri(self):
        """Test that redirect_uri is required."""
        with pytest.raises(ValueError) as exc_info:
            sign_state(
                provider="google",
                redirect_uri="",
                mode="login",
                signing_key=TEST_SIGNING_KEY,
            )

        assert "redirect_uri is required" in str(exc_info.value)

    def test_sign_state_invalid_mode(self):
        """Test that mode must be 'login' or 'link'."""
        with pytest.raises(ValueError) as exc_info:
            sign_state(
                provider="google",
                redirect_uri="http://localhost:3000/callback",
                mode="invalid",
                signing_key=TEST_SIGNING_KEY,
            )

        assert "mode must be 'login' or 'link'" in str(exc_info.value)

    def test_sign_state_different_nonces(self):
        """Test that each state gets a different nonce."""
        state1 = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )
        state2 = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        payload1 = jwt.decode(state1, TEST_SIGNING_KEY, algorithms=["HS256"])
        payload2 = jwt.decode(state2, TEST_SIGNING_KEY, algorithms=["HS256"])

        assert payload1["nonce"] != payload2["nonce"]


class TestVerifyState:
    """Tests for verify_state function."""

    def test_verify_state_roundtrip(self):
        """Test that verify_state decodes a valid state."""
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
            code_challenge="test_challenge",
        )

        payload = verify_state(state, TEST_SIGNING_KEY)

        assert payload["provider"] == "google"
        assert payload["redirect_uri"] == "http://localhost:3000/callback"
        assert payload["mode"] == "login"
        assert payload["cc"] == "test_challenge"
        assert payload["type"] == "oauth_state"

    def test_verify_state_with_expected_provider(self):
        """Test verification with expected provider matching."""
        state = sign_state(
            provider="github",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        # Should succeed with matching provider
        payload = verify_state(state, TEST_SIGNING_KEY, expected_provider="github")
        assert payload["provider"] == "github"

    def test_verify_state_provider_mismatch(self):
        """Test that provider mismatch raises error."""
        state = sign_state(
            provider="github",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        with pytest.raises(OAuthStateInvalidError) as exc_info:
            verify_state(state, TEST_SIGNING_KEY, expected_provider="google")

        assert "provider mismatch" in str(exc_info.value)

    def test_verify_state_redirect_uri_mismatch(self):
        """Test that redirect_uri mismatch raises error."""
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        with pytest.raises(OAuthStateInvalidError) as exc_info:
            verify_state(
                state,
                TEST_SIGNING_KEY,
                expected_redirect_uri="http://evil.com/callback",
            )

        assert "redirect_uri mismatch" in str(exc_info.value)

    def test_verify_state_expired(self):
        """Test that expired state raises error."""
        # Create state with 0 second expiry (already expired)
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
            expiry_seconds=0,
        )

        # Wait a moment for expiry
        time.sleep(0.1)

        with pytest.raises(OAuthStateExpiredError) as exc_info:
            verify_state(state, TEST_SIGNING_KEY)

        assert "expired" in str(exc_info.value).lower()

    def test_verify_state_tampered(self):
        """Test that tampered state raises error."""
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        # Tamper with the state
        tampered = state[:-5] + "XXXXX"

        with pytest.raises(OAuthStateInvalidError):
            verify_state(tampered, TEST_SIGNING_KEY)

    def test_verify_state_wrong_key(self):
        """Test that wrong signing key raises error."""
        state = sign_state(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            signing_key=TEST_SIGNING_KEY,
        )

        with pytest.raises(OAuthStateInvalidError):
            verify_state(state, "wrong-key")

    def test_verify_state_wrong_type(self):
        """Test that wrong token type raises error."""
        # Create a JWT with wrong type
        payload = {
            "type": "access_token",  # Wrong type
            "provider": "google",
            "redirect_uri": "http://localhost:3000/callback",
            "mode": "login",
            "nonce": "test",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        state = jwt.encode(payload, TEST_SIGNING_KEY, algorithm="HS256")

        with pytest.raises(OAuthStateInvalidError) as exc_info:
            verify_state(state, TEST_SIGNING_KEY)

        assert "type" in str(exc_info.value).lower()

    def test_verify_state_missing_provider(self):
        """Test that missing provider raises error."""
        payload = {
            "type": "oauth_state",
            "redirect_uri": "http://localhost:3000/callback",
            "mode": "login",
            "nonce": "test",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        state = jwt.encode(payload, TEST_SIGNING_KEY, algorithm="HS256")

        with pytest.raises(OAuthStateMissingFieldError) as exc_info:
            verify_state(state, TEST_SIGNING_KEY)

        assert "provider" in str(exc_info.value)

    def test_verify_state_link_mode_missing_user_id(self):
        """Test that link mode without link_user_id raises error."""
        payload = {
            "type": "oauth_state",
            "provider": "google",
            "redirect_uri": "http://localhost:3000/callback",
            "mode": "link",  # Link mode without link_user_id
            "nonce": "test",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        state = jwt.encode(payload, TEST_SIGNING_KEY, algorithm="HS256")

        with pytest.raises(OAuthStateMissingFieldError) as exc_info:
            verify_state(state, TEST_SIGNING_KEY)

        assert "link_user_id" in str(exc_info.value)

    def test_verify_state_invalid_mode(self):
        """Test that invalid mode raises error."""
        payload = {
            "type": "oauth_state",
            "provider": "google",
            "redirect_uri": "http://localhost:3000/callback",
            "mode": "invalid",
            "nonce": "test",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        }
        state = jwt.encode(payload, TEST_SIGNING_KEY, algorithm="HS256")

        with pytest.raises(OAuthStateInvalidError) as exc_info:
            verify_state(state, TEST_SIGNING_KEY)

        assert "mode" in str(exc_info.value).lower()


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_state_for_authorize(self):
        """Test create_state_for_authorize convenience function."""
        state = create_state_for_authorize(
            provider="google",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            code_challenge="test_challenge",
            signing_key=TEST_SIGNING_KEY,
        )

        payload = verify_state(state, TEST_SIGNING_KEY)
        assert payload["provider"] == "google"
        assert payload["cc"] == "test_challenge"

    def test_verify_state_for_callback(self):
        """Test verify_state_for_callback convenience function."""
        state = create_state_for_authorize(
            provider="github",
            redirect_uri="http://localhost:3000/callback",
            mode="login",
            code_challenge="test_challenge",
            signing_key=TEST_SIGNING_KEY,
        )

        payload = verify_state_for_callback(
            state=state,
            signing_key=TEST_SIGNING_KEY,
            expected_provider="github",
            expected_redirect_uri="http://localhost:3000/callback",
        )

        assert payload["provider"] == "github"
        assert payload["redirect_uri"] == "http://localhost:3000/callback"

    def test_link_mode_flow(self):
        """Test complete link mode flow."""
        user_id = str(uuid4())

        # Create state for linking
        state = create_state_for_authorize(
            provider="apple",
            redirect_uri="http://localhost:3000/callback",
            mode="link",
            code_challenge="link_challenge",
            signing_key=TEST_SIGNING_KEY,
            link_user_id=user_id,
        )

        # Verify in callback
        payload = verify_state_for_callback(
            state=state,
            signing_key=TEST_SIGNING_KEY,
            expected_provider="apple",
            expected_redirect_uri="http://localhost:3000/callback",
        )

        assert payload["mode"] == "link"
        assert payload["link_user_id"] == user_id
        assert payload["cc"] == "link_challenge"


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_exceptions_inherit_from_base(self):
        """Test all exceptions inherit from OAuthStateError."""
        assert issubclass(OAuthStateExpiredError, OAuthStateError)
        assert issubclass(OAuthStateInvalidError, OAuthStateError)
        assert issubclass(OAuthStateMissingFieldError, OAuthStateError)

    def test_catch_all_state_errors(self):
        """Test that base exception catches all specific errors."""
        # Create an expired state by backdating it
        now = datetime.now(timezone.utc)
        payload = {
            "type": "oauth_state",
            "provider": "google",
            "redirect_uri": "http://localhost:3000/callback",
            "mode": "login",
            "nonce": "test",
            "iat": now - timedelta(minutes=15),
            "exp": now - timedelta(minutes=5),  # Expired 5 minutes ago
        }
        state = jwt.encode(payload, TEST_SIGNING_KEY, algorithm="HS256")

        # Should be caught by base exception
        with pytest.raises(OAuthStateError):
            verify_state(state, TEST_SIGNING_KEY)
