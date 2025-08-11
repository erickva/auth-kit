"""
FastAPI Backend Example using auth-kit-fastapi
"""

import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from auth_kit_fastapi import (
    AuthConfig,
    init_auth,
    auth_router,
    BaseUser,
    Base
)
from auth_kit_fastapi.core.events import auth_events

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./authkit_demo.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Auth configuration
auth_config = AuthConfig(
    # JWT settings
    jwt_secret=os.getenv("JWT_SECRET", "change-this-secret-key"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
    refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")),
    
    # Passkey settings
    passkey_rp_id=os.getenv("PASSKEY_RP_ID", "localhost"),
    passkey_rp_name=os.getenv("PASSKEY_RP_NAME", "Auth Kit Demo"),
    passkey_origin=os.getenv("PASSKEY_ORIGIN", "http://localhost:3000"),
    passkey_timeout_ms=int(os.getenv("PASSKEY_TIMEOUT_MS", "60000")),
    
    # 2FA settings
    totp_issuer=os.getenv("TOTP_ISSUER", "Auth Kit Demo"),
    totp_window=int(os.getenv("TOTP_WINDOW", "1")),
    recovery_codes_count=int(os.getenv("RECOVERY_CODES_COUNT", "8")),
    
    # Email settings (optional)
    smtp_host=os.getenv("SMTP_HOST"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None,
    smtp_username=os.getenv("SMTP_USERNAME"),
    smtp_password=os.getenv("SMTP_PASSWORD"),
    smtp_tls=os.getenv("SMTP_TLS", "true").lower() == "true",
    smtp_ssl=os.getenv("SMTP_SSL", "false").lower() == "true",
    email_from=os.getenv("EMAIL_FROM", "noreply@authkit.demo"),
    email_template_dir=os.getenv("EMAIL_TEMPLATE_DIR"),
    
    # App settings
    app_name=os.getenv("APP_NAME", "Auth Kit Demo"),
    app_url=os.getenv("APP_URL", "http://localhost:3000"),
    support_email=os.getenv("SUPPORT_EMAIL", "support@authkit.demo"),
    
    # Feature flags
    features={
        "email_verification": os.getenv("ENABLE_EMAIL_VERIFICATION", "true").lower() == "true",
        "password_reset": os.getenv("ENABLE_PASSWORD_RESET", "true").lower() == "true",
        "two_factor": os.getenv("ENABLE_2FA", "true").lower() == "true",
        "passkeys": os.getenv("ENABLE_PASSKEYS", "true").lower() == "true"
    }
)


# Event handlers
@auth_events.on("user_registered")
async def handle_user_registered(event):
    """Handle user registration event"""
    print(f"New user registered: {event['data']['user_id']}")
    # You can add custom logic here like:
    # - Send welcome email
    # - Add to mailing list
    # - Create default user settings
    

@auth_events.on("user_logged_in")
async def handle_user_login(event):
    """Handle user login event"""
    print(f"User logged in: {event['data']['user_id']}")
    # You can add custom logic here like:
    # - Log login attempt
    # - Update last login timestamp
    # - Check for suspicious activity
    

@auth_events.on("2fa_enabled")
async def handle_2fa_enabled(event):
    """Handle 2FA enabled event"""
    print(f"2FA enabled for user: {event['data']['user_id']}")
    # You can add custom logic here like:
    # - Send confirmation email
    # - Award security badge
    # - Update user security score
    

@auth_events.on("passkey_registered")
async def handle_passkey_registered(event):
    """Handle passkey registration event"""
    print(f"Passkey registered for user: {event['data']['user_id']}")
    # You can add custom logic here like:
    # - Send notification email
    # - Log device information
    # - Update security settings


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting Auth Kit Demo API...")
    
    # Initialize auth with database session
    init_auth(app, auth_config, SessionLocal)
    
    yield
    
    # Shutdown
    print("Shutting down Auth Kit Demo API...")


# Create FastAPI app
app = FastAPI(
    title="Auth Kit Demo API",
    description="Example API using auth-kit-fastapi",
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

# Include auth router
app.include_router(auth_router, prefix="/api")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth-kit-demo",
        "features": {
            "email_verification": auth_config.is_feature_enabled("email_verification"),
            "password_reset": auth_config.is_feature_enabled("password_reset"),
            "two_factor": auth_config.is_feature_enabled("two_factor"),
            "passkeys": auth_config.is_feature_enabled("passkeys")
        }
    }

# Example protected endpoint
from fastapi import Depends
from auth_kit_fastapi.core.dependencies import get_current_active_user

@app.get("/api/protected")
async def protected_endpoint(current_user: BaseUser = Depends(get_current_active_user)):
    """Example protected endpoint"""
    return {
        "message": "This is a protected endpoint",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "is_verified": current_user.is_verified,
            "two_factor_enabled": current_user.two_factor_enabled
        }
    }

# Custom error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_error"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )