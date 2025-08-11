# Custom User Models Guide

This guide explains how to extend the default user model with custom fields and functionality.

## CLI Support

When creating a new project with the CLI, you can specify that you need custom user fields:

```bash
# The CLI will ask about custom user fields during setup
npx @auth-kit/cli create my-app

# Generate user profile components
npx @auth-kit/cli generate component ProfileSettings
npx @auth-kit/cli generate component AvatarUpload
```

For existing projects, the CLI-generated structure makes it easy to extend the user model by modifying the generated files.

## Overview

Auth Kit provides a flexible user model that can be extended to meet your application's specific needs. This guide covers:
- Adding custom fields to the user model
- Creating database migrations
- Updating schemas and types
- Frontend integration
- Common customization patterns

## Backend Customization

### 1. Extending the User Model

The base user model includes essential fields. You can extend it by creating your own model:

```python
# backend/app/models/user.py
from auth_kit_fastapi.models import BaseUser
from sqlalchemy import Column, String, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class User(BaseUser):
    __tablename__ = "users"
    
    # Add custom fields
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(500), nullable=True)
    
    # Role-based access control
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    # Preferences stored as JSON
    preferences = Column(JSON, default=dict)
    
    # Organization/Company fields
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    
    # Additional metadata
    metadata = Column(JSON, default=dict)
    last_login_ip = Column(String(45), nullable=True)
    login_count = Column(Integer, default=0)
    
    # Custom methods
    def get_display_name(self) -> str:
        """Get user's display name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split('@')[0]
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.role == UserRole.ADMIN:
            return True
        
        # Add custom permission logic
        permissions_map = {
            UserRole.MODERATOR: ["read", "write", "moderate"],
            UserRole.USER: ["read"]
        }
        
        return permission in permissions_map.get(self.role, [])
    
    def to_dict(self) -> dict:
        """Convert user to dictionary with custom fields"""
        base_dict = super().to_dict()
        base_dict.update({
            "phone_number": self.phone_number,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "role": self.role.value if self.role else None,
            "display_name": self.get_display_name(),
            "company_name": self.company_name,
            "job_title": self.job_title,
        })
        return base_dict
```

### 2. Creating Migrations

After adding custom fields, create a database migration:

```bash
# Generate migration
alembic revision --autogenerate -m "Add custom user fields"

# Apply migration
alembic upgrade head
```

Example migration file:

```python
# migrations/versions/xxx_add_custom_user_fields.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add custom columns
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('bio', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('role', sa.Enum('user', 'admin', 'moderator', name='userrole'), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('preferences', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('users', sa.Column('company_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('job_title', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('metadata', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('users', sa.Column('last_login_ip', sa.String(45), nullable=True))
    op.add_column('users', sa.Column('login_count', sa.Integer(), nullable=False, server_default='0'))
    
    # Add indexes for frequently queried fields
    op.create_index('ix_users_phone_number', 'users', ['phone_number'])
    op.create_index('ix_users_role', 'users', ['role'])

def downgrade():
    op.drop_index('ix_users_role', 'users')
    op.drop_index('ix_users_phone_number', 'users')
    
    op.drop_column('users', 'login_count')
    op.drop_column('users', 'last_login_ip')
    op.drop_column('users', 'metadata')
    op.drop_column('users', 'job_title')
    op.drop_column('users', 'company_name')
    op.drop_column('users', 'preferences')
    op.drop_column('users', 'role')
    op.drop_column('users', 'bio')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'phone_number')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS userrole')
```

### 3. Updating Schemas

Create Pydantic schemas for your custom fields:

```python
# backend/app/schemas/user.py
from auth_kit_fastapi.schemas import UserCreate as BaseUserCreate, UserUpdate as BaseUserUpdate, UserResponse as BaseUserResponse
from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

class UserPreferences(BaseModel):
    theme: str = "light"
    language: str = "en"
    notifications_enabled: bool = True
    email_frequency: str = "daily"

class UserCreate(BaseUserCreate):
    # Add custom fields to registration
    phone_number: Optional[str] = Field(None, max_length=20, regex=r'^\+?1?\d{9,15}$')
    date_of_birth: Optional[datetime] = None
    company_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    
    @validator('date_of_birth')
    def validate_age(cls, v):
        if v and v > datetime.now():
            raise ValueError('Date of birth cannot be in the future')
        if v and (datetime.now() - v).days < 365 * 13:  # Must be at least 13
            raise ValueError('User must be at least 13 years old')
        return v

class UserUpdate(BaseUserUpdate):
    # Fields that can be updated
    phone_number: Optional[str] = Field(None, max_length=20, regex=r'^\+?1?\d{9,15}$')
    date_of_birth: Optional[datetime] = None
    avatar_url: Optional[HttpUrl] = None
    bio: Optional[str] = Field(None, max_length=500)
    company_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    preferences: Optional[UserPreferences] = None

class UserResponse(BaseUserResponse):
    # Fields returned in API responses
    phone_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    role: UserRole = UserRole.USER
    display_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    preferences: Dict[str, Any] = {}
    login_count: int = 0
    
    class Config:
        orm_mode = True

class AdminUserResponse(UserResponse):
    # Additional fields for admin views
    last_login_ip: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
```

### 4. Custom API Endpoints

Add endpoints for your custom functionality:

```python
# backend/app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import boto3  # For S3 avatar uploads

from app.models.user import User, UserRole
from app.schemas.user import UserUpdate, UserResponse, AdminUserResponse
from auth_kit_fastapi.core.dependencies import get_current_user, get_db

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile with custom fields"""
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload user avatar"""
    # Validate file
    if file.content_type not in ["image/jpeg", "image/png", "image/gif"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if file.size > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File too large")
    
    # Upload to S3 or local storage
    file_key = f"avatars/{current_user.id}/{file.filename}"
    # ... upload logic ...
    
    # Update user
    current_user.avatar_url = f"https://cdn.example.com/{file_key}"
    db.commit()
    
    return {"avatar_url": current_user.avatar_url}

@router.get("/users", response_model=List[AdminUserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List users (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: UserRole,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = role
    db.commit()
    
    return {"message": f"User role updated to {role}"}
```

## Frontend Integration

### 1. Update TypeScript Types

Create types for your custom fields:

```typescript
// frontend/src/types/user.ts
export interface User {
  // Base fields from auth-kit
  id: string
  email: string
  firstName?: string
  lastName?: string
  emailVerified: boolean
  
  // Custom fields
  phoneNumber?: string
  dateOfBirth?: string
  avatarUrl?: string
  bio?: string
  role: 'user' | 'admin' | 'moderator'
  displayName: string
  companyName?: string
  jobTitle?: string
  preferences: UserPreferences
  loginCount: number
}

export interface UserPreferences {
  theme: 'light' | 'dark'
  language: string
  notificationsEnabled: boolean
  emailFrequency: 'daily' | 'weekly' | 'never'
}

export interface UpdateProfileData {
  firstName?: string
  lastName?: string
  phoneNumber?: string
  dateOfBirth?: string
  bio?: string
  companyName?: string
  jobTitle?: string
  preferences?: Partial<UserPreferences>
}
```

### 2. Profile Management Component

Create components to manage custom fields:

```tsx
// frontend/src/components/ProfileSettings.tsx
import React, { useState } from 'react'
import { useAuth } from '@auth-kit/react'
import { UpdateProfileData } from '../types/user'

export function ProfileSettings() {
  const { user, updateUser } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState<UpdateProfileData>({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    phoneNumber: user?.phoneNumber || '',
    bio: user?.bio || '',
    companyName: user?.companyName || '',
    jobTitle: user?.jobTitle || '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await updateUser(formData)
      alert('Profile updated successfully!')
    } catch (error) {
      console.error('Failed to update profile:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  return (
    <form onSubmit={handleSubmit} className="profile-settings">
      <h2>Profile Settings</h2>
      
      <div className="form-group">
        <label htmlFor="firstName">First Name</label>
        <input
          id="firstName"
          name="firstName"
          type="text"
          value={formData.firstName}
          onChange={handleInputChange}
        />
      </div>

      <div className="form-group">
        <label htmlFor="lastName">Last Name</label>
        <input
          id="lastName"
          name="lastName"
          type="text"
          value={formData.lastName}
          onChange={handleInputChange}
        />
      </div>

      <div className="form-group">
        <label htmlFor="phoneNumber">Phone Number</label>
        <input
          id="phoneNumber"
          name="phoneNumber"
          type="tel"
          value={formData.phoneNumber}
          onChange={handleInputChange}
          placeholder="+1234567890"
        />
      </div>

      <div className="form-group">
        <label htmlFor="bio">Bio</label>
        <textarea
          id="bio"
          name="bio"
          value={formData.bio}
          onChange={handleInputChange}
          rows={4}
          maxLength={500}
        />
        <small>{formData.bio?.length || 0}/500 characters</small>
      </div>

      <div className="form-group">
        <label htmlFor="companyName">Company</label>
        <input
          id="companyName"
          name="companyName"
          type="text"
          value={formData.companyName}
          onChange={handleInputChange}
        />
      </div>

      <div className="form-group">
        <label htmlFor="jobTitle">Job Title</label>
        <input
          id="jobTitle"
          name="jobTitle"
          type="text"
          value={formData.jobTitle}
          onChange={handleInputChange}
        />
      </div>

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Saving...' : 'Save Changes'}
      </button>
    </form>
  )
}
```

### 3. Avatar Upload Component

Handle avatar uploads:

```tsx
// frontend/src/components/AvatarUpload.tsx
import React, { useState, useRef } from 'react'
import { useAuth } from '@auth-kit/react'

export function AvatarUpload() {
  const { user, updateUser } = useAuth()
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file
    if (!['image/jpeg', 'image/png', 'image/gif'].includes(file.type)) {
      alert('Please select a valid image file')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('File size must be less than 5MB')
      return
    }

    setIsUploading(true)

    try {
      // Upload to server
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/users/avatar', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authkit_access_token')}`
        },
        body: formData
      })

      if (!response.ok) throw new Error('Upload failed')

      const { avatar_url } = await response.json()
      
      // Update local user state
      await updateUser({ avatarUrl: avatar_url })
    } catch (error) {
      console.error('Failed to upload avatar:', error)
      alert('Failed to upload avatar')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="avatar-upload">
      <div className="current-avatar">
        {user?.avatarUrl ? (
          <img src={user.avatarUrl} alt="Avatar" />
        ) : (
          <div className="avatar-placeholder">
            {user?.displayName?.charAt(0).toUpperCase()}
          </div>
        )}
      </div>
      
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
      >
        {isUploading ? 'Uploading...' : 'Change Avatar'}
      </button>
    </div>
  )
}
```

### 4. Role-Based Access Control

Implement RBAC in your components:

```tsx
// frontend/src/components/AdminPanel.tsx
import { useAuth } from '@auth-kit/react'
import { Navigate } from 'react-router-dom'

export function AdminPanel() {
  const { user } = useAuth()

  // Check role
  if (!user || user.role !== 'admin') {
    return <Navigate to="/unauthorized" />
  }

  return (
    <div className="admin-panel">
      <h1>Admin Panel</h1>
      {/* Admin-only content */}
    </div>
  )
}

// Create a reusable RBAC component
export function RequireRole({ 
  roles, 
  children, 
  fallback = <div>Unauthorized</div> 
}: {
  roles: string[]
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  const { user } = useAuth()

  if (!user || !roles.includes(user.role)) {
    return <>{fallback}</>
  }

  return <>{children}</>
}

// Usage
<RequireRole roles={['admin', 'moderator']}>
  <ModeratorTools />
</RequireRole>
```

## Common Customization Patterns

### 1. Multi-tenancy

Add organization/tenant support:

```python
class User(BaseUser):
    # Organization fields
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'))
    organization = relationship("Organization", back_populates="users")
    organization_role = Column(String(50), default="member")
    
    def can_access_organization(self, org_id: str) -> bool:
        return str(self.organization_id) == org_id
```

### 2. Social Profiles

Link social media accounts:

```python
class SocialProfile(Base):
    __tablename__ = "social_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    provider = Column(String(50))  # twitter, linkedin, github
    profile_url = Column(String(500))
    username = Column(String(100))
    
    user = relationship("User", back_populates="social_profiles")

class User(BaseUser):
    social_profiles = relationship("SocialProfile", back_populates="user")
```

### 3. User Preferences

Store complex preferences:

```python
class User(BaseUser):
    preferences = Column(JSON, default=lambda: {
        "notifications": {
            "email": True,
            "push": True,
            "sms": False,
            "marketing": False
        },
        "privacy": {
            "profile_visible": True,
            "show_email": False,
            "show_phone": False
        },
        "ui": {
            "theme": "light",
            "language": "en",
            "timezone": "UTC"
        }
    })
```

### 4. Audit Trail

Track user actions:

```python
class UserAuditLog(Base):
    __tablename__ = "user_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")

class User(BaseUser):
    audit_logs = relationship("UserAuditLog", back_populates="user")
    
    def log_action(self, action: str, details: dict = None, request = None):
        log = UserAuditLog(
            user_id=self.id,
            action=action,
            details=details or {},
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )
        db.add(log)
```

## Best Practices

### 1. Data Validation

Always validate custom fields:

```python
@validator('phone_number')
def validate_phone(cls, v):
    if v and not re.match(r'^\+?1?\d{9,15}$', v):
        raise ValueError('Invalid phone number format')
    return v

@validator('bio')
def validate_bio(cls, v):
    if v and len(v) > 500:
        raise ValueError('Bio must be 500 characters or less')
    return v
```

### 2. Privacy Considerations

Control what data is exposed:

```python
class UserResponse(BaseModel):
    # Public fields
    id: str
    display_name: str
    avatar_url: Optional[str]
    
    @classmethod
    def from_user(cls, user: User, include_private: bool = False):
        data = {
            "id": str(user.id),
            "display_name": user.get_display_name(),
            "avatar_url": user.avatar_url
        }
        
        if include_private:
            data.update({
                "email": user.email,
                "phone_number": user.phone_number,
                "date_of_birth": user.date_of_birth
            })
        
        return cls(**data)
```

### 3. Migration Strategy

Plan for data migrations:

```python
# Add fields with defaults for existing users
def upgrade():
    op.add_column('users', 
        sa.Column('preferences', sa.JSON(), 
                  nullable=False, 
                  server_default='{}')
    )
    
    # Populate data for existing users
    op.execute("""
        UPDATE users 
        SET preferences = '{"theme": "light", "language": "en"}'
        WHERE preferences = '{}'
    """)
```

### 4. Performance

Index frequently queried fields:

```python
class User(BaseUser):
    __table_args__ = (
        Index('ix_users_role_active', 'role', 'is_active'),
        Index('ix_users_org_role', 'organization_id', 'organization_role'),
    )
```

## Testing Custom Fields

Write tests for your customizations:

```python
async def test_custom_user_fields():
    # Test user creation with custom fields
    user_data = {
        "email": "test@example.com",
        "password": "password123",
        "phone_number": "+1234567890",
        "company_name": "Test Corp",
        "job_title": "Developer"
    }
    
    response = await client.post("/api/auth/register", json=user_data)
    assert response.status_code == 201
    
    user = response.json()
    assert user["phone_number"] == "+1234567890"
    assert user["company_name"] == "Test Corp"
    assert user["display_name"] == "test"

async def test_profile_update():
    # Test updating custom fields
    update_data = {
        "bio": "Software developer passionate about auth",
        "preferences": {
            "theme": "dark",
            "language": "es"
        }
    }
    
    response = await client.put("/api/users/profile", 
                                json=update_data,
                                headers=auth_headers)
    assert response.status_code == 200
    
    updated = response.json()
    assert updated["bio"] == update_data["bio"]
    assert updated["preferences"]["theme"] == "dark"
```

## Next Steps

- Implement [Email Verification](./email-verification.md) for custom fields
- Add validation for phone numbers with [SMS verification](./sms-verification.md)
- Create admin interface for user management
- Set up analytics for custom field usage