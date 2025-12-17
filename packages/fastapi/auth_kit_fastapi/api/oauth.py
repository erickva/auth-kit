"""
OAuth API endpoints for social authentication.

Provides endpoints for:
- GET /oauth/providers - List enabled OAuth providers
- POST /oauth/{provider}/authorize - Initiate OAuth flow
- POST /oauth/{provider}/callback - Complete OAuth login/signup
- GET /oauth/links - List linked social accounts
- POST /oauth/links/{provider}/link - Link a social account
- DELETE /oauth/links/{provider} - Unlink a social account
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..core.dependencies import get_current_user, get_current_active_user, get_config
from ..core.oauth_state import (
    create_state_for_authorize,
    verify_state_for_callback,
    OAuthStateError,
    OAuthStateExpiredError,
    OAuthStateInvalidError,
)
from ..core.crypto_oauth import encrypt_token
from ..core.security import create_access_token, create_refresh_token
from ..core.events import auth_events
from ..models.user import BaseUser
from ..models.social_account import SocialAccount
from ..services.oauth.providers import get_provider, get_available_providers
from ..services.oauth.providers.base import OAuthProviderError
from ..schemas.oauth import (
    OAuthProvidersResponse,
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
    OAuthLinkRequest,
    OAuthLinksResponse,
    LinkedAccountInfo,
    OAuthLinkSuccessResponse,
    OAuthUnlinkSuccessResponse,
    OAuthErrorResponse,
)
from ..schemas.auth import LoginResponse, UserResponse, TokenResponse

router = APIRouter()


@router.get("/providers", response_model=OAuthProvidersResponse)
async def get_providers(
    config=Depends(get_config),
):
    """
    Get list of enabled OAuth providers.

    Returns the providers configured for this application.
    """
    providers = config.get_social_providers()
    return OAuthProvidersResponse(providers=providers)


@router.post("/{provider}/authorize", response_model=OAuthAuthorizeResponse)
async def authorize(
    provider: str,
    request_data: OAuthAuthorizeRequest,
    request: Request,
    config=Depends(get_config),
    db: Session = Depends(get_db),
):
    """
    Initiate OAuth authorization flow.

    Generates a state token and returns the provider's authorization URL.
    The client should redirect the user to this URL.

    For link mode, the user must be authenticated (provide Authorization header).
    """
    # Validate provider is enabled
    enabled_providers = config.get_social_providers()
    if provider not in enabled_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' is not enabled",
        )

    # Validate PKCE method
    if request_data.code_challenge_method != "S256":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only S256 code_challenge_method is supported",
        )

    # For link mode, require authentication
    link_user_id = None
    if request_data.mode == "link":
        # Try to get current user from Authorization header
        from ..core.security import decode_token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required for account linking",
            )

        token = auth_header.split(" ")[1]
        try:
            payload = decode_token(token, config.jwt_secret, config.jwt_algorithm)
            link_user_id = payload.get("sub")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

    # Get provider instance
    try:
        oauth_provider = get_provider(provider, config=config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize OAuth provider: {str(e)}",
        )

    # Generate signed state token
    signing_key = config.get_oauth_state_signing_key()
    state = create_state_for_authorize(
        provider=provider,
        redirect_uri=request_data.redirect_uri,
        mode=request_data.mode,
        code_challenge=request_data.code_challenge,
        signing_key=signing_key,
        link_user_id=link_user_id,
        expiry_seconds=config.oauth_state_expiry_seconds,
    )

    # Build authorization URL
    authorization_url = oauth_provider.build_authorize_url(
        redirect_uri=request_data.redirect_uri,
        code_challenge=request_data.code_challenge,
        state=state,
        scope=request_data.scope,
    )

    return OAuthAuthorizeResponse(
        provider=provider,
        authorization_url=authorization_url,
        state=state,
    )


@router.post("/{provider}/callback", response_model=LoginResponse)
async def callback(
    provider: str,
    request_data: OAuthCallbackRequest,
    request: Request,
    db: Session = Depends(get_db),
    config=Depends(get_config),
):
    """
    Complete OAuth login/signup flow.

    Exchanges the authorization code for tokens, fetches user profile,
    and either logs in existing user or creates new account.

    Returns the same LoginResponse as password login for consistency.
    """
    # Validate provider is enabled
    enabled_providers = config.get_social_providers()
    if provider not in enabled_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' is not enabled",
        )

    # Verify state token
    signing_key = config.get_oauth_state_signing_key()
    try:
        state_payload = verify_state_for_callback(
            state=request_data.state,
            signing_key=signing_key,
            expected_provider=provider,
            expected_redirect_uri=request_data.redirect_uri,
        )
    except OAuthStateExpiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has expired. Please try again.",
        )
    except OAuthStateInvalidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OAuth state: {str(e)}",
        )
    except OAuthStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth state error: {str(e)}",
        )

    # Check mode - callback endpoint is for login only
    if state_payload.get("mode") == "link":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /oauth/links/{provider}/link endpoint for account linking",
        )

    # Get provider instance
    try:
        oauth_provider = get_provider(provider, config=config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize OAuth provider: {str(e)}",
        )

    # Exchange code for tokens and get profile
    try:
        tokens, profile = await oauth_provider.get_user_identity(
            code=request_data.code,
            code_verifier=request_data.code_verifier,
            redirect_uri=request_data.redirect_uri,
        )
    except OAuthProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider error: {str(e)}",
        )

    # Require email for MVP
    if not profile.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required but not provided by OAuth provider",
        )

    User = config.user_model

    # Look up existing social account
    social_account = db.query(SocialAccount).filter(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == profile.provider_user_id,
    ).first()

    user = None

    if social_account:
        # Existing social account - log in that user
        user = db.query(User).filter(User.id == social_account.user_id).first()
        if not user:
            # Orphaned social account - remove it
            db.delete(social_account)
            db.commit()
            social_account = None

    if not user:
        # Check if user exists with this email
        user = db.query(User).filter(User.email == profile.email).first()

        if user:
            # Link social account to existing user
            social_account = _create_social_account(
                db, user.id, provider, profile, tokens, config
            )
        else:
            # Create new user
            user = User(
                email=profile.email,
                first_name=profile.username,
                is_active=True,
                is_verified=True,  # Email verified by OAuth provider
                has_usable_password=False,  # Social-only user
                hashed_password="",  # No password
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Create social account
            social_account = _create_social_account(
                db, user.id, provider, profile, tokens, config
            )

            # Emit registration event
            await auth_events.emit("user_registered", {
                "user_id": str(user.id),
                "method": "oauth",
                "provider": provider,
            })

    # Update social account tokens if needed
    if social_account and tokens:
        _update_social_account_tokens(social_account, tokens, config)
        db.commit()

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Check if 2FA is required
    requires_2fa = getattr(user, "two_factor_enabled", False)
    token_type = "2fa_temp" if requires_2fa else "access"

    # Generate tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "type": token_type},
        secret_key=config.jwt_secret,
        algorithm=config.jwt_algorithm,
        expires_delta=timedelta(minutes=config.access_token_expire_minutes),
    )

    refresh_token = None
    if not requires_2fa:
        refresh_token, _ = create_refresh_token(
            data={"sub": str(user.id)},
            secret_key=config.jwt_secret,
            algorithm=config.jwt_algorithm,
            expires_delta=timedelta(days=config.refresh_token_expire_days),
        )

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

    # Emit login event
    await auth_events.emit("user_logged_in", {
        "user_id": str(user.id),
        "method": "oauth",
        "provider": provider,
    })

    return LoginResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=config.access_token_expire_minutes * 60,
        ),
        requires_2fa=requires_2fa,
    )


@router.get("/links", response_model=OAuthLinksResponse)
async def get_links(
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get list of linked social accounts for the current user.
    """
    social_accounts = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id
    ).all()

    links = [
        LinkedAccountInfo(
            id=sa.id,
            provider=sa.provider,
            provider_email=sa.provider_email,
            provider_username=sa.provider_username,
            created_at=sa.created_at,
        )
        for sa in social_accounts
    ]

    return OAuthLinksResponse(links=links)


@router.post("/links/{provider}/link", response_model=OAuthLinkSuccessResponse)
async def link_account(
    provider: str,
    request_data: OAuthLinkRequest,
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    config=Depends(get_config),
):
    """
    Link a social account to the current user.

    Exchanges the OAuth code and links the provider identity to this user.
    """
    # Validate provider is enabled
    enabled_providers = config.get_social_providers()
    if provider not in enabled_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' is not enabled",
        )

    # Verify state token
    signing_key = config.get_oauth_state_signing_key()
    try:
        state_payload = verify_state_for_callback(
            state=request_data.state,
            signing_key=signing_key,
            expected_provider=provider,
            expected_redirect_uri=request_data.redirect_uri,
        )
    except OAuthStateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth state error: {str(e)}",
        )

    # Verify this is a link-mode state for this user
    if state_payload.get("mode") != "link":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State was not created for account linking",
        )

    if state_payload.get("link_user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State was created for a different user",
        )

    # Check if user already has this provider linked
    existing = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.provider == provider,
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have a {provider} account linked",
        )

    # Get provider instance
    try:
        oauth_provider = get_provider(provider, config=config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize OAuth provider: {str(e)}",
        )

    # Exchange code for tokens and get profile
    try:
        tokens, profile = await oauth_provider.get_user_identity(
            code=request_data.code,
            code_verifier=request_data.code_verifier,
            redirect_uri=request_data.redirect_uri,
        )
    except OAuthProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider error: {str(e)}",
        )

    # Check if this provider identity is already linked to another user
    existing_link = db.query(SocialAccount).filter(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == profile.provider_user_id,
    ).first()

    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This {provider} account is already linked to another user",
        )

    # Create social account link
    try:
        _create_social_account(
            db, current_user.id, provider, profile, tokens, config
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This {provider} account is already linked",
        )

    # Emit link event
    await auth_events.emit("social_account_linked", {
        "user_id": str(current_user.id),
        "provider": provider,
    })

    return OAuthLinkSuccessResponse(provider=provider)


@router.delete("/links/{provider}", response_model=OAuthUnlinkSuccessResponse)
async def unlink_account(
    provider: str,
    current_user: BaseUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    config=Depends(get_config),
):
    """
    Unlink a social account from the current user.

    Prevents unlinking if it would leave the user with no way to log in.
    """
    # Find the social account
    social_account = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.provider == provider,
    ).first()

    if not social_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} account linked",
        )

    # Check lockout rules
    social_count = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id
    ).count()

    # Check passkeys count if available
    passkey_count = 0
    try:
        from ..models.user import UserCredential
        passkey_count = db.query(UserCredential).filter(
            UserCredential.user_id == current_user.id
        ).count()
    except Exception:
        pass  # Passkeys may not be enabled

    has_password = getattr(current_user, "has_usable_password", True)

    # After unlinking this one:
    remaining_social = social_count - 1
    remaining_auth_methods = remaining_social + passkey_count + (1 if has_password else 0)

    if remaining_auth_methods == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink last authentication method. "
                   "Please add a password or another login method first.",
        )

    # Delete the social account
    db.delete(social_account)
    db.commit()

    # Emit unlink event
    await auth_events.emit("social_account_unlinked", {
        "user_id": str(current_user.id),
        "provider": provider,
    })

    return OAuthUnlinkSuccessResponse(provider=provider)


def _create_social_account(
    db: Session,
    user_id: UUID,
    provider: str,
    profile,
    tokens,
    config,
) -> SocialAccount:
    """Create a new social account record with encrypted tokens."""
    encryption_key = config.oauth_token_encryption_key

    social_account = SocialAccount(
        user_id=user_id,
        provider=provider,
        provider_user_id=profile.provider_user_id,
        provider_email=profile.email,
        provider_username=profile.username,
        access_token_enc=encrypt_token(tokens.access_token, encryption_key) if tokens.access_token else None,
        refresh_token_enc=encrypt_token(tokens.refresh_token, encryption_key) if tokens.refresh_token else None,
        id_token_enc=encrypt_token(tokens.id_token, encryption_key) if tokens.id_token else None,
        token_type=tokens.token_type,
        scope=tokens.scope,
        expires_at=tokens.expires_at,
    )

    db.add(social_account)
    db.commit()
    db.refresh(social_account)

    return social_account


def _update_social_account_tokens(social_account: SocialAccount, tokens, config):
    """Update tokens on an existing social account."""
    encryption_key = config.oauth_token_encryption_key

    if tokens.access_token:
        social_account.access_token_enc = encrypt_token(tokens.access_token, encryption_key)
    if tokens.refresh_token:
        social_account.refresh_token_enc = encrypt_token(tokens.refresh_token, encryption_key)
    if tokens.id_token:
        social_account.id_token_enc = encrypt_token(tokens.id_token, encryption_key)
    if tokens.token_type:
        social_account.token_type = tokens.token_type
    if tokens.scope:
        social_account.scope = tokens.scope
    if tokens.expires_at:
        social_account.expires_at = tokens.expires_at

    social_account.updated_at = datetime.now(timezone.utc)
