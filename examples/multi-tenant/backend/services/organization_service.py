"""
Organization service for business logic
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import Organization, OrganizationMember, OrganizationRole, OrganizationPlan


class OrganizationService:
    """Service for organization operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_organization(
        self,
        name: str,
        owner_id: UUID,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        website: Optional[str] = None,
        plan: OrganizationPlan = OrganizationPlan.FREE
    ) -> Organization:
        """
        Create a new organization with owner
        
        Args:
            name: Organization name
            owner_id: User ID who will be the owner
            slug: URL-friendly identifier
            description: Organization description
            website: Organization website
            plan: Subscription plan
            
        Returns:
            Created organization
        """
        # Create organization
        organization = Organization(
            name=name,
            slug=slug or self._generate_slug(name),
            description=description,
            website=website,
            plan=plan
        )
        
        self.db.add(organization)
        self.db.flush()  # Get ID without committing
        
        # Add owner as member
        owner_member = OrganizationMember(
            organization_id=organization.id,
            user_id=owner_id,
            role=OrganizationRole.OWNER
        )
        
        self.db.add(owner_member)
        self.db.commit()
        self.db.refresh(organization)
        
        return organization
    
    def get_organization(self, organization_id: UUID) -> Optional[Organization]:
        """Get organization by ID"""
        return self.db.query(Organization).filter(
            Organization.id == organization_id,
            Organization.is_active == True
        ).first()
    
    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug"""
        return self.db.query(Organization).filter(
            Organization.slug == slug,
            Organization.is_active == True
        ).first()
    
    def get_user_organizations(self, user_id: UUID) -> List[Organization]:
        """Get all organizations for a user"""
        memberships = self.db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        ).all()
        
        org_ids = [m.organization_id for m in memberships]
        
        organizations = self.db.query(Organization).filter(
            Organization.id.in_(org_ids),
            Organization.is_active == True
        ).all()
        
        return organizations
    
    async def update_organization(
        self,
        organization_id: UUID,
        **kwargs
    ) -> Optional[Organization]:
        """Update organization details"""
        organization = self.get_organization(organization_id)
        if not organization:
            return None
        
        # Update fields
        for field, value in kwargs.items():
            if hasattr(organization, field) and value is not None:
                setattr(organization, field, value)
        
        organization.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(organization)
        
        return organization
    
    async def delete_organization(self, organization_id: UUID) -> bool:
        """
        Delete organization (soft delete)
        
        This will cascade to all related data
        """
        organization = self.get_organization(organization_id)
        if not organization:
            return False
        
        # Soft delete
        organization.is_active = False
        organization.updated_at = datetime.utcnow()
        
        # Also deactivate all memberships
        self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id
        ).update({"is_active": False})
        
        self.db.commit()
        
        return True
    
    def add_member(
        self,
        organization_id: UUID,
        user_id: UUID,
        role: OrganizationRole = OrganizationRole.MEMBER,
        invited_by_id: Optional[UUID] = None
    ) -> OrganizationMember:
        """Add a member to organization"""
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            invited_by_id=invited_by_id
        )
        
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        
        return member
    
    def update_member_role(
        self,
        organization_id: UUID,
        user_id: UUID,
        new_role: OrganizationRole
    ) -> Optional[OrganizationMember]:
        """Update member's role"""
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        ).first()
        
        if not member:
            return None
        
        member.role = new_role
        self.db.commit()
        self.db.refresh(member)
        
        return member
    
    def remove_member(
        self,
        organization_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove member from organization (soft delete)"""
        member = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.is_active == True
        ).first()
        
        if not member:
            return False
        
        member.is_active = False
        self.db.commit()
        
        return True
    
    def transfer_ownership(
        self,
        organization_id: UUID,
        current_owner_id: UUID,
        new_owner_id: UUID
    ) -> bool:
        """Transfer organization ownership"""
        # Get current owner
        current_owner = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_owner_id,
            OrganizationMember.role == OrganizationRole.OWNER,
            OrganizationMember.is_active == True
        ).first()
        
        if not current_owner:
            return False
        
        # Get new owner
        new_owner = self.db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == new_owner_id,
            OrganizationMember.is_active == True
        ).first()
        
        if not new_owner:
            return False
        
        # Transfer ownership
        current_owner.role = OrganizationRole.ADMIN
        new_owner.role = OrganizationRole.OWNER
        
        self.db.commit()
        
        return True
    
    def _generate_slug(self, name: str) -> str:
        """Generate unique slug from name"""
        from slugify import slugify
        import secrets
        
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        
        # Check for uniqueness
        while self.get_organization_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
            if counter > 10:
                # Add random suffix if too many collisions
                slug = f"{base_slug}-{secrets.token_urlsafe(4)}"
                break
        
        return slug