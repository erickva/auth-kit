"""
Main application factory for Auth Kit FastAPI
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import AuthConfig
from .database import get_db, init_db
from ..api import auth, passkeys, two_factor
from ..models.user import Base


def create_auth_app(config: AuthConfig) -> FastAPI:
    """
    Create and configure the Auth Kit FastAPI application
    
    Args:
        config: Authentication configuration
        
    Returns:
        Configured FastAPI application
    """
    
    # Create FastAPI app
    app = FastAPI(
        title="Auth Kit API",
        description="Authentication API powered by Auth Kit",
        version="1.0.0"
    )
    
    # Configure CORS
    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=config.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Store config in app state
    app.state.config = config
    
    # Initialize database
    engine = create_engine(
        config.database_url,
        echo=config.database_echo,
        pool_pre_ping=True
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Store database session factory
    app.state.db_session = SessionLocal
    
    # Include routers
    app.include_router(
        auth.router,
        prefix="",
        tags=["Authentication"]
    )
    
    if config.is_feature_enabled("passkeys"):
        app.include_router(
            passkeys.router,
            prefix="/passkeys",
            tags=["Passkeys"]
        )
    
    if config.is_feature_enabled("two_factor"):
        app.include_router(
            two_factor.router,
            prefix="/2fa",
            tags=["Two-Factor Authentication"]
        )
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Check if the authentication service is running"""
        return {
            "status": "healthy",
            "service": "auth-kit",
            "features": {
                "passkeys": config.is_feature_enabled("passkeys"),
                "two_factor": config.is_feature_enabled("two_factor"),
                "email_verification": config.is_feature_enabled("email_verification"),
                "social_login": config.get_social_providers()
            }
        }
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        # Initialize any services that need startup
        pass
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        # Cleanup any resources
        pass
    
    return app