"""
Audit log model for tracking organization actions
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from auth_kit_fastapi.models import Base


class AuditLog(Base):
    """Audit log for organization actions"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "member.invited", "project.created"
    resource_type = Column(String(50))  # e.g., "member", "project", "organization"
    resource_id = Column(UUID(as_uuid=True))
    
    # Additional data
    details = Column(JSONB, default={})  # Flexible JSON field for action-specific data
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("BaseUser")
    
    # Indexes
    __table_args__ = (
        Index("idx_audit_org", "organization_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id} at {self.created_at}>"