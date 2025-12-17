"""
Tests for Social OAuth models (SocialAccount and has_usable_password)
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from auth_kit_fastapi.models import SocialAccount
# Import User from conftest (concrete implementation of BaseUser)
from tests.conftest import User


class TestHasUsablePassword:
    """Tests for has_usable_password field on User"""

    def test_default_has_usable_password_true(self, db):
        """Test that has_usable_password defaults to True for normal users"""
        user = User(
            email="normal@example.com",
            first_name="Normal",
            last_name="User",
            is_active=True,
            is_verified=True
        )
        user.set_password("password123")

        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.has_usable_password is True

    def test_social_user_has_usable_password_false(self, db):
        """Test that social-only users can have has_usable_password=False"""
        user = User(
            email="social@example.com",
            first_name="Social",
            last_name="User",
            is_active=True,
            is_verified=True,
            has_usable_password=False,
            hashed_password=""  # Empty hash for social-only users
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.has_usable_password is False

    def test_has_usable_password_in_to_dict(self, db):
        """Test that has_usable_password is included in to_dict()"""
        user = User(
            email="dict@example.com",
            is_active=True,
            has_usable_password=False,
            hashed_password=""
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        user_dict = user.to_dict()
        assert "has_usable_password" in user_dict
        assert user_dict["has_usable_password"] is False

    def test_query_by_has_usable_password(self, db):
        """Test querying users by has_usable_password"""
        # Create users with password
        user_with_password = User(
            email="with_password@example.com",
            is_active=True,
            has_usable_password=True,
            hashed_password="hashed"
        )

        # Create social-only user
        user_social_only = User(
            email="social_only@example.com",
            is_active=True,
            has_usable_password=False,
            hashed_password=""
        )

        db.add_all([user_with_password, user_social_only])
        db.commit()

        # Query users with password
        users_with_password = db.query(User).filter(
            User.has_usable_password == True
        ).all()
        assert any(u.email == "with_password@example.com" for u in users_with_password)

        # Query social-only users
        social_users = db.query(User).filter(
            User.has_usable_password == False
        ).all()
        assert any(u.email == "social_only@example.com" for u in social_users)


class TestSocialAccount:
    """Tests for SocialAccount model"""

    def test_create_social_account(self, db, test_user):
        """Test creating a social account"""
        social_account = SocialAccount(
            user_id=test_user.id,
            provider="google",
            provider_user_id="google-123456",
            provider_email="test@gmail.com",
            provider_username="Test User"
        )

        db.add(social_account)
        db.commit()
        db.refresh(social_account)

        assert social_account.id is not None
        assert social_account.user_id == test_user.id
        assert social_account.provider == "google"
        assert social_account.provider_user_id == "google-123456"
        assert social_account.created_at is not None
        assert social_account.updated_at is not None

    def test_social_account_encrypted_tokens(self, db, test_user):
        """Test storing encrypted tokens in social account"""
        social_account = SocialAccount(
            user_id=test_user.id,
            provider="github",
            provider_user_id="github-789",
            access_token_enc="v1:base64encryptedtoken",
            refresh_token_enc="v1:base64encryptedrefresh",
            id_token_enc="v1:base64encryptedidtoken",
            token_type="Bearer",
            scope="user:email read:user",
            expires_at=datetime.utcnow()
        )

        db.add(social_account)
        db.commit()
        db.refresh(social_account)

        assert social_account.access_token_enc == "v1:base64encryptedtoken"
        assert social_account.refresh_token_enc == "v1:base64encryptedrefresh"
        assert social_account.id_token_enc == "v1:base64encryptedidtoken"
        assert social_account.token_type == "Bearer"
        assert social_account.scope == "user:email read:user"

    def test_unique_constraint_provider_user(self, db, test_user):
        """Test unique constraint on (provider, provider_user_id)"""
        # Create first social account
        social1 = SocialAccount(
            user_id=test_user.id,
            provider="google",
            provider_user_id="unique-google-id"
        )
        db.add(social1)
        db.commit()

        # Create another user
        user2 = User(
            email="user2@example.com",
            is_active=True,
            hashed_password="hash"
        )
        db.add(user2)
        db.commit()

        # Try to link same provider identity to different user
        social2 = SocialAccount(
            user_id=user2.id,
            provider="google",
            provider_user_id="unique-google-id"  # Same as social1
        )
        db.add(social2)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

    def test_unique_constraint_user_provider(self, db, test_user):
        """Test unique constraint on (user_id, provider)"""
        # Create first social account
        social1 = SocialAccount(
            user_id=test_user.id,
            provider="github",
            provider_user_id="github-1"
        )
        db.add(social1)
        db.commit()

        # Try to add another github account for same user
        social2 = SocialAccount(
            user_id=test_user.id,
            provider="github",  # Same provider
            provider_user_id="github-2"  # Different provider user
        )
        db.add(social2)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

    def test_multiple_providers_per_user(self, db, test_user):
        """Test that a user can have multiple different providers"""
        google_account = SocialAccount(
            user_id=test_user.id,
            provider="google",
            provider_user_id="google-123"
        )
        github_account = SocialAccount(
            user_id=test_user.id,
            provider="github",
            provider_user_id="github-456"
        )
        apple_account = SocialAccount(
            user_id=test_user.id,
            provider="apple",
            provider_user_id="apple-789"
        )

        db.add_all([google_account, github_account, apple_account])
        db.commit()

        # Query user's social accounts
        user_accounts = db.query(SocialAccount).filter(
            SocialAccount.user_id == test_user.id
        ).all()

        assert len(user_accounts) == 3
        providers = {a.provider for a in user_accounts}
        assert providers == {"google", "github", "apple"}

    def test_social_account_to_dict(self, db, test_user):
        """Test to_dict excludes sensitive token data"""
        social_account = SocialAccount(
            user_id=test_user.id,
            provider="google",
            provider_user_id="google-123",
            provider_email="test@gmail.com",
            access_token_enc="v1:secret_token"
        )

        db.add(social_account)
        db.commit()
        db.refresh(social_account)

        result = social_account.to_dict()

        # Should include safe fields
        assert "id" in result
        assert "provider" in result
        assert "provider_email" in result
        assert "created_at" in result

        # Should NOT include encrypted tokens
        assert "access_token_enc" not in result
        assert "refresh_token_enc" not in result
        assert "id_token_enc" not in result

    def test_update_tokens_method(self, db, test_user):
        """Test update_tokens helper method"""
        social_account = SocialAccount(
            user_id=test_user.id,
            provider="google",
            provider_user_id="google-123"
        )
        db.add(social_account)
        db.commit()

        original_updated_at = social_account.updated_at

        # Update tokens
        new_expires = datetime.utcnow()
        social_account.update_tokens(
            access_token_enc="v1:new_access",
            refresh_token_enc="v1:new_refresh",
            token_type="Bearer",
            scope="email profile",
            expires_at=new_expires
        )
        db.commit()
        db.refresh(social_account)

        assert social_account.access_token_enc == "v1:new_access"
        assert social_account.refresh_token_enc == "v1:new_refresh"
        assert social_account.token_type == "Bearer"
        assert social_account.scope == "email profile"

    def test_cascade_delete_with_user(self, db):
        """Test that social accounts are deleted when user is deleted"""
        # Create user with social account
        user = User(
            email="cascade@example.com",
            is_active=True,
            hashed_password="hash"
        )
        db.add(user)
        db.commit()

        social = SocialAccount(
            user_id=user.id,
            provider="google",
            provider_user_id="google-cascade"
        )
        db.add(social)
        db.commit()

        social_id = social.id

        # Delete user
        db.delete(user)
        db.commit()

        # Social account should be gone
        remaining = db.query(SocialAccount).filter(
            SocialAccount.id == social_id
        ).first()
        assert remaining is None

    def test_foreign_key_constraint(self, db):
        """Test that foreign key to users table is enforced"""
        fake_user_id = uuid4()

        social = SocialAccount(
            user_id=fake_user_id,  # Non-existent user
            provider="google",
            provider_user_id="google-fake"
        )
        db.add(social)

        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()
