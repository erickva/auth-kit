"""
Two-Factor Authentication schemas
"""

from typing import List, Optional
from pydantic import BaseModel, Field, validator


class TwoFactorSetupResponse(BaseModel):
    """2FA setup response"""
    secret: str
    qr_code: str  # Base64 encoded QR code image
    manual_entry_key: str
    message: str = "Scan the QR code with your authenticator app"


class TwoFactorVerifyRequest(BaseModel):
    """Verify 2FA code"""
    code: str = Field(..., pattern="^[0-9]{6}$")
    
    @validator('code')
    def validate_code(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('Code must be 6 digits')
        return v


class TwoFactorEnableResponse(BaseModel):
    """2FA enable response"""
    recovery_codes: List[str]
    message: str = "Two-factor authentication has been enabled"


class TwoFactorDisableRequest(BaseModel):
    """Disable 2FA request"""
    password: str


class RecoveryCodesRegenerateRequest(BaseModel):
    """Regenerate recovery codes request"""
    password: str


class RecoveryCodesResponse(BaseModel):
    """Recovery codes response"""
    recovery_codes: List[str]
    message: str = "New recovery codes have been generated"


class TwoFactorLoginVerifyRequest(BaseModel):
    """Verify 2FA during login"""
    # Define is_recovery_code before code so validator has access to it
    is_recovery_code: bool = False
    code: str

    @validator('code')
    def validate_code(cls, v, values):
        """Validate 2FA code depending on the flag.

        When using recovery codes, allow pattern XXXX-XXXX-XXXX-XXXX (alphanumeric)
        and skip the 6-digit check.
        """
        if values.get('is_recovery_code'):
            # Recovery code format: XXXX-XXXX-XXXX-XXXX (letters/digits)
            compact = v.replace('-', '')
            if not compact.isalnum() or len(compact) != 16:
                raise ValueError('Invalid recovery code format')
        else:
            # TOTP code: strictly 6 digits
            if not v.isdigit() or len(v) != 6:
                raise ValueError('Code must be 6 digits')
        return v


class TwoFactorStatusResponse(BaseModel):
    """2FA status response"""
    enabled: bool
    method: Optional[str] = None
    backup_codes_remaining: Optional[int] = None
    created_at: Optional[str] = None
