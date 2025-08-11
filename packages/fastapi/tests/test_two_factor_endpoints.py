"""
Tests for two-factor authentication endpoints
"""

import pytest
import pyotp
import json
from unittest.mock import patch

from auth_kit_fastapi.core.security import hash_recovery_code, verify_recovery_code


class TestTwoFactorEndpoints:
    """Test 2FA API endpoints"""
    
    def test_get_2fa_status_disabled(self, client, auth_headers):
        """Test get 2FA status when disabled"""
        response = client.get(
            "/api/2fa/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["method"] is None
        assert data["backup_codes_remaining"] is None
        
    def test_get_2fa_status_enabled(self, client, db, test_user_with_2fa):
        """Test get 2FA status when enabled"""
        # Login to get auth token
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        # Complete 2FA login
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        code = totp.now()
        
        verify_response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": code, "is_recovery_code": False}
        )
        
        access_token = verify_response.json()["tokens"]["access_token"]
        
        # Get status
        response = client.get(
            "/api/2fa/status",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["method"] == "totp"
        assert data["backup_codes_remaining"] == 3  # Based on test fixture
        
    def test_begin_2fa_setup(self, client, auth_headers):
        """Test begin 2FA setup"""
        with client as c:
            response = c.post(
                "/api/2fa/setup/begin",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "secret" in data
            assert "qr_code" in data
            assert data["qr_code"].startswith("data:image/png;base64,")
            assert "manual_entry_key" in data
            assert data["manual_entry_key"] == data["secret"]
            
            # Verify session contains temp secret
            with c.session() as session:
                assert "2fa_temp_secret" in session
                
    def test_begin_2fa_setup_already_enabled(self, client, db, test_user_with_2fa):
        """Test begin 2FA setup when already enabled"""
        # Get full auth token for 2FA user
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        code = totp.now()
        
        verify_response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": code, "is_recovery_code": False}
        )
        
        access_token = verify_response.json()["tokens"]["access_token"]
        
        response = client.post(
            "/api/2fa/setup/begin",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status_code == 400
        assert "already enabled" in response.json()["detail"]
        
    def test_verify_2fa_setup(self, client, auth_headers):
        """Test verify 2FA setup"""
        with client as c:
            # Begin setup
            begin_response = c.post(
                "/api/2fa/setup/begin",
                headers=auth_headers
            )
            secret = begin_response.json()["secret"]
            
            # Generate valid TOTP code
            totp = pyotp.TOTP(secret)
            code = totp.now()
            
            # Verify setup
            response = c.post(
                "/api/2fa/setup/verify",
                headers=auth_headers,
                json={"code": code}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "recovery_codes" in data
            assert len(data["recovery_codes"]) == 8  # Based on config
            assert all("-" in code for code in data["recovery_codes"])
            assert "enabled" in data["message"]
            
    def test_verify_2fa_setup_invalid_code(self, client, auth_headers):
        """Test verify 2FA setup with invalid code"""
        with client as c:
            # Begin setup
            c.post(
                "/api/2fa/setup/begin",
                headers=auth_headers
            )
            
            # Try invalid code
            response = c.post(
                "/api/2fa/setup/verify",
                headers=auth_headers,
                json={"code": "000000"}
            )
            
            assert response.status_code == 400
            assert "Invalid verification code" in response.json()["detail"]
            
    def test_verify_2fa_setup_no_session(self, client, auth_headers):
        """Test verify 2FA setup without session"""
        response = client.post(
            "/api/2fa/setup/verify",
            headers=auth_headers,
            json={"code": "123456"}
        )
        
        assert response.status_code == 400
        assert "session expired" in response.json()["detail"]
        
    def test_disable_2fa(self, client, db, test_user_with_2fa):
        """Test disable 2FA"""
        # Get full auth token
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        code = totp.now()
        
        verify_response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": code, "is_recovery_code": False}
        )
        
        access_token = verify_response.json()["tokens"]["access_token"]
        
        # Disable 2FA
        response = client.post(
            "/api/2fa/disable",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"password": "password123"}
        )
        
        assert response.status_code == 200
        assert "disabled" in response.json()["message"]
        
        # Verify it's disabled in DB
        db.refresh(test_user_with_2fa)
        assert test_user_with_2fa.two_factor_enabled is False
        assert test_user_with_2fa.two_factor_secret is None
        
    def test_disable_2fa_wrong_password(self, client, db, test_user_with_2fa):
        """Test disable 2FA with wrong password"""
        # Get full auth token (abbreviated for brevity)
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        code = totp.now()
        
        verify_response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": code, "is_recovery_code": False}
        )
        
        access_token = verify_response.json()["tokens"]["access_token"]
        
        response = client.post(
            "/api/2fa/disable",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"password": "wrongpassword"}
        )
        
        assert response.status_code == 400
        assert "Incorrect password" in response.json()["detail"]
        
    def test_regenerate_recovery_codes(self, client, db, test_user_with_2fa):
        """Test regenerate recovery codes"""
        # Get full auth token
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        code = totp.now()
        
        verify_response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": code, "is_recovery_code": False}
        )
        
        access_token = verify_response.json()["tokens"]["access_token"]
        
        # Regenerate codes
        response = client.post(
            "/api/2fa/recovery-codes",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recovery_codes" in data
        assert len(data["recovery_codes"]) == 8
        assert "generated" in data["message"]
        
        # Verify old codes don't work
        old_codes = ["AAAA-BBBB", "CCCC-DDDD", "EEEE-FFFF"]
        db.refresh(test_user_with_2fa)
        stored_codes = json.loads(test_user_with_2fa.two_factor_recovery_codes)
        
        for old_code in old_codes:
            assert not any(
                verify_recovery_code(old_code, stored["code"]) 
                for stored in stored_codes
            )
            
    def test_verify_2fa_login_with_totp(self, client, test_user_with_2fa):
        """Test verify 2FA login with TOTP code"""
        # First login to get temp token
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        
        assert login_response.json()["requires_2fa"] is True
        temp_token = login_response.json()["tokens"]["access_token"]
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        code = totp.now()
        
        # Verify 2FA
        response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": code, "is_recovery_code": False}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == test_user_with_2fa.email
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        
    def test_verify_2fa_login_with_recovery_code(self, client, db, test_user_with_2fa):
        """Test verify 2FA login with recovery code"""
        # First login
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        # Use recovery code
        response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": "AAAA-BBBB", "is_recovery_code": True}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "tokens" in data
        
        # Verify recovery code is marked as used
        db.refresh(test_user_with_2fa)
        stored_codes = json.loads(test_user_with_2fa.two_factor_recovery_codes)
        used_code = next(
            (c for c in stored_codes if verify_recovery_code("AAAA-BBBB", c["code"])),
            None
        )
        assert used_code is not None
        assert used_code["used"] is True
        
    def test_verify_2fa_login_invalid_code(self, client, test_user_with_2fa):
        """Test verify 2FA login with invalid code"""
        # First login
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        temp_token = login_response.json()["tokens"]["access_token"]
        
        response = client.post(
            "/api/2fa/verify/login",
            headers={"Authorization": f"Bearer {temp_token}"},
            json={"code": "000000", "is_recovery_code": False}
        )
        
        assert response.status_code == 400
        assert "Invalid verification code" in response.json()["detail"]