"""
OAuth schemas for request/response validation.

Defines Pydantic models for OAuth endpoints including:
- Provider listing
- Authorization initiation
- Callback handling
- Account linking/unlinking
"""

from datetime import datetime
from typing import Optional, List, Literal
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


# Provider schemas
class OAuthProviderInfo(BaseModel):
    """Information about an OAuth provider."""
    name: str = Field(..., description="Provider identifier (google, github, apple)")
    display_name: str = Field(..., description="Human-readable provider name")
    enabled: bool = Field(True, description="Whether the provider is enabled")


class OAuthProvidersResponse(BaseModel):
    """Response for GET /auth/oauth/providers."""
    providers: List[str] = Field(..., description="List of enabled provider names")


# Authorization schemas
class OAuthAuthorizeRequest(BaseModel):
    """Request for POST /auth/oauth/{provider}/authorize."""
    redirect_uri: str = Field(
        ...,
        description="URI to redirect after authorization"
    )
    code_challenge: str = Field(
        ...,
        min_length=43,
        max_length=128,
        description="PKCE code challenge (base64url encoded SHA256 of verifier)"
    )
    code_challenge_method: Literal["S256"] = Field(
        "S256",
        description="PKCE challenge method (only S256 supported)"
    )
    mode: Literal["login", "link"] = Field(
        "login",
        description="OAuth mode: 'login' for authentication, 'link' for account linking"
    )
    scope: Optional[str] = Field(
        None,
        description="Optional scope override for the OAuth request"
    )


class OAuthAuthorizeResponse(BaseModel):
    """Response for POST /auth/oauth/{provider}/authorize."""
    provider: str = Field(..., description="Provider name")
    authorization_url: str = Field(..., description="URL to redirect user to")
    state: str = Field(..., description="State token for CSRF protection")


# Callback schemas
class OAuthCallbackRequest(BaseModel):
    """Request for POST /auth/oauth/{provider}/callback."""
    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State token from authorize response")
    redirect_uri: str = Field(
        ...,
        description="Must match the redirect_uri used in authorize"
    )
    code_verifier: str = Field(
        ...,
        min_length=43,
        max_length=128,
        description="PKCE code verifier (original random string)"
    )


# Link schemas
class OAuthLinkRequest(BaseModel):
    """Request for POST /auth/oauth/links/{provider}/link."""
    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State token from authorize response")
    redirect_uri: str = Field(
        ...,
        description="Must match the redirect_uri used in authorize"
    )
    code_verifier: str = Field(
        ...,
        min_length=43,
        max_length=128,
        description="PKCE code verifier"
    )


class LinkedAccountInfo(BaseModel):
    """Information about a linked social account."""
    id: UUID = Field(..., description="Social account ID")
    provider: str = Field(..., description="Provider name")
    provider_email: Optional[str] = Field(None, description="Email from provider")
    provider_username: Optional[str] = Field(None, description="Username from provider")
    created_at: datetime = Field(..., description="When the account was linked")

    class Config:
        from_attributes = True


class OAuthLinksResponse(BaseModel):
    """Response for GET /auth/oauth/links."""
    links: List[LinkedAccountInfo] = Field(
        ...,
        description="List of linked social accounts"
    )


class OAuthLinkSuccessResponse(BaseModel):
    """Response for successful account linking."""
    success: bool = True
    provider: str = Field(..., description="Provider that was linked")
    message: str = Field(
        "Social account linked successfully",
        description="Success message"
    )


class OAuthUnlinkSuccessResponse(BaseModel):
    """Response for successful account unlinking."""
    success: bool = True
    provider: str = Field(..., description="Provider that was unlinked")
    message: str = Field(
        "Social account unlinked successfully",
        description="Success message"
    )


# Error schemas
class OAuthErrorResponse(BaseModel):
    """OAuth error response."""
    error: str = Field(..., description="Error code")
    error_description: Optional[str] = Field(None, description="Error description")
    provider: Optional[str] = Field(None, description="Provider if applicable")
