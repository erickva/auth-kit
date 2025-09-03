"""
Authentication API endpoints
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..core.dependencies import get_current_user, get_current_active_user, get_config
from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    generate_password_reset_token,
    verify_password_reset_token,
    generate_email_verification_token,
    verify_email_verification_token
)
from ..core.events import auth_events
from ..models.user import BaseUser, UserSession
from ..schemas.auth import (
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    MessageResponse
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Register a new user"""
    # Check if user exists
    User = config.user_model
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        is_verified=not config.is_feature_enabled("email_verification")
    )
    new_user.set_password(user_data.password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send verification email if enabled
    if config.is_feature_enabled("email_verification") and not new_user.is_verified:
        # TODO: Send verification email
        await auth_events.emit("email_verification_sent", {"user_id": str(new_user.id)})
    
    # Emit registration event
    await auth_events.emit("user_registered", {"user_id": str(new_user.id)})
    
    return new_user


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Login with email and password"""
    # Find user by email
    User = config.user_model
    user = db.query(User).filter(
        User.email == form_data.username
    ).first()
    
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Check if 2FA is enabled
    if user.two_factor_enabled:
        # Create temporary token for 2FA verification
        temp_token_data = {"sub": str(user.id), "type": "2fa_temp"}
        temp_token = create_access_token(
            temp_token_data,
            config.jwt_secret,
            config.jwt_algorithm,
            expires_delta=timedelta(minutes=5)
        )
        
        return LoginResponse(
            user=user,
            tokens=TokenResponse(
                access_token=temp_token,
                token_type="bearer",
                expires_in=300  # 5 minutes
            ),
            requires_2fa=True,
            message="Two-factor authentication required"
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
    refresh_token_expires = timedelta(days=config.refresh_token_expire_days)
    
    access_token = create_access_token(
        {"sub": str(user.id)},
        config.jwt_secret,
        config.jwt_algorithm,
        expires_delta=access_token_expires
    )
    
    refresh_token, jti = create_refresh_token(
        {"sub": str(user.id)},
        config.jwt_secret,
        config.jwt_algorithm,
        expires_delta=refresh_token_expires
    )
    
    # Create session
    session = UserSession(
        user_id=user.id,
        refresh_token_jti=jti,
        device_id=request.headers.get("X-Device-ID"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
        expires_at=datetime.now(timezone.utc) + refresh_token_expires
    )
    db.add(session)
    
    # Update last login
    user.update_last_login()
    db.commit()
    
    # Emit login event
    await auth_events.emit("user_logged_in", {"user_id": str(user.id)})
    
    return LoginResponse(
        user=user,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Refresh access token"""
    try:
        # Decode refresh token
        payload = decode_token(
            refresh_data.refresh_token,
            config.jwt_secret,
            config.jwt_algorithm
        )
        
        # Verify token type
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        # Get JTI and user ID
        jti = payload.get("jti")
        user_id = payload.get("sub")
        
        if not jti or not user_id:
            raise ValueError("Invalid token payload")
        
        # Find session
        session = db.query(UserSession).filter(
            UserSession.refresh_token_jti == jti,
            UserSession.user_id == user_id
        ).first()
        
        if not session or session.is_expired:
            raise ValueError("Session expired or not found")
        
        # Get user
        User = config.user_model
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")
        
        # Create new access token
        access_token_expires = timedelta(minutes=config.access_token_expire_minutes)
        access_token = create_access_token(
            {"sub": str(user.id)},
            config.jwt_secret,
            config.jwt_algorithm,
            expires_delta=access_token_expires
        )
        
        # Update session activity
        session.update_activity()
        db.commit()
        
        # Emit event
        await auth_events.emit("token_refreshed", {"user_id": str(user.id)})
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    logout_data: LogoutRequest,
    current_user: Annotated[BaseUser, Depends(get_current_user)],
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Logout user"""
    try:
        # Decode refresh token to get JTI
        payload = decode_token(
            logout_data.refresh_token,
            config.jwt_secret,
            config.jwt_algorithm
        )
        jti = payload.get("jti")
        
        if logout_data.everywhere:
            # Delete all user sessions
            db.query(UserSession).filter(
                UserSession.user_id == current_user.id
            ).delete()
        else:
            # Delete specific session
            db.query(UserSession).filter(
                UserSession.refresh_token_jti == jti,
                UserSession.user_id == current_user.id
            ).delete()
        
        db.commit()
        
        # Emit logout event
        await auth_events.emit("user_logged_out", {"user_id": str(current_user.id)})
        
        return MessageResponse(message="Successfully logged out")
        
    except Exception:
        # Even if token is invalid, consider it a successful logout
        return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: Annotated[BaseUser, Depends(get_current_active_user)]
):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Update user profile"""
    # Update fields
    for field, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    # Emit update event
    await auth_events.emit("user_updated", {"user_id": str(current_user.id)})
    
    return current_user


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Change password"""
    # Verify current password
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Set new password
    current_user.set_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    
    # Optionally invalidate all sessions
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id
    ).delete()
    
    db.commit()
    
    # Emit event
    await auth_events.emit("password_changed", {"user_id": str(current_user.id)})
    
    return MessageResponse(message="Password changed successfully")


@router.post("/password/reset", response_model=MessageResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Request password reset"""
    # Find user
    User = config.user_model
    user = db.query(User).filter(
        User.email == reset_data.email
    ).first()
    
    # Always return success to prevent email enumeration
    if user and user.is_active:
        # Generate reset token
        reset_token = generate_password_reset_token(
            user.email,
            config.jwt_secret
        )
        
        # TODO: Send password reset email
        await auth_events.emit("password_reset_requested", {
            "user_id": str(user.id),
            "email": user.email
        })
    
    return MessageResponse(
        message="If the email exists, password reset instructions have been sent"
    )


@router.post("/password/reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Confirm password reset"""
    # Verify token
    email = verify_password_reset_token(
        reset_confirm.token,
        config.jwt_secret
    )
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Find user
    User = config.user_model
    user = db.query(User).filter(
        User.email == email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Set new password
    user.set_password(reset_confirm.new_password)
    user.updated_at = datetime.utcnow()
    
    # Invalidate all sessions
    db.query(UserSession).filter(
        UserSession.user_id == user.id
    ).delete()
    
    db.commit()
    
    # Emit event
    await auth_events.emit("password_reset_completed", {"user_id": str(user.id)})
    
    return MessageResponse(message="Password has been reset successfully")


@router.get("/verify-email/{token}", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Verify email address"""
    # Verify token
    email = verify_email_verification_token(
        token,
        config.jwt_secret
    )
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Find user
    User = config.user_model
    user = db.query(User).filter(
        User.email == email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    if user.is_verified:
        return MessageResponse(message="Email already verified")
    
    # Verify email
    user.verify_email()
    db.commit()
    
    # Emit event
    await auth_events.emit("email_verified", {"user_id": str(user.id)})
    
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    config = Depends(get_config)
):
    """Resend email verification"""
    if current_user.is_verified:
        return MessageResponse(message="Email already verified")
    
    # Generate verification token
    verification_token = generate_email_verification_token(
        current_user.email,
        config.jwt_secret
    )
    
    # TODO: Send verification email
    await auth_events.emit("email_verification_sent", {
        "user_id": str(current_user.id),
        "email": current_user.email
    })
    
    return MessageResponse(message="Verification email sent")