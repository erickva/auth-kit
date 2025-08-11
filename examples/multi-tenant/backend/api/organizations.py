"""
Organization API endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from slugify import slugify

from auth_kit_fastapi.core.database import get_db
from auth_kit_fastapi.core.dependencies import get_current_active_user
from auth_kit_fastapi.models import BaseUser

from ..models import Organization, OrganizationMember, OrganizationRole, OrganizationPlan
from ..core.dependencies import get_current_organization, require_admin
from ..core.audit import AuditLogger
from ..services import OrganizationService


router = APIRouter()


# Schemas
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    logo_url: Optional[str]
    website: Optional[str]
    plan: OrganizationPlan
    member_count: int
    created_at: str
    
    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int


# Endpoints
@router.get("/", response_model=OrganizationListResponse)
async def list_organizations(
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's organizations"""
    service = OrganizationService(db)
    organizations = service.get_user_organizations(current_user.id)
    
    return OrganizationListResponse(
        organizations=[
            OrganizationResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                description=org.description,
                logo_url=org.logo_url,
                website=org.website,
                plan=org.plan,
                member_count=org.member_count,
                created_at=org.created_at.isoformat()
            )
            for org in organizations
        ],
        total=len(organizations)
    )


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    request: Request,
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    service = OrganizationService(db)
    
    # Generate slug if not provided
    slug = org_data.slug or slugify(org_data.name)
    
    # Check if slug exists
    if service.get_organization_by_slug(slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{slug}' already exists"
        )
    
    # Create organization
    organization = await service.create_organization(
        name=org_data.name,
        slug=slug,
        description=org_data.description,
        website=org_data.website,
        owner_id=current_user.id
    )
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_organization_action(
            organization=organization,
            user=current_user,
            action="created",
            request=request
        )
    
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        website=organization.website,
        plan=organization.plan,
        member_count=1,
        created_at=organization.created_at.isoformat()
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization: Organization = Depends(get_current_organization)
):
    """Get organization details"""
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        logo_url=organization.logo_url,
        website=organization.website,
        plan=organization.plan,
        member_count=organization.member_count,
        created_at=organization.created_at.isoformat()
    )


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    org_update: OrganizationUpdate,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_admin),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update organization (admin only)"""
    service = OrganizationService(db)
    
    # Update organization
    updated_org = await service.update_organization(
        organization_id=organization.id,
        **org_update.dict(exclude_unset=True)
    )
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_organization_action(
            organization=updated_org,
            user=current_user,
            action="updated",
            details=org_update.dict(exclude_unset=True),
            request=request
        )
    
    return OrganizationResponse(
        id=updated_org.id,
        name=updated_org.name,
        slug=updated_org.slug,
        description=updated_org.description,
        logo_url=updated_org.logo_url,
        website=updated_org.website,
        plan=updated_org.plan,
        member_count=updated_org.member_count,
        created_at=updated_org.created_at.isoformat()
    )


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_admin),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete organization (owner only)"""
    # Only owner can delete
    if member.role != OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can delete it"
        )
    
    # Log audit event before deletion
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_organization_action(
            organization=organization,
            user=current_user,
            action="deleted",
            request=request
        )
    
    # Delete organization (cascades to all related data)
    service = OrganizationService(db)
    await service.delete_organization(organization.id)
    
    return None