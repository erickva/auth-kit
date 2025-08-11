"""
Project model - example of organization-scoped resource
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from auth_kit_fastapi.models import Base


class Project(Base):
    """Project model - belongs to organization"""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Project-specific fields
    key = Column(String(50), nullable=False)  # Unique within organization
    status = Column(String(50), default="active", nullable=False)
    
    # Metadata
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="projects")
    created_by = relationship("BaseUser")
    
    # Indexes
    __table_args__ = (
        Index("idx_project_org", "organization_id"),
        Index("idx_project_key", "organization_id", "key", unique=True),
        Index("idx_project_status", "status"),
        Index("idx_project_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<Project {self.name} ({self.key})>"