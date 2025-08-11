"""
Tests for authentication endpoints
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt

from auth_kit_fastapi.core.security import get_password_hash


class TestAuthEndpoints:
    """Test authentication API endpoints"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "firstName": "New",
                "lastName": "User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["firstName"] == "New"
        assert data["lastName"] == "User"
        assert "id" in data
        assert "hashed_password" not in data
        
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "password": "password123",
                "firstName": "Duplicate",
                "lastName": "User"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
        
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "password123",
                "firstName": "Invalid",
                "lastName": "Email"
            }
        )
        
        assert response.status_code == 422
        
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert data["user"]["email"] == test_user.email
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
        assert data["tokens"]["token_type"] == "bearer"
        assert "requires_2fa" not in data or data["requires_2fa"] is False
        
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
        
    def test_login_inactive_user(self, client, db, test_user):
        """Test login with inactive user"""
        test_user.is_active = False
        db.commit()
        
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "password123"
            }
        )
        
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"]
        
    def test_login_with_2fa(self, client, test_user_with_2fa):
        """Test login with 2FA enabled"""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user_with_2fa.email,
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["requires_2fa"] is True
        assert "access_token" in data["tokens"]
        assert "refresh_token" not in data["tokens"]
        assert data["message"] == "Two-factor authentication required"
        
    def test_refresh_token(self, client, test_user):
        """Test token refresh"""
        # Login first
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "password123"
            }
        )
        tokens = login_response.json()["tokens"]
        
        # Refresh token
        response = client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        
    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": "invalid-token"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]
        
    def test_logout(self, client, auth_headers):
        """Test logout"""
        response = client.post(
            "/api/auth/logout",
            headers=auth_headers,
            json={
                "refresh_token": "some-refresh-token"
            }
        )
        
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
        
    def test_logout_everywhere(self, client, auth_headers):
        """Test logout from all devices"""
        response = client.post(
            "/api/auth/logout",
            headers=auth_headers,
            json={
                "refresh_token": "some-refresh-token",
                "everywhere": True
            }
        )
        
        assert response.status_code == 200
        
    def test_get_profile(self, client, auth_headers, test_user):
        """Test get current user profile"""
        response = client.get(
            "/api/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["firstName"] == test_user.first_name
        assert data["lastName"] == test_user.last_name
        
    def test_get_profile_unauthorized(self, client):
        """Test get profile without auth"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
        
    def test_update_profile(self, client, auth_headers):
        """Test update user profile"""
        response = client.put(
            "/api/auth/me",
            headers=auth_headers,
            json={
                "firstName": "Updated",
                "lastName": "Name",
                "phoneNumber": "+1234567890"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["firstName"] == "Updated"
        assert data["lastName"] == "Name"
        assert data["phoneNumber"] == "+1234567890"
        
    def test_change_password(self, client, auth_headers):
        """Test change password"""
        response = client.post(
            "/api/auth/password/change",
            headers=auth_headers,
            json={
                "current_password": "password123",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]
        
        # Try login with new password
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": "test@example.com",
                "password": "newpassword123"
            }
        )
        assert login_response.status_code == 200
        
    def test_change_password_wrong_current(self, client, auth_headers):
        """Test change password with wrong current password"""
        response = client.post(
            "/api/auth/password/change",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"]
        
    def test_request_password_reset(self, client, test_user):
        """Test password reset request"""
        response = client.post(
            "/api/auth/password/reset",
            json={
                "email": test_user.email
            }
        )
        
        assert response.status_code == 200
        assert "If the email exists" in response.json()["message"]
        
    def test_request_password_reset_nonexistent(self, client):
        """Test password reset for non-existent email"""
        response = client.post(
            "/api/auth/password/reset",
            json={
                "email": "nonexistent@example.com"
            }
        )
        
        # Should still return 200 to prevent email enumeration
        assert response.status_code == 200
        assert "If the email exists" in response.json()["message"]
        
    def test_verify_email(self, client, test_user_unverified, auth_config):
        """Test email verification"""
        from auth_kit_fastapi.core.security import generate_email_verification_token
        
        # Generate verification token
        token = generate_email_verification_token(
            test_user_unverified.email,
            auth_config.jwt_secret
        )
        
        response = client.get(f"/api/auth/verify-email/{token}")
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"]
        
    def test_verify_email_invalid_token(self, client):
        """Test email verification with invalid token"""
        response = client.get("/api/auth/verify-email/invalid-token")
        
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]
        
    def test_resend_verification(self, client, db, test_user):
        """Test resend email verification"""
        # Make user unverified
        test_user.is_verified = False
        db.commit()
        
        # Get auth token
        login_response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "password123"
            }
        )
        token = login_response.json()["tokens"]["access_token"]
        
        response = client.post(
            "/api/auth/resend-verification",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "sent" in response.json()["message"]
        
    def test_resend_verification_already_verified(self, client, auth_headers):
        """Test resend verification for already verified user"""
        response = client.post(
            "/api/auth/resend-verification",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "already verified" in response.json()["message"]