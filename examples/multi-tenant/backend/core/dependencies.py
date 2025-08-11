"""
Dependencies for multi-tenant operations
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from auth_kit_fastapi.core.database import get_db
from auth_kit_fastapi.core.dependencies import get_current_active_user
from auth_kit_fastapi.models import BaseUser

from ..models import Organization, OrganizationMember


async def get_current_organization_id(request: Request) -> Optional[UUID]:
    """
    Get current organization ID from header or session
    
    Organizations can be specified via:
    1. X-Organization-ID header
    2. Session/cookie (for web apps)
    3. User's default organization
    """
    # Check header first
    org_id = request.headers.get("X-Organization-ID")
    if org_id:
        try:
            return UUID(org_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID format"
            )
    
    # Check session/cookie
    if hasattr(request, "session") and "organization_id" in request.session:
        return UUID(request.session["organization_id"])
    
    return None


async def get_current_organization(
    organization_id: Optional[UUID] = Depends(get_current_organization_id),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Organization:
    """Get current organization with membership validation"""
    
    if not organization_id:
        # Try to get user's first organization
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True
        ).first()
        
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No organization selected and user has no organizations"
            )
        
        organization_id = membership.organization_id
    
    # Get organization
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.is_active == True
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check membership
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    # Attach membership to organization for easy access
    organization._current_membership = membership
    
    return organization


async def get_organization_member(
    organization: Organization = Depends(get_current_organization),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> OrganizationMember:
    """Get current user's membership in the organization"""
    
    if hasattr(organization, "_current_membership"):
        return organization._current_membership
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    return membership


def require_organization_role(allowed_roles: list[str]):
    """Dependency to require specific organization roles"""
    
    async def role_checker(
        member: OrganizationMember = Depends(get_organization_member)
    ):
        if member.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )
        return member
    
    return role_checker


# Convenience dependencies for common role requirements
require_owner = require_organization_role(["owner"])
require_admin = require_organization_role(["owner", "admin"])
require_member = require_organization_role(["owner", "admin", "member"])
require_any_role = require_organization_role(["owner", "admin", "member", "viewer"])