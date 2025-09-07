"""
Passkey/WebAuthn API endpoints
"""

import base64
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    AuthenticatorTransport,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    AuthenticatorAttachment
)

from ..core.database import get_db
from ..core.dependencies import get_current_active_user, get_config
from ..core.security import create_access_token, create_refresh_token
from ..core.events import auth_events
from ..models.user import BaseUser, UserCredential, UserSession
from ..schemas.passkey import (
    PasskeyCreate,
    PasskeyResponse,
    PasskeyListResponse,
    RegistrationOptionsResponse,
    RegistrationCompleteRequest,
    AuthenticationOptionsResponse,
    AuthenticationCompleteRequest,
    AuthenticationBeginRequest
)
from ..schemas.auth import LoginResponse, TokenResponse, MessageResponse

router = APIRouter()


@router.get("/", response_model=PasskeyListResponse)
async def list_passkeys(
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """List user's passkeys"""
    passkeys = db.query(UserCredential).filter(
        UserCredential.user_id == current_user.id
    ).all()
    
    return PasskeyListResponse(
        passkeys=[PasskeyResponse.from_orm(p) for p in passkeys],
        total=len(passkeys)
    )


@router.post("/register/begin", response_model=RegistrationOptionsResponse)
async def begin_registration(
    passkey_data: PasskeyCreate,
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Begin passkey registration"""
    # Get existing credentials
    existing_credentials = db.query(UserCredential).filter(
        UserCredential.user_id == current_user.id
    ).all()
    
    exclude_credentials = []
    for cred in existing_credentials:
        exclude_credentials.append(
            PublicKeyCredentialDescriptor(
                id=base64.urlsafe_b64decode(cred.credential_id + "=="),
                transports=[AuthenticatorTransport.INTERNAL, AuthenticatorTransport.USB]
            )
        )
    
    # Generate registration options
    options = generate_registration_options(
        rp_id=config.passkey_rp_id,
        rp_name=config.passkey_rp_name,
        user_id=str(current_user.id).encode(),
        user_name=current_user.email,
        user_display_name=current_user.display_name,
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED
        ),
        timeout=config.passkey_timeout_ms
    )
    
    # Store challenge in session/cache (simplified - use Redis in production)
    request.session["passkey_challenge"] = bytes_to_base64url(options.challenge)
    
    # Convert to JSON-serializable format
    return json.loads(options_to_json(options))


@router.post("/register/complete", response_model=PasskeyResponse)
async def complete_registration(
    registration_data: RegistrationCompleteRequest,
    request: Request,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Complete passkey registration"""
    # Try to get challenge from request body first (for proxy/CORS scenarios)
    # Fall back to session if not provided
    expected_challenge = registration_data.challenge if hasattr(registration_data, 'challenge') and registration_data.challenge else None
    
    if not expected_challenge:
        # Fall back to session
        expected_challenge = request.session.get("passkey_challenge")
    
    if not expected_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration session expired or challenge not provided"
        )
    
    # Verify registration
    try:
        # Decode challenge from base64url format (WebAuthn standard)
        if isinstance(expected_challenge, str):
            expected_challenge_bytes = base64url_to_bytes(expected_challenge)
        else:
            expected_challenge_bytes = expected_challenge
            
        # Convert Pydantic model to dict for webauthn library
        credential_dict = registration_data.response.dict(by_alias=True)
        
        verification = verify_registration_response(
            credential=credential_dict,
            expected_challenge=expected_challenge_bytes,
            expected_origin=config.passkey_origin,
            expected_rp_id=config.passkey_rp_id
        )
        
        if not verification.verified:
            raise ValueError("Verification failed")
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration verification failed: {str(e)}"
        )
    
    # Save credential
    credential = UserCredential(
        user_id=current_user.id,
        credential_id=base64.b64encode(verification.credential_id).decode(),
        public_key=base64.b64encode(verification.credential_public_key).decode(),
        sign_count=verification.sign_count,
        name=registration_data.name,
        authenticator_type="platform" if registration_data.response.authenticatorAttachment == "platform" else "cross-platform",
        is_discoverable=True  # Modern passkeys are discoverable
    )
    
    db.add(credential)
    db.commit()
    db.refresh(credential)
    
    # Clear challenge
    request.session.pop("passkey_challenge", None)
    
    # Emit event
    await auth_events.emit("passkey_registered", {
        "user_id": str(current_user.id),
        "passkey_id": str(credential.id)
    })
    
    return credential


@router.post("/authenticate/begin", response_model=AuthenticationOptionsResponse)
async def begin_authentication(
    auth_data: AuthenticationBeginRequest,
    request: Request,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Begin passkey authentication"""
    allow_credentials = []
    
    if auth_data.email:
        # Find user by email
        User = config.user_model
        user = db.query(User).filter(
            User.email == auth_data.email
        ).first()
        
        if user:
            # Get user's credentials
            credentials = db.query(UserCredential).filter(
                UserCredential.user_id == user.id
            ).all()
            
            for cred in credentials:
                allow_credentials.append(
                    PublicKeyCredentialDescriptor(
                        id=base64.urlsafe_b64decode(cred.credential_id + "=="),
                        transports=[AuthenticatorTransport.INTERNAL, AuthenticatorTransport.USB]
                    )
                )
    
    # Generate authentication options
    options = generate_authentication_options(
        rp_id=config.passkey_rp_id,
        allow_credentials=allow_credentials if allow_credentials else None,
        user_verification=UserVerificationRequirement.PREFERRED,
        timeout=config.passkey_timeout_ms
    )
    
    # Store challenge
    request.session["auth_challenge"] = bytes_to_base64url(options.challenge)
    
    return json.loads(options_to_json(options))


@router.post("/authenticate/complete", response_model=LoginResponse)
async def complete_authentication(
    auth_data: AuthenticationCompleteRequest,
    request: Request,
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Complete passkey authentication"""
    # Try to get challenge from request body first (for proxy/CORS scenarios)
    # Fall back to session if not provided
    expected_challenge = auth_data.challenge if hasattr(auth_data, 'challenge') and auth_data.challenge else None
    
    if not expected_challenge:
        # Fall back to session
        expected_challenge = request.session.get("auth_challenge")
    
    if not expected_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication session expired or challenge not provided"
        )
    
    # Find credential
    credential_id = auth_data.response.id
    credential = db.query(UserCredential).filter(
        UserCredential.credential_id == credential_id
    ).first()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential not found"
        )
    
    # Get user
    User = config.user_model
    user = db.query(User).filter(
        User.id == credential.user_id
    ).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Verify authentication
    try:
        # Decode challenge from base64url format (WebAuthn standard)
        if isinstance(expected_challenge, str):
            expected_challenge_bytes = base64url_to_bytes(expected_challenge)
        else:
            expected_challenge_bytes = expected_challenge
            
        # Convert Pydantic model to dict for webauthn library
        credential_dict = auth_data.response.dict(by_alias=True)
        
        verification = verify_authentication_response(
            credential=credential_dict,
            expected_challenge=expected_challenge_bytes,
            expected_origin=config.passkey_origin,
            expected_rp_id=config.passkey_rp_id,
            credential_public_key=base64.b64decode(credential.public_key),
            credential_current_sign_count=credential.sign_count
        )
        
        if not verification.verified:
            raise ValueError("Verification failed")
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication verification failed: {str(e)}"
        )
    
    # Update credential usage
    credential.update_usage(verification.new_sign_count)
    
    # Create tokens
    from datetime import timedelta, datetime, timezone
    
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
    
    # Clear challenge
    request.session.pop("auth_challenge", None)
    
    # Emit event
    await auth_events.emit("passkey_authenticated", {
        "user_id": str(user.id),
        "passkey_id": str(credential.id)
    })
    
    return LoginResponse(
        user=user,
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds())
        )
    )


@router.delete("/{passkey_id}", response_model=MessageResponse)
async def delete_passkey(
    passkey_id: UUID,
    current_user: Annotated[BaseUser, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Delete a passkey"""
    # Find passkey
    passkey = db.query(UserCredential).filter(
        UserCredential.id == passkey_id,
        UserCredential.user_id == current_user.id
    ).first()
    
    if not passkey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passkey not found"
        )
    
    # Check if user has other auth methods
    passkey_count = db.query(UserCredential).filter(
        UserCredential.user_id == current_user.id
    ).count()
    
    if passkey_count == 1 and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete last authentication method"
        )
    
    # Delete passkey
    db.delete(passkey)
    db.commit()
    
    # Emit event
    await auth_events.emit("passkey_deleted", {
        "user_id": str(current_user.id),
        "passkey_id": str(passkey_id)
    })
    
    return MessageResponse(message="Passkey deleted successfully")