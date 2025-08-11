"""
Passkey/WebAuthn schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class PasskeyBase(BaseModel):
    """Base passkey schema"""
    name: str = Field(..., min_length=3, max_length=255)


class PasskeyCreate(PasskeyBase):
    """Passkey registration request"""
    pass


class PasskeyResponse(PasskeyBase):
    """Passkey response"""
    id: UUID
    credential_id: str
    authenticator_type: str
    is_discoverable: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PasskeyListResponse(BaseModel):
    """List of user's passkeys"""
    passkeys: List[PasskeyResponse]
    total: int


# WebAuthn schemas
class PublicKeyCredentialRpEntity(BaseModel):
    """Relying Party entity"""
    id: str
    name: str


class PublicKeyCredentialUserEntity(BaseModel):
    """User entity"""
    id: str
    name: str
    displayName: str


class PublicKeyCredentialParameters(BaseModel):
    """Credential parameters"""
    type: str = "public-key"
    alg: int


class PublicKeyCredentialDescriptor(BaseModel):
    """Credential descriptor"""
    type: str = "public-key"
    id: str
    transports: Optional[List[str]] = None


class AuthenticatorSelectionCriteria(BaseModel):
    """Authenticator selection criteria"""
    authenticatorAttachment: Optional[str] = None
    residentKey: Optional[str] = None
    userVerification: Optional[str] = "preferred"


class RegistrationOptionsResponse(BaseModel):
    """WebAuthn registration options"""
    challenge: str
    rp: PublicKeyCredentialRpEntity
    user: PublicKeyCredentialUserEntity
    pubKeyCredParams: List[PublicKeyCredentialParameters]
    timeout: Optional[int] = 60000
    excludeCredentials: Optional[List[PublicKeyCredentialDescriptor]] = []
    authenticatorSelection: Optional[AuthenticatorSelectionCriteria] = None
    attestation: Optional[str] = "none"


class RegistrationCredentialResponse(BaseModel):
    """Registration credential from client"""
    id: str
    rawId: str
    type: str = "public-key"
    response: Dict[str, Any]
    clientExtensionResults: Optional[Dict[str, Any]] = None
    authenticatorAttachment: Optional[str] = None


class RegistrationCompleteRequest(BaseModel):
    """Complete registration request"""
    name: str
    response: RegistrationCredentialResponse
    challenge: str


class AuthenticationOptionsResponse(BaseModel):
    """WebAuthn authentication options"""
    challenge: str
    timeout: Optional[int] = 60000
    rpId: Optional[str] = None
    allowCredentials: Optional[List[PublicKeyCredentialDescriptor]] = []
    userVerification: Optional[str] = "preferred"


class AuthenticationCredentialResponse(BaseModel):
    """Authentication credential from client"""
    id: str
    rawId: str
    type: str = "public-key"
    response: Dict[str, Any]
    clientExtensionResults: Optional[Dict[str, Any]] = None


class AuthenticationCompleteRequest(BaseModel):
    """Complete authentication request"""
    response: AuthenticationCredentialResponse
    challenge: str


class AuthenticationBeginRequest(BaseModel):
    """Begin authentication request"""
    email: Optional[str] = None  # For discoverable credentials