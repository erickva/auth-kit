"""
Organization models for multi-tenancy
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Boolean, Enum, ForeignKey, 
    UniqueConstraint, Index, Integer, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from auth_kit_fastapi.models import Base, BaseUser


class OrganizationPlan(str, PyEnum):
    """Organization subscription plans"""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OrganizationRole(str, PyEnum):
    """Organization member roles"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    logo_url = Column(String(500))
    website = Column(String(500))
    
    # Subscription
    plan = Column(
        Enum(OrganizationPlan), 
        default=OrganizationPlan.FREE, 
        nullable=False
    )
    plan_expires_at = Column(DateTime(timezone=True))
    
    # Settings
    settings = Column(Text, default="{}")  # JSON field for flexible settings
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_organization_slug", "slug"),
        Index("idx_organization_plan", "plan"),
        Index("idx_organization_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<Organization {self.name} ({self.slug})>"
    
    @property
    def member_count(self) -> int:
        """Get active member count"""
        return len([m for m in self.members if m.is_active])
    
    @property
    def is_on_free_plan(self) -> bool:
        """Check if organization is on free plan"""
        return self.plan == OrganizationPlan.FREE
    
    def can_add_member(self, max_free_members: int = 5) -> bool:
        """Check if organization can add more members"""
        if self.plan != OrganizationPlan.FREE:
            return True
        return self.member_count < max_free_members


class OrganizationMember(Base):
    """Organization membership model"""
    __tablename__ = "organization_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(
        Enum(OrganizationRole), 
        default=OrganizationRole.MEMBER, 
        nullable=False
    )
    
    # Metadata
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("BaseUser", foreign_keys=[user_id], backref="organization_memberships")
    invited_by = relationship("BaseUser", foreign_keys=[invited_by_id])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
        Index("idx_member_org", "organization_id"),
        Index("idx_member_user", "user_id"),
        Index("idx_member_role", "role"),
    )
    
    def __repr__(self):
        return f"<OrganizationMember {self.user_id} in {self.organization_id} as {self.role}>"
    
    @property
    def is_owner(self) -> bool:
        """Check if member is owner"""
        return self.role == OrganizationRole.OWNER
    
    @property
    def is_admin(self) -> bool:
        """Check if member is admin or higher"""
        return self.role in [OrganizationRole.OWNER, OrganizationRole.ADMIN]
    
    @property
    def can_manage_members(self) -> bool:
        """Check if member can manage other members"""
        return self.is_admin
    
    @property
    def can_edit_organization(self) -> bool:
        """Check if member can edit organization settings"""
        return self.is_admin
    
    def can_access_resource(self, resource_type: str) -> bool:
        """Check if member can access resource type"""
        if self.role == OrganizationRole.VIEWER:
            return resource_type in ["read", "list"]
        return True


class OrganizationInvitation(Base):
    """Organization invitation model"""
    __tablename__ = "organization_invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(
        Enum(OrganizationRole), 
        default=OrganizationRole.MEMBER, 
        nullable=False
    )
    token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Metadata
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True))
    
    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    invited_by = relationship("BaseUser")
    
    # Indexes
    __table_args__ = (
        Index("idx_invitation_token", "token"),
        Index("idx_invitation_email", "email"),
        Index("idx_invitation_org", "organization_id"),
    )
    
    def __repr__(self):
        return f"<OrganizationInvitation {self.email} to {self.organization_id}>"
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_accepted(self) -> bool:
        """Check if invitation is accepted"""
        return self.accepted_at is not None
    
    @property
    def is_valid(self) -> bool:
        """Check if invitation is valid"""
        return not self.is_expired and not self.is_accepted