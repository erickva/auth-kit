"""
FastAPI dependencies for authentication
"""

from typing import Optional, Annotated
from datetime import datetime, timezone
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from .database import get_db
from .security import decode_token
from ..models.user import BaseUser
from ..schemas.auth import ErrorResponse


# Custom bearer scheme that works better in sub-app contexts
# HTTPBearer extracts the bearer token without needing a tokenUrl
class BearerAuth(HTTPBearer):
    def __init__(self, auto_error: bool = False):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            return credentials.credentials
        return None

# OAuth2 scheme for token authentication
oauth2_scheme = BearerAuth(auto_error=False)


async def get_current_user(
    request: Request,
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> BaseUser:
    """
    Get current authenticated user from JWT token
    
    Args:
        request: FastAPI request object
        token: JWT access token
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # HTTPBearer handles token extraction, so if we don't have a token, fail
    if not token:
        raise credentials_exception
    
    try:
        # Get JWT config from app state
        config = request.app.state.config
        
        # Decode token
        payload = decode_token(
            token,
            config.jwt_secret,
            config.jwt_algorithm
        )
        
        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception
            
        # Get user ID
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Get user from database
    config = request.app.state.config
    User = config.user_model
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise credentials_exception
        
    return user


async def get_current_active_user(
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_user)]
) -> BaseUser:
    """
    Get current active user
    
    Args:
        request: FastAPI request object
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def require_verified_user(
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)]
) -> BaseUser:
    """
    Require email-verified user
    
    Args:
        request: FastAPI request object
        current_user: Current active user
        
    Returns:
        Verified user
        
    Raises:
        HTTPException: If user email is not verified
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


async def require_superuser(
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)]
) -> BaseUser:
    """
    Require superuser privileges
    
    Args:
        request: FastAPI request object
        current_user: Current active user
        
    Returns:
        Superuser
        
    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges"
        )
    return current_user


async def get_optional_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[BaseUser]:
    """
    Get optional authenticated user (for mixed auth endpoints)
    
    Args:
        request: FastAPI request object
        token: Optional JWT token
        db: Database session
        
    Returns:
        User object or None
    """
    if not token:
        return None
        
    try:
        return await get_current_user(request, token, db)
    except HTTPException:
        return None


def get_config(request: Request):
    """
    Get auth configuration from app state
    
    Args:
        request: FastAPI request object
        
    Returns:
        AuthConfig object
    """
    # Try to get config from current app state
    if hasattr(request.app.state, 'config'):
        return request.app.state.config
    
    # In sub-app context, check parent app (if mounted)
    # When mounted as sub-app, the request.scope might have the root path
    if hasattr(request, 'scope') and 'app' in request.scope:
        app = request.scope['app']
        if hasattr(app, 'state') and hasattr(app.state, 'config'):
            return app.state.config
    
    # Try to find config in parent app through mounting
    # This handles cases where the auth app is mounted on a main app
    if hasattr(request.app, 'routes'):
        for route in request.app.routes:
            if hasattr(route, 'app') and hasattr(route.app, 'state'):
                if hasattr(route.app.state, 'config'):
                    return route.app.state.config
    
    # If we still can't find config, raise an error
    raise RuntimeError("Auth configuration not found in app state")