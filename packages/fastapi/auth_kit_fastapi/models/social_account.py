"""
Social Account model for OAuth provider links
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID

from .user import Base


class SocialAccount(Base):
    """
    Stores linked OAuth provider accounts for users.

    Each user can have one account per provider (e.g., one Google, one GitHub).
    Provider tokens are stored encrypted using AES-256-GCM.
    """

    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Provider identification
    provider = Column(String(50), nullable=False)  # google, github, apple
    provider_user_id = Column(String(255), nullable=False)  # Provider's user ID

    # Provider profile info (optional, for display)
    provider_email = Column(String(255), nullable=True)
    provider_username = Column(String(255), nullable=True)

    # Encrypted tokens (format: v1:<base64(nonce || ciphertext)>)
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    id_token_enc = Column(Text, nullable=True)

    # Token metadata
    token_type = Column(String(50), nullable=True)  # Usually "Bearer"
    scope = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Token expiration

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Constraints
    __table_args__ = (
        # Each provider user can only be linked to one auth-kit user
        UniqueConstraint('provider', 'provider_user_id', name='uq_social_provider_user'),
        # Each user can only have one link per provider
        UniqueConstraint('user_id', 'provider', name='uq_social_user_provider'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization (excludes tokens)"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "provider": self.provider,
            "provider_email": self.provider_email,
            "provider_username": self.provider_username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def update_tokens(
        self,
        access_token_enc: str = None,
        refresh_token_enc: str = None,
        id_token_enc: str = None,
        token_type: str = None,
        scope: str = None,
        expires_at: datetime = None
    ) -> None:
        """Update encrypted tokens and metadata"""
        if access_token_enc is not None:
            self.access_token_enc = access_token_enc
        if refresh_token_enc is not None:
            self.refresh_token_enc = refresh_token_enc
        if id_token_enc is not None:
            self.id_token_enc = id_token_enc
        if token_type is not None:
            self.token_type = token_type
        if scope is not None:
            self.scope = scope
        if expires_at is not None:
            self.expires_at = expires_at
        self.updated_at = datetime.utcnow()
