"""
Two-Factor Authentication API endpoints
"""

import pyotp
import qrcode
import io
import base64
import json
from typing import Annotated, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_active_user, get_config
from ..core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_recovery_codes,
    hash_recovery_code,
    verify_recovery_code
)
from ..core.events import auth_events
from ..models.user import BaseUser, UserSession
from ..schemas.two_factor import (
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    TwoFactorEnableResponse,
    TwoFactorDisableRequest,
    RecoveryCodesRegenerateRequest,
    RecoveryCodesResponse,
    TwoFactorLoginVerifyRequest,
    TwoFactorStatusResponse
)
from ..schemas.auth import LoginResponse, TokenResponse, MessageResponse

router = APIRouter()


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: Annotated[BaseUser, Depends(get_current_active_user)]
):
    """Get 2FA status for current user"""
    recovery_codes = []
    if current_user.two_factor_recovery_codes:
        recovery_codes = json.loads(current_user.two_factor_recovery_codes)
    
    return TwoFactorStatusResponse(
        enabled=current_user.two_factor_enabled,
        method="totp" if current_user.two_factor_enabled else None,
        backup_codes_remaining=len([c for c in recovery_codes if c.get("used") is False]) if recovery_codes else None,
        created_at=current_user.updated_at.isoformat() if current_user.two_factor_enabled else None
    )


@router.post("/setup/begin", response_model=TwoFactorSetupResponse)
async def begin_2fa_setup(
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    config = Depends(get_config)
):
    """Begin 2FA setup process"""
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    # Generate secret
    secret = pyotp.random_base32()
    
    # Store secret temporarily (use Redis/cache in production)
    request.session["2fa_temp_secret"] = secret
    
    # Generate provisioning URI
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=config.totp_issuer
    )
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{qr_code_b64}",
        manual_entry_key=secret,
        message="Scan the QR code with your authenticator app"
    )


@router.post("/setup/verify", response_model=TwoFactorEnableResponse)
async def verify_2fa_setup(
    verify_data: TwoFactorVerifyRequest,
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Verify and enable 2FA"""
    # Get temporary secret
    temp_secret = request.session.get("2fa_temp_secret")
    if not temp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Setup session expired. Please start again."
        )
    
    # Verify TOTP code
    totp = pyotp.TOTP(temp_secret)
    if not totp.verify(verify_data.code, valid_window=config.totp_window):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Generate recovery codes
    recovery_codes = generate_recovery_codes(config.recovery_codes_count)
    
    # Hash recovery codes for storage
    hashed_codes = [
        {"code": hash_recovery_code(code), "used": False}
        for code in recovery_codes
    ]
    
    # Enable 2FA
    current_user.two_factor_enabled = True
    current_user.two_factor_secret = temp_secret
    current_user.two_factor_recovery_codes = json.dumps(hashed_codes)
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Clear temporary secret
    request.session.pop("2fa_temp_secret", None)
    
    # Emit event
    await auth_events.emit("2fa_enabled", {"user_id": str(current_user.id)})
    
    return TwoFactorEnableResponse(
        recovery_codes=recovery_codes,
        message="Two-factor authentication has been enabled. Save these recovery codes in a safe place."
    )


@router.post("/disable", response_model=MessageResponse)
async def disable_2fa(
    disable_data: TwoFactorDisableRequest,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Disable 2FA"""
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not current_user.verify_password(disable_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.two_factor_recovery_codes = None
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Emit event
    await auth_events.emit("2fa_disabled", {"user_id": str(current_user.id)})
    
    return MessageResponse(message="Two-factor authentication has been disabled")


@router.post("/recovery-codes", response_model=RecoveryCodesResponse)
async def regenerate_recovery_codes(
    regenerate_data: RecoveryCodesRegenerateRequest,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Regenerate recovery codes"""
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not current_user.verify_password(regenerate_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Generate new recovery codes
    recovery_codes = generate_recovery_codes(config.recovery_codes_count)
    
    # Hash for storage
    hashed_codes = [
        {"code": hash_recovery_code(code), "used": False}
        for code in recovery_codes
    ]
    
    # Update recovery codes
    current_user.two_factor_recovery_codes = json.dumps(hashed_codes)
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Emit event
    await auth_events.emit("recovery_codes_generated", {"user_id": str(current_user.id)})
    
    return RecoveryCodesResponse(
        recovery_codes=recovery_codes,
        message="New recovery codes have been generated. Save them in a safe place."
    )


@router.post("/verify/login", response_model=LoginResponse)
async def verify_2fa_login(
    verify_data: TwoFactorLoginVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Verify 2FA during login"""
    # Get temp token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
    
    temp_token = auth_header.split(" ")[1]
    
    # Decode temp token
    try:
        payload = decode_token(temp_token, config.jwt_secret, config.jwt_algorithm)
        if payload.get("type") != "2fa_temp":
            raise ValueError("Invalid token type")
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")
            
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Get user
    User = config.user_model
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Verify code
    verified = False
    
    if verify_data.is_recovery_code:
        # Verify recovery code
        if not user.two_factor_recovery_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No recovery codes available"
            )
        
        recovery_codes = json.loads(user.two_factor_recovery_codes)
        
        for i, stored_code in enumerate(recovery_codes):
            if not stored_code["used"] and verify_recovery_code(verify_data.code, stored_code["code"]):
                recovery_codes[i]["used"] = True
                user.two_factor_recovery_codes = json.dumps(recovery_codes)
                verified = True
                break
                
    else:
        # Verify TOTP code
        if not user.two_factor_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA not properly configured"
            )
        
        totp = pyotp.TOTP(user.two_factor_secret)
        verified = totp.verify(verify_data.code, valid_window=config.totp_window)
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Create full tokens
    from datetime import timezone
    
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
    
    # Emit event
    await auth_events.emit("2fa_verified", {"user_id": str(user.id)})
    
    return LoginResponse(
        user=user,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
    )