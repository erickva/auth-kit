"""
Export all schemas
"""

from .auth import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    LoginResponse,
    RefreshTokenRequest,
    LogoutRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    EmailVerificationRequest,
    MessageResponse,
    ErrorResponse
)

from .passkey import (
    PasskeyBase,
    PasskeyCreate,
    PasskeyResponse,
    PasskeyListResponse,
    RegistrationOptionsResponse,
    RegistrationCompleteRequest,
    AuthenticationOptionsResponse,
    AuthenticationCompleteRequest,
    AuthenticationBeginRequest
)

from .two_factor import (
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    TwoFactorEnableResponse,
    TwoFactorDisableRequest,
    RecoveryCodesRegenerateRequest,
    RecoveryCodesResponse,
    TwoFactorLoginVerifyRequest,
    TwoFactorStatusResponse
)

from .oauth import (
    OAuthProviderInfo,
    OAuthProvidersResponse,
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
    OAuthLinkRequest,
    LinkedAccountInfo,
    OAuthLinksResponse,
    OAuthLinkSuccessResponse,
    OAuthUnlinkSuccessResponse,
    OAuthErrorResponse,
)

__all__ = [
    # Auth schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "LoginRequest",
    "TokenResponse", 
    "LoginResponse",
    "RefreshTokenRequest",
    "LogoutRequest",
    "PasswordChangeRequest",
    "PasswordResetRequest",
    "PasswordResetConfirmRequest",
    "EmailVerificationRequest",
    "MessageResponse",
    "ErrorResponse",
    
    # Passkey schemas
    "PasskeyBase",
    "PasskeyCreate",
    "PasskeyResponse",
    "PasskeyListResponse",
    "RegistrationOptionsResponse",
    "RegistrationCompleteRequest",
    "AuthenticationOptionsResponse",
    "AuthenticationCompleteRequest",
    "AuthenticationBeginRequest",
    
    # 2FA schemas
    "TwoFactorSetupResponse",
    "TwoFactorVerifyRequest",
    "TwoFactorEnableResponse",
    "TwoFactorDisableRequest",
    "RecoveryCodesRegenerateRequest",
    "RecoveryCodesResponse",
    "TwoFactorLoginVerifyRequest",
    "TwoFactorStatusResponse",

    # OAuth schemas
    "OAuthProviderInfo",
    "OAuthProvidersResponse",
    "OAuthAuthorizeRequest",
    "OAuthAuthorizeResponse",
    "OAuthCallbackRequest",
    "OAuthLinkRequest",
    "LinkedAccountInfo",
    "OAuthLinksResponse",
    "OAuthLinkSuccessResponse",
    "OAuthUnlinkSuccessResponse",
    "OAuthErrorResponse",
]