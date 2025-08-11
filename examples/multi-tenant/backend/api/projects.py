"""
Project API endpoints - Example of organization-scoped resource
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from auth_kit_fastapi.core.database import get_db
from auth_kit_fastapi.core.dependencies import get_current_active_user
from auth_kit_fastapi.models import BaseUser

from ..models import Project, Organization, OrganizationMember
from ..core.dependencies import get_current_organization, get_organization_member, require_member
from ..core.audit import AuditLogger


router = APIRouter()


# Schemas
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=1, max_length=50, regex="^[A-Z][A-Z0-9]*$")
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(active|archived|closed)$")


class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    key: str
    description: Optional[str]
    status: str
    created_by_id: UUID
    created_at: str
    updated_at: str
    is_archived: bool
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int


# Endpoints
@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    organization_id: Optional[UUID] = Query(None, description="Filter by organization"),
    status: Optional[str] = Query(None, regex="^(active|archived|closed)$"),
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(get_organization_member),
    db: Session = Depends(get_db)
):
    """List projects in organization"""
    # Use provided org ID or current org
    filter_org_id = organization_id or organization.id
    
    # Build query
    query = db.query(Project).filter(
        Project.organization_id == filter_org_id
    )
    
    if status:
        query = query.filter(Project.status == status)
    
    if not member.is_admin:
        # Non-admins can't see archived projects
        query = query.filter(Project.is_archived == False)
    
    projects = query.order_by(Project.created_at.desc()).all()
    
    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=p.id,
                organization_id=p.organization_id,
                name=p.name,
                key=p.key,
                description=p.description,
                status=p.status,
                created_by_id=p.created_by_id,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
                is_archived=p.is_archived
            )
            for p in projects
        ],
        total=len(projects)
    )


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_member),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new project (member and above)"""
    
    # Check if project key already exists in org
    existing = db.query(Project).filter(
        Project.organization_id == organization.id,
        Project.key == project_data.key
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with key '{project_data.key}' already exists in this organization"
        )
    
    # Create project
    project = Project(
        organization_id=organization.id,
        name=project_data.name,
        key=project_data.key,
        description=project_data.description,
        created_by_id=current_user.id
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_project_action(
            organization=organization,
            user=current_user,
            action="created",
            project_id=project.id,
            details={"name": project.name, "key": project.key},
            request=request
        )
    
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        key=project.key,
        description=project.description,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        is_archived=project.is_archived
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(get_organization_member),
    db: Session = Depends(get_db)
):
    """Get project details"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.organization_id == organization.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if non-admin can access archived project
    if project.is_archived and not member.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view archived projects"
        )
    
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        key=project.key,
        description=project.description,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        is_archived=project.is_archived
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_member),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update project (member and above)"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.organization_id == organization.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update fields
    update_data = project_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    # Update timestamp
    from datetime import datetime
    project.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(project)
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_project_action(
            organization=organization,
            user=current_user,
            action="updated",
            project_id=project.id,
            details=update_data,
            request=request
        )
    
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        key=project.key,
        description=project.description,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        is_archived=project.is_archived
    )


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: UUID,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    member: OrganizationMember = Depends(require_member),
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Archive project (member and above)"""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.organization_id == organization.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is already archived"
        )
    
    # Archive project
    project.is_archived = True
    project.status = "archived"
    
    from datetime import datetime
    project.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(project)
    
    # Log audit event
    if request.app.state.auth_config.is_feature_enabled("audit_logs"):
        audit = AuditLogger(db)
        await audit.log_project_action(
            organization=organization,
            user=current_user,
            action="archived",
            project_id=project.id,
            request=request
        )
    
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        key=project.key,
        description=project.description,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at.isoformat(),
        updated_at=project.updated_at.isoformat(),
        is_archived=project.is_archived
    )