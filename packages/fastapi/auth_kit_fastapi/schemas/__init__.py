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
    "TwoFactorStatusResponse"
]