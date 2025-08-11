"""
Audit logging functionality
"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import Request

from auth_kit_fastapi.models import BaseUser
from ..models import AuditLog, Organization


class AuditLogger:
    """Service for logging audit events"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def log(
        self,
        organization: Organization,
        user: Optional[BaseUser],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> AuditLog:
        """
        Log an audit event
        
        Args:
            organization: Organization context
            user: User who performed the action (optional for system actions)
            action: Action identifier (e.g., "member.invited", "project.created")
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional action-specific details
            request: HTTP request for IP/user agent logging
        """
        audit_log = AuditLog(
            organization_id=organization.id,
            user_id=user.id if user else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            created_at=datetime.utcnow()
        )
        
        # Add request metadata if available
        if request:
            audit_log.ip_address = request.client.host if request.client else None
            audit_log.user_agent = request.headers.get("User-Agent")
        
        self.db.add(audit_log)
        self.db.commit()
        
        return audit_log
    
    async def log_organization_action(
        self,
        organization: Organization,
        user: BaseUser,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log organization-level action"""
        return await self.log(
            organization=organization,
            user=user,
            action=f"organization.{action}",
            resource_type="organization",
            resource_id=organization.id,
            details=details,
            request=request
        )
    
    async def log_member_action(
        self,
        organization: Organization,
        user: BaseUser,
        action: str,
        member_id: UUID,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log member-related action"""
        return await self.log(
            organization=organization,
            user=user,
            action=f"member.{action}",
            resource_type="member",
            resource_id=member_id,
            details=details,
            request=request
        )
    
    async def log_project_action(
        self,
        organization: Organization,
        user: BaseUser,
        action: str,
        project_id: UUID,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log project-related action"""
        return await self.log(
            organization=organization,
            user=user,
            action=f"project.{action}",
            resource_type="project",
            resource_id=project_id,
            details=details,
            request=request
        )


# Common audit actions
AUDIT_ACTIONS = {
    # Organization actions
    "organization.created": "Organization created",
    "organization.updated": "Organization settings updated",
    "organization.deleted": "Organization deleted",
    "organization.plan_changed": "Organization plan changed",
    
    # Member actions
    "member.invited": "Member invited",
    "member.joined": "Member joined",
    "member.role_changed": "Member role changed",
    "member.removed": "Member removed",
    "member.left": "Member left organization",
    
    # Project actions
    "project.created": "Project created",
    "project.updated": "Project updated",
    "project.archived": "Project archived",
    "project.deleted": "Project deleted",
    
    # Security actions
    "security.login": "User logged in",
    "security.logout": "User logged out",
    "security.password_changed": "Password changed",
    "security.2fa_enabled": "2FA enabled",
    "security.2fa_disabled": "2FA disabled",
}