"""
User service for authentication operations
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..models.user import BaseUser, UserSession
from ..core.security import get_password_hash, verify_password
from ..core.events import auth_events
from ..schemas.auth import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user-related operations
    
    Handles user CRUD operations, authentication, and session management
    """
    
    def __init__(self, db: Session, user_model=None):
        """
        Initialize user service
        
        Args:
            db: Database session
            user_model: Concrete User model class
        """
        self.db = db
        self.user_model = user_model or BaseUser
        
    async def create_user(
        self,
        user_data: UserCreate,
        is_verified: bool = False,
        is_active: bool = True
    ) -> BaseUser:
        """
        Create a new user
        
        Args:
            user_data: User creation data
            is_verified: Whether user email is pre-verified
            is_active: Whether user is active
            
        Returns:
            Created user
            
        Raises:
            ValueError: If email already exists
        """
        # Check if user exists
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create new user
        user = self.user_model(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone_number=user_data.phone_number,
            is_verified=is_verified,
            is_active=is_active
        )
        
        # Set password if provided
        if user_data.password:
            user.set_password(user_data.password)
        
        # Save to database
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Emit event
        await auth_events.emit("user_registered", {"user_id": str(user.id)})
        
        return user
        
    def get_user(self, user_id: UUID) -> Optional[BaseUser]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User or None
        """
        return self.db.query(self.user_model).filter(
            BaseUser.id == user_id
        ).first()
        
    def get_user_by_email(self, email: str) -> Optional[BaseUser]:
        """
        Get user by email
        
        Args:
            email: User email
            
        Returns:
            User or None
        """
        return self.db.query(self.user_model).filter(
            BaseUser.email == email
        ).first()
        
    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate
    ) -> Optional[BaseUser]:
        """
        Update user information
        
        Args:
            user_id: User ID
            user_data: Update data
            
        Returns:
            Updated user or None
        """
        user = self.get_user(user_id)
        if not user:
            return None
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(user)
        
        # Emit event
        await auth_events.emit("user_updated", {"user_id": str(user.id)})
        
        return user
        
    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user (soft delete)
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        user = self.get_user(user_id)
        if not user:
            return False
        
        # Soft delete
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        # Delete all sessions
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).delete()
        
        self.db.commit()
        
        # Emit event
        await auth_events.emit("user_deleted", {"user_id": str(user_id)})
        
        return True
        
    def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[BaseUser]:
        """
        Authenticate user with email and password
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Authenticated user or None
        """
        user = self.get_user_by_email(email)
        if not user:
            return None
            
        if not user.verify_password(password):
            return None
            
        if not user.is_active:
            return None
            
        return user
        
    def get_user_sessions(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[UserSession]:
        """
        Get user sessions
        
        Args:
            user_id: User ID
            active_only: Only return active sessions
            
        Returns:
            List of user sessions
        """
        query = self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        )
        
        if active_only:
            query = query.filter(
                UserSession.expires_at > datetime.utcnow()
            )
            
        return query.all()
        
    def create_session(
        self,
        user_id: UUID,
        refresh_token_jti: str,
        expires_at: datetime,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """
        Create user session
        
        Args:
            user_id: User ID
            refresh_token_jti: Refresh token JTI
            expires_at: Session expiration
            device_id: Device identifier
            ip_address: IP address
            user_agent: User agent string
            
        Returns:
            Created session
        """
        session = UserSession(
            user_id=user_id,
            refresh_token_jti=refresh_token_jti,
            expires_at=expires_at,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
        
    def get_session_by_jti(
        self,
        jti: str
    ) -> Optional[UserSession]:
        """
        Get session by refresh token JTI
        
        Args:
            jti: Refresh token JTI
            
        Returns:
            Session or None
        """
        return self.db.query(UserSession).filter(
            UserSession.refresh_token_jti == jti
        ).first()
        
    def revoke_session(self, jti: str) -> bool:
        """
        Revoke session by JTI
        
        Args:
            jti: Refresh token JTI
            
        Returns:
            True if revoked, False if not found
        """
        session = self.get_session_by_jti(jti)
        if not session:
            return False
            
        self.db.delete(session)
        self.db.commit()
        
        return True
        
    def revoke_all_sessions(self, user_id: UUID) -> int:
        """
        Revoke all user sessions
        
        Args:
            user_id: User ID
            
        Returns:
            Number of sessions revoked
        """
        count = self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).delete()
        
        self.db.commit()
        
        return count
        
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        count = self.db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).delete()
        
        self.db.commit()
        
        logger.info(f"Cleaned up {count} expired sessions")
        
        return count
        
    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str,
        revoke_sessions: bool = True
    ) -> bool:
        """
        Change user password
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            revoke_sessions: Whether to revoke all sessions
            
        Returns:
            True if changed, False if current password incorrect
        """
        user = self.get_user(user_id)
        if not user:
            return False
            
        # Verify current password
        if not user.verify_password(current_password):
            return False
            
        # Set new password
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Revoke sessions if requested
        if revoke_sessions:
            self.revoke_all_sessions(user_id)
            
        self.db.commit()
        
        # Emit event
        await auth_events.emit("password_changed", {"user_id": str(user_id)})
        
        return True
        
    def search_users(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[BaseUser]:
        """
        Search users by email or name
        
        Args:
            query: Search query
            limit: Maximum results
            offset: Result offset
            
        Returns:
            List of matching users
        """
        search_term = f"%{query}%"
        
        return self.db.query(self.user_model).filter(
            or_(
                BaseUser.email.ilike(search_term),
                BaseUser.first_name.ilike(search_term),
                BaseUser.last_name.ilike(search_term)
            )
        ).limit(limit).offset(offset).all()