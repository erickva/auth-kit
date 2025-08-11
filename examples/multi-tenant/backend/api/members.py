"""
Organization member management API endpoints
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
import secrets

from auth_kit_fastapi.core.database import get_db
from auth_kit_fastapi.core.dependencies import get_current_active_user
from auth_kit_fastapi.models import BaseUser

from ..models import Organization, OrganizationMember, OrganizationRole, OrganizationInvitation
from ..core.dependencies import get_current_organization, get_organization_member, require_admin
from ..core.audit import AuditLogger
from ..services import OrganizationService


router = APIRouter()


# Schemas
class MemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: OrganizationRole
    joined_at: str
    is_active: bool
    
    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    members: List[MemberResponse]
    total: int


class InvitationCreate(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER


class InvitationResponse(BaseModel):
    id: UUID
    email: str
    role: OrganizationRole
    invited_by: str
    created_at: str
    expires_at: str
    is_accepted: bool
    
    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    role: OrganizationRole


# Endpoints
@router.get("/{organization_id}/members", response_model=MemberListResponse)
async def list_members(
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(get_organization_member),
    db: Session = Depends(get_db)
):
    """List organization members"""
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.is_active == True
    ).all()
    
    # Join with user data
    member_responses = []
    for m in members:
        user = db.query(BaseUser).filter(BaseUser.id == m.user_id).first()
        if user:
            member_responses.append(MemberResponse(
                id=m.id,
                user_id=m.user_id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=m.role,
                joined_at=m.joined_at.isoformat(),
                is_active=m.is_active
            ))
    
    return MemberListResponse(
        members=member_responses,
        total=len(member_responses)
    )


@router.post("/{organization_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    invitation_data: InvitationCreate,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_admin),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Invite a new member to organization (admin only)"""
    
    # Check if feature is enabled
    if not request.app.state.auth_config.is_feature_enabled("organization_invitations"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization invitations are not enabled"
        )
    
    # Check if user is already a member
    existing_member = db.query(OrganizationMember).join(BaseUser).filter(
        BaseUser.email == invitation_data.email,
        OrganizationMember.organization_id == organization.id
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )
    
    # Check if invitation already exists
    existing_invitation = db.query(OrganizationInvitation).filter(
        OrganizationInvitation.email == invitation_data.email,
        OrganizationInvitation.organization_id == organization.id,
        OrganizationInvitation.accepted_at == None
    ).first()
    
    if existing_invitation and existing_invitation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active invitation already exists for this email"
        )
    
    # Check organization limits
    max_free_members = int(os.getenv("MAX_FREE_PLAN_MEMBERS", "5"))
    if not organization.can_add_member(max_free_members):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Free plan organizations are limited to {max_free_members} members"
        )
    
    # Create invitation
    invitation = OrganizationInvitation(
        organization_id=organization.id,
        email=invitation_data.email,
        role=invitation_data.role,
        token=secrets.token_urlsafe(32),
        invited_by_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=int(os.getenv("INVITATION_EXPIRY_DAYS", "7")))
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    # TODO: Send invitation email
    # In a real app, you would send an email with the invitation link
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_member_action(
            organization=organization,
            user=current_user,
            action="invited",
            member_id=invitation.id,
            details={"email": invitation_data.email, "role": invitation_data.role},
            request=request
        )
    
    return InvitationResponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        invited_by=current_user.email,
        created_at=invitation.created_at.isoformat(),
        expires_at=invitation.expires_at.isoformat(),
        is_accepted=False
    )


@router.put("/{organization_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    user_id: UUID,
    role_update: MemberRoleUpdate,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    current_member: OrganizationMember = Depends(require_admin),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update member role (admin only)"""
    
    # Get target member
    target_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.is_active == True
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Can't change owner role
    if target_member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role"
        )
    
    # Can't set someone as owner
    if role_update.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign owner role"
        )
    
    # Update role
    old_role = target_member.role
    target_member.role = role_update.role
    db.commit()
    db.refresh(target_member)
    
    # Get user details
    target_user = db.query(BaseUser).filter(BaseUser.id == user_id).first()
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_member_action(
            organization=organization,
            user=current_user,
            action="role_changed",
            member_id=target_member.id,
            details={"old_role": old_role, "new_role": role_update.role},
            request=request
        )
    
    return MemberResponse(
        id=target_member.id,
        user_id=target_member.user_id,
        email=target_user.email,
        first_name=target_user.first_name,
        last_name=target_user.last_name,
        role=target_member.role,
        joined_at=target_member.joined_at.isoformat(),
        is_active=target_member.is_active
    )


@router.delete("/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: UUID,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    current_member: OrganizationMember = Depends(require_admin),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove member from organization (admin only)"""
    
    # Get target member
    target_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.is_active == True
    ).first()
    
    if not target_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    # Can't remove owner
    if target_member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner"
        )
    
    # Can't remove self
    if target_member.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself. Use the leave endpoint instead."
        )
    
    # Soft delete member
    target_member.is_active = False
    db.commit()
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_member_action(
            organization=organization,
            user=current_user,
            action="removed",
            member_id=target_member.id,
            request=request
        )
    
    return None


@router.post("/{organization_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_organization(
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(get_organization_member),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Leave organization"""
    
    # Can't leave if owner
    if member.role == OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization owner cannot leave. Transfer ownership first."
        )
    
    # Soft delete membership
    member.is_active = False
    db.commit()
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_member_action(
            organization=organization,
            user=current_user,
            action="left",
            member_id=member.id,
            request=request
        )
    
    return None