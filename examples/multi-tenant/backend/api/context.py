"""
Context API endpoints for current user and organization
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from auth_kit_fastapi.core.database import get_db
from auth_kit_fastapi.core.dependencies import get_current_active_user
from auth_kit_fastapi.models import BaseUser

from ..models import Organization, OrganizationMember, OrganizationRole
from ..core.dependencies import get_current_organization_id


router = APIRouter()


# Schemas
class UserOrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    role: OrganizationRole
    is_current: bool
    
    class Config:
        from_attributes = True


class UserContextResponse(BaseModel):
    user: dict
    current_organization: Optional[UserOrganizationResponse]
    organizations: List[UserOrganizationResponse]


class SwitchOrganizationRequest(BaseModel):
    organization_id: UUID


# Endpoints
@router.get("/me", response_model=UserContextResponse)
async def get_user_context(
    request: Request,
    current_user: BaseUser = Depends(get_current_active_user),
    current_org_id: Optional[UUID] = Depends(get_current_organization_id),
    db: Session = Depends(get_db)
):
    """Get current user context with organizations"""
    
    # Get user's organizations
    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.is_active == True
    ).all()
    
    organizations = []
    current_organization = None
    
    for membership in memberships:
        org = db.query(Organization).filter(
            Organization.id == membership.organization_id,
            Organization.is_active == True
        ).first()
        
        if org:
            org_response = UserOrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                role=membership.role,
                is_current=org.id == current_org_id
            )
            organizations.append(org_response)
            
            if org.id == current_org_id:
                current_organization = org_response
    
    # If no current org but user has orgs, use the first one
    if not current_organization and organizations:
        organizations[0].is_current = True
        current_organization = organizations[0]
    
    return UserContextResponse(
        user={
            "id": str(current_user.id),
            "email": current_user.email,
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "isVerified": current_user.is_verified,
            "twoFactorEnabled": current_user.two_factor_enabled
        },
        current_organization=current_organization,
        organizations=organizations
    )


@router.post("/switch-organization")
async def switch_organization(
    switch_data: SwitchOrganizationRequest,
    request: Request,
    response: Response,
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Switch current organization"""
    
    # Verify user is member of target organization
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == switch_data.organization_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.is_active == True
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    # Verify organization is active
    organization = db.query(Organization).filter(
        Organization.id == switch_data.organization_id,
        Organization.is_active == True
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    # Set organization in session/cookie
    if hasattr(request, "session"):
        request.session["organization_id"] = str(switch_data.organization_id)
    
    # Also set in response header for API clients
    response.headers["X-Organization-ID"] = str(switch_data.organization_id)
    
    return {
        "message": "Organization switched successfully",
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
            "role": membership.role
        }
    }


@router.post("/accept-invitation/{token}")
async def accept_invitation(
    token: str,
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Accept organization invitation"""
    from ..models import OrganizationInvitation
    
    # Find invitation
    invitation = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.token == token
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    # Check if expired
    if invitation.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Check if already accepted
    if invitation.is_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted"
        )
    
    # Check if email matches (optional - you might want to allow any logged-in user)
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is for a different email address"
        )
    
    # Check if already a member
    existing_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == invitation.organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of this organization"
            )
        else:
            # Reactivate membership
            existing_member.is_active = True
            existing_member.role = invitation.role
            db.commit()
    else:
        # Create membership
        membership = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=current_user.id,
            role=invitation.role,
            invited_by_id=invitation.invited_by_id
        )
        db.add(membership)
    
    # Mark invitation as accepted
    from datetime import datetime
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    
    # Get organization details
    organization = db.query(Organization).filter(
        Organization.id == invitation.organization_id
    ).first()
    
    return {
        "message": "Successfully joined organization",
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
            "role": invitation.role
        }
    }