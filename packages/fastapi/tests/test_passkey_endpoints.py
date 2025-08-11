"""
Tests for passkey/WebAuthn endpoints
"""

import pytest
import base64
import json
from unittest.mock import Mock, patch

from auth_kit_fastapi.models import UserCredential


class TestPasskeyEndpoints:
    """Test passkey API endpoints"""
    
    def test_list_passkeys(self, client, auth_headers, db, test_user):
        """Test listing user passkeys"""
        # Add test passkeys
        passkey1 = UserCredential(
            user_id=test_user.id,
            credential_id="cred1",
            public_key="pubkey1",
            sign_count=0,
            name="My Phone"
        )
        passkey2 = UserCredential(
            user_id=test_user.id,
            credential_id="cred2",
            public_key="pubkey2",
            sign_count=5,
            name="My Laptop"
        )
        db.add_all([passkey1, passkey2])
        db.commit()
        
        response = client.get(
            "/api/passkeys/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["passkeys"]) == 2
        assert any(p["name"] == "My Phone" for p in data["passkeys"])
        assert any(p["name"] == "My Laptop" for p in data["passkeys"])
        
    def test_list_passkeys_unauthorized(self, client):
        """Test listing passkeys without auth"""
        response = client.get("/api/passkeys/")
        assert response.status_code == 401
        
    @patch('auth_kit_fastapi.api.passkeys.generate_registration_options')
    def test_begin_registration(self, mock_generate_options, client, auth_headers):
        """Test begin passkey registration"""
        # Mock WebAuthn response
        mock_options = Mock()
        mock_options.challenge = b'mock-challenge'
        mock_generate_options.return_value = mock_options
        
        with patch('auth_kit_fastapi.api.passkeys.options_to_json') as mock_to_json:
            mock_to_json.return_value = json.dumps({
                "challenge": "bW9jay1jaGFsbGVuZ2U=",
                "rp": {"id": "localhost", "name": "Test App"},
                "user": {
                    "id": "user-id",
                    "name": "test@example.com",
                    "displayName": "Test User"
                },
                "pubKeyCredParams": [{"alg": -7, "type": "public-key"}],
                "authenticatorSelection": {
                    "authenticatorAttachment": "platform",
                    "userVerification": "preferred"
                }
            })
            
            response = client.post(
                "/api/passkeys/register/begin",
                headers=auth_headers,
                json={"name": "My Device"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data
        assert data["rp"]["id"] == "localhost"
        assert data["user"]["name"] == "test@example.com"
        
    @patch('auth_kit_fastapi.api.passkeys.verify_registration_response')
    def test_complete_registration(self, mock_verify, client, auth_headers):
        """Test complete passkey registration"""
        # Set up session with challenge
        with client as c:
            # Store challenge in session
            with c.session() as session:
                session["passkey_challenge"] = "bW9jay1jaGFsbGVuZ2U="
            
            # Mock verification response
            mock_verification = Mock()
            mock_verification.verified = True
            mock_verification.credential_id = b'credential-id'
            mock_verification.credential_public_key = b'public-key'
            mock_verification.sign_count = 0
            mock_verify.return_value = mock_verification
            
            response = c.post(
                "/api/passkeys/register/complete",
                headers=auth_headers,
                json={
                    "name": "My Device",
                    "response": {
                        "id": "cred-id",
                        "rawId": "cred-id",
                        "response": {
                            "attestationObject": "mock-attestation",
                            "clientDataJSON": "mock-client-data"
                        },
                        "type": "public-key",
                        "authenticatorAttachment": "platform"
                    }
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Device"
        assert "id" in data
        assert data["authenticatorType"] == "platform"
        
    def test_complete_registration_no_session(self, client, auth_headers):
        """Test complete registration without session"""
        response = client.post(
            "/api/passkeys/register/complete",
            headers=auth_headers,
            json={
                "name": "My Device",
                "response": {
                    "id": "cred-id",
                    "rawId": "cred-id",
                    "response": {
                        "attestationObject": "mock-attestation",
                        "clientDataJSON": "mock-client-data"
                    },
                    "type": "public-key"
                }
            }
        )
        
        assert response.status_code == 400
        assert "session expired" in response.json()["detail"]
        
    @patch('auth_kit_fastapi.api.passkeys.generate_authentication_options')
    def test_begin_authentication(self, mock_generate_options, client):
        """Test begin passkey authentication"""
        mock_options = Mock()
        mock_options.challenge = b'auth-challenge'
        mock_generate_options.return_value = mock_options
        
        with patch('auth_kit_fastapi.api.passkeys.options_to_json') as mock_to_json:
            mock_to_json.return_value = json.dumps({
                "challenge": "YXV0aC1jaGFsbGVuZ2U=",
                "rpId": "localhost",
                "userVerification": "preferred"
            })
            
            response = client.post(
                "/api/passkeys/authenticate/begin",
                json={"email": "test@example.com"}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data
        assert data["rpId"] == "localhost"
        
    @patch('auth_kit_fastapi.api.passkeys.verify_authentication_response')
    def test_complete_authentication(self, mock_verify, client, db, test_user):
        """Test complete passkey authentication"""
        # Add test passkey
        passkey = UserCredential(
            user_id=test_user.id,
            credential_id="Y3JlZC1pZA==",  # base64 encoded
            public_key="cHVibGljLWtleQ==",  # base64 encoded
            sign_count=5,
            name="Test Device"
        )
        db.add(passkey)
        db.commit()
        
        with client as c:
            # Store challenge in session
            with c.session() as session:
                session["auth_challenge"] = "YXV0aC1jaGFsbGVuZ2U="
            
            # Mock verification
            mock_verification = Mock()
            mock_verification.verified = True
            mock_verification.new_sign_count = 6
            mock_verify.return_value = mock_verification
            
            response = c.post(
                "/api/passkeys/authenticate/complete",
                json={
                    "response": {
                        "id": "Y3JlZC1pZA==",
                        "rawId": "Y3JlZC1pZA==",
                        "response": {
                            "authenticatorData": "mock-auth-data",
                            "clientDataJSON": "mock-client-data",
                            "signature": "mock-signature"
                        },
                        "type": "public-key"
                    }
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == test_user.email
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        
    def test_delete_passkey(self, client, auth_headers, db, test_user):
        """Test delete passkey"""
        # Add test passkey
        passkey = UserCredential(
            user_id=test_user.id,
            credential_id="cred1",
            public_key="pubkey1",
            sign_count=0,
            name="My Device"
        )
        db.add(passkey)
        db.commit()
        
        response = client.delete(
            f"/api/passkeys/{passkey.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]
        
        # Verify deleted
        assert db.query(UserCredential).filter_by(id=passkey.id).first() is None
        
    def test_delete_passkey_not_found(self, client, auth_headers):
        """Test delete non-existent passkey"""
        import uuid
        response = client.delete(
            f"/api/passkeys/{uuid.uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        
    def test_delete_last_auth_method(self, client, auth_headers, db, test_user):
        """Test prevent deleting last authentication method"""
        # Remove password so passkey is last auth method
        test_user.hashed_password = None
        db.commit()
        
        # Add single passkey
        passkey = UserCredential(
            user_id=test_user.id,
            credential_id="cred1",
            public_key="pubkey1",
            sign_count=0,
            name="My Only Device"
        )
        db.add(passkey)
        db.commit()
        
        response = client.delete(
            f"/api/passkeys/{passkey.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "last authentication method" in response.json()["detail"]