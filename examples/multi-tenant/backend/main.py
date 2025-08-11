"""
Multi-tenant SaaS API with Auth Kit
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from auth_kit_fastapi import AuthConfig, init_auth, auth_router, Base
from auth_kit_fastapi.core.events import auth_events

from .models import Organization, OrganizationMember, Project, AuditLog
from .api import organizations, members, projects, context
from .core.audit import AuditLogger

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/multitenant_saas")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
Base.metadata.create_all(bind=engine)

# Auth configuration
auth_config = AuthConfig(
    jwt_secret=os.getenv("JWT_SECRET", "change-this-secret-key"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")),
    
    passkey_rp_id=os.getenv("PASSKEY_RP_ID", "localhost"),
    passkey_rp_name=os.getenv("PASSKEY_RP_NAME", "Multi-Tenant SaaS"),
    passkey_origin=os.getenv("PASSKEY_ORIGIN", "http://localhost:3000"),
    
    totp_issuer=os.getenv("TOTP_ISSUER", "Multi-Tenant SaaS"),
    
    app_name=os.getenv("APP_NAME", "Multi-Tenant SaaS"),
    app_url=os.getenv("APP_URL", "http://localhost:3000"),
    
    features={
        "email_verification": os.getenv("ENABLE_EMAIL_VERIFICATION", "true").lower() == "true",
        "organization_invitations": os.getenv("ENABLE_ORGANIZATION_INVITATIONS", "true").lower() == "true",
        "audit_logs": os.getenv("ENABLE_AUDIT_LOGS", "true").lower() == "true"
    }
)


# Event handlers for audit logging
@auth_events.on("user_registered")
async def handle_user_registered(event):
    """Create default organization for new users"""
    from .services import OrganizationService
    
    user_id = event["data"]["user_id"]
    
    # Create a database session
    db = SessionLocal()
    try:
        service = OrganizationService(db)
        
        # Create default personal organization
        org_name = f"Personal Workspace"
        org = await service.create_organization(
            name=org_name,
            owner_id=user_id,
            plan="free"
        )
        
        print(f"Created default organization for user {user_id}: {org.slug}")
        
    finally:
        db.close()


@auth_events.on("user_logged_in")
async def handle_user_login(event):
    """Log user login in audit log"""
    # In a real app, you'd log this to the user's organizations
    print(f"User logged in: {event['data']['user_id']}")


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Multi-Tenant SaaS API...")
    
    # Initialize auth
    init_auth(app, auth_config, SessionLocal)
    
    # Store config for use in dependencies
    app.state.auth_config = auth_config
    
    yield
    
    # Shutdown
    print("Shutting down Multi-Tenant SaaS API...")


# Create FastAPI app
app = FastAPI(
    title="Multi-Tenant SaaS API",
    description="Multi-tenant SaaS example with Auth Kit",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["Organizations"])
app.include_router(members.router, prefix="/api/organizations", tags=["Members"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(context.router, prefix="/api/context", tags=["Context"])

# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "multi-tenant-saas",
        "features": {
            "multi_tenancy": True,
            "audit_logs": auth_config.is_feature_enabled("audit_logs"),
            "invitations": auth_config.is_feature_enabled("organization_invitations")
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-Tenant SaaS API",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )