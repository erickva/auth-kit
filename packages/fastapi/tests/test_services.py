"""
Tests for service classes
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json
import pyotp

from auth_kit_fastapi.services import (
    UserService,
    EmailService,
    PasskeyService,
    TwoFactorService
)
from auth_kit_fastapi.schemas.auth import UserCreate, UserUpdate
from auth_kit_fastapi.models import UserCredential


class TestUserService:
    """Test user service"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db):
        """Test create user"""
        service = UserService(db)
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="password123",
            firstName="New",
            lastName="User"
        )
        
        user = await service.create_user(user_data)
        
        assert user.email == "newuser@example.com"
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.verify_password("password123")
        assert user.is_active is True
        assert user.is_verified is False  # Default when email verification enabled
        
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, db, test_user):
        """Test create user with duplicate email"""
        service = UserService(db)
        
        user_data = UserCreate(
            email=test_user.email,
            password="password123"
        )
        
        with pytest.raises(ValueError, match="already registered"):
            await service.create_user(user_data)
            
    def test_get_user(self, db, test_user):
        """Test get user by ID"""
        service = UserService(db)
        
        user = service.get_user(test_user.id)
        assert user is not None
        assert user.email == test_user.email
        
        # Test non-existent user
        import uuid
        non_user = service.get_user(uuid.uuid4())
        assert non_user is None
        
    def test_get_user_by_email(self, db, test_user):
        """Test get user by email"""
        service = UserService(db)
        
        user = service.get_user_by_email(test_user.email)
        assert user is not None
        assert user.id == test_user.id
        
        # Test non-existent email
        non_user = service.get_user_by_email("nonexistent@example.com")
        assert non_user is None
        
    @pytest.mark.asyncio
    async def test_update_user(self, db, test_user):
        """Test update user"""
        service = UserService(db)
        
        update_data = UserUpdate(
            firstName="Updated",
            lastName="Name",
            phoneNumber="+1234567890"
        )
        
        updated = await service.update_user(test_user.id, update_data)
        
        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"
        assert updated.phone_number == "+1234567890"
        
    @pytest.mark.asyncio
    async def test_delete_user(self, db, test_user):
        """Test delete user (soft delete)"""
        service = UserService(db)
        
        result = await service.delete_user(test_user.id)
        
        assert result is True
        db.refresh(test_user)
        assert test_user.is_active is False
        
    def test_authenticate_user(self, db, test_user):
        """Test authenticate user"""
        service = UserService(db)
        
        # Valid credentials
        user = service.authenticate_user(test_user.email, "password123")
        assert user is not None
        assert user.id == test_user.id
        
        # Invalid password
        user = service.authenticate_user(test_user.email, "wrongpassword")
        assert user is None
        
        # Non-existent user
        user = service.authenticate_user("nonexistent@example.com", "password123")
        assert user is None
        
        # Inactive user
        test_user.is_active = False
        db.commit()
        user = service.authenticate_user(test_user.email, "password123")
        assert user is None
        
    @pytest.mark.asyncio
    async def test_change_password(self, db, test_user):
        """Test change password"""
        service = UserService(db)
        
        result = await service.change_password(
            test_user.id,
            "password123",
            "newpassword123"
        )
        
        assert result is True
        assert test_user.verify_password("newpassword123")
        
        # Test wrong current password
        result = await service.change_password(
            test_user.id,
            "wrongpassword",
            "anotherpassword"
        )
        assert result is False
        
    def test_search_users(self, db, test_user):
        """Test search users"""
        service = UserService(db)
        
        # Search by email
        results = service.search_users("test@")
        assert len(results) >= 1
        assert any(u.id == test_user.id for u in results)
        
        # Search by name
        results = service.search_users("Test")
        assert len(results) >= 1
        assert any(u.id == test_user.id for u in results)
        
        # No results
        results = service.search_users("nonexistent")
        assert len(results) == 0


class TestEmailService:
    """Test email service"""
    
    @pytest.mark.asyncio
    async def test_send_email(self, auth_config):
        """Test send email"""
        service = EmailService(auth_config)
        
        with patch.object(service, '_create_smtp_connection') as mock_smtp:
            mock_connection = Mock()
            mock_smtp.return_value = mock_connection
            
            result = await service.send_email(
                to_email="test@example.com",
                subject="Test Email",
                template_name="test",
                context={"name": "Test User"}
            )
            
            assert result is True
            mock_connection.send_message.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_send_verification_email(self, auth_config):
        """Test send verification email"""
        service = EmailService(auth_config)
        
        with patch.object(service, 'send_email') as mock_send:
            mock_send.return_value = True
            
            result = await service.send_verification_email(
                "test@example.com",
                "Test User"
            )
            
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args[1]
            assert call_args["to_email"] == "test@example.com"
            assert "verify_url" in call_args["context"]
            
    @pytest.mark.asyncio
    async def test_send_password_reset_email(self, auth_config):
        """Test send password reset email"""
        service = EmailService(auth_config)
        
        with patch.object(service, 'send_email') as mock_send:
            mock_send.return_value = True
            
            result = await service.send_password_reset_email(
                "test@example.com",
                "Test User"
            )
            
            assert result is True
            mock_send.assert_called_once()
            call_args = mock_send.call_args[1]
            assert "reset_url" in call_args["context"]


class TestPasskeyService:
    """Test passkey service"""
    
    @pytest.mark.asyncio
    async def test_begin_registration(self, db, auth_config, test_user):
        """Test begin passkey registration"""
        service = PasskeyService(db, auth_config)
        
        with patch('auth_kit_fastapi.services.passkey_service.generate_registration_options') as mock_generate:
            mock_options = Mock()
            mock_options.challenge = b'test-challenge'
            mock_generate.return_value = mock_options
            
            with patch('auth_kit_fastapi.services.passkey_service.options_to_json') as mock_to_json:
                mock_to_json.return_value = '{"challenge": "dGVzdC1jaGFsbGVuZ2U="}'
                
                options = await service.begin_registration(test_user, "My Device")
                
                assert "challenge" in options
                assert "_challenge" in options
                mock_generate.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_complete_registration(self, db, auth_config, test_user):
        """Test complete passkey registration"""
        service = PasskeyService(db, auth_config)
        
        with patch('auth_kit_fastapi.services.passkey_service.verify_registration_response') as mock_verify:
            mock_verification = Mock()
            mock_verification.verified = True
            mock_verification.credential_id = b'cred-id'
            mock_verification.credential_public_key = b'pub-key'
            mock_verification.sign_count = 0
            mock_verify.return_value = mock_verification
            
            registration_response = {
                "id": "cred-id",
                "rawId": "cred-id",
                "response": {
                    "attestationObject": "mock",
                    "clientDataJSON": "mock"
                },
                "type": "public-key",
                "authenticatorAttachment": "platform"
            }
            
            credential = await service.complete_registration(
                test_user,
                "My Device",
                registration_response,
                "dGVzdC1jaGFsbGVuZ2U="
            )
            
            assert credential.name == "My Device"
            assert credential.user_id == test_user.id
            assert credential.authenticator_type == "platform"
            
    def test_get_user_credentials(self, db, test_user):
        """Test get user credentials"""
        service = PasskeyService(db, Mock())
        
        # Add test credentials
        cred1 = UserCredential(
            user_id=test_user.id,
            credential_id="cred1",
            public_key="key1",
            sign_count=0,
            name="Device 1"
        )
        cred2 = UserCredential(
            user_id=test_user.id,
            credential_id="cred2",
            public_key="key2",
            sign_count=5,
            name="Device 2"
        )
        db.add_all([cred1, cred2])
        db.commit()
        
        credentials = service.get_user_credentials(test_user.id)
        assert len(credentials) == 2
        assert any(c.name == "Device 1" for c in credentials)
        assert any(c.name == "Device 2" for c in credentials)
        
    @pytest.mark.asyncio
    async def test_delete_credential(self, db, auth_config, test_user):
        """Test delete credential"""
        service = PasskeyService(db, auth_config)
        
        # Add credential
        credential = UserCredential(
            user_id=test_user.id,
            credential_id="cred1",
            public_key="key1",
            sign_count=0,
            name="Device"
        )
        db.add(credential)
        db.commit()
        
        # Delete it
        result = await service.delete_credential(credential.id, test_user.id)
        assert result is True
        
        # Verify deleted
        assert db.query(UserCredential).filter_by(id=credential.id).first() is None
        
    @pytest.mark.asyncio
    async def test_delete_last_auth_method_prevented(self, db, auth_config, test_user):
        """Test prevention of deleting last auth method"""
        service = PasskeyService(db, auth_config)
        
        # Remove password
        test_user.hashed_password = None
        db.commit()
        
        # Add single credential
        credential = UserCredential(
            user_id=test_user.id,
            credential_id="cred1",
            public_key="key1",
            sign_count=0,
            name="Only Device"
        )
        db.add(credential)
        db.commit()
        
        # Try to delete
        with pytest.raises(ValueError, match="last authentication method"):
            await service.delete_credential(credential.id, test_user.id)


class TestTwoFactorService:
    """Test two-factor service"""
    
    def test_get_2fa_status(self, db, auth_config, test_user_with_2fa):
        """Test get 2FA status"""
        service = TwoFactorService(db, auth_config)
        
        status = service.get_2fa_status(test_user_with_2fa)
        
        assert status["enabled"] is True
        assert status["method"] == "totp"
        assert status["backup_codes_remaining"] == 3
        
    def test_generate_qr_code(self, db, auth_config, test_user):
        """Test generate QR code"""
        service = TwoFactorService(db, auth_config)
        
        secret = service.generate_2fa_secret()
        qr_data, uri = service.generate_qr_code(test_user, secret)
        
        assert qr_data.startswith("data:image/png;base64,")
        assert test_user.email in uri
        assert auth_config.totp_issuer in uri
        
    def test_verify_totp_code(self, db, auth_config):
        """Test verify TOTP code"""
        service = TwoFactorService(db, auth_config)
        
        secret = "JBSWY3DPEHPK3PXP"
        totp = pyotp.TOTP(secret)
        
        # Valid code
        assert service.verify_totp_code(secret, totp.now()) is True
        
        # Invalid code
        assert service.verify_totp_code(secret, "000000") is False
        
    @pytest.mark.asyncio
    async def test_enable_2fa(self, db, auth_config, test_user):
        """Test enable 2FA"""
        service = TwoFactorService(db, auth_config)
        
        secret = service.generate_2fa_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        recovery_codes = await service.enable_2fa(test_user, secret, code)
        
        assert len(recovery_codes) == auth_config.recovery_codes_count
        assert test_user.two_factor_enabled is True
        assert test_user.two_factor_secret == secret
        
    @pytest.mark.asyncio
    async def test_disable_2fa(self, db, auth_config, test_user_with_2fa):
        """Test disable 2FA"""
        service = TwoFactorService(db, auth_config)
        
        result = await service.disable_2fa(test_user_with_2fa, "password123")
        
        assert result is True
        assert test_user_with_2fa.two_factor_enabled is False
        assert test_user_with_2fa.two_factor_secret is None
        
    def test_verify_2fa_code(self, db, auth_config, test_user_with_2fa):
        """Test verify 2FA code"""
        service = TwoFactorService(db, auth_config)
        
        # Test TOTP code
        totp = pyotp.TOTP(test_user_with_2fa.two_factor_secret)
        assert service.verify_2fa_code(test_user_with_2fa, totp.now()) is True
        
        # Test recovery code
        assert service.verify_2fa_code(
            test_user_with_2fa, 
            "AAAA-BBBB", 
            is_recovery_code=True
        ) is True
        
        # Verify recovery code marked as used
        db.refresh(test_user_with_2fa)
        codes = json.loads(test_user_with_2fa.two_factor_recovery_codes)
        assert any(c["used"] is True for c in codes)