"""
Configuration for Auth Kit FastAPI
"""

import base64
from typing import Dict, Any, Optional, List, Type
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class AuthConfig(BaseSettings):
    """Authentication configuration"""

    # User Model
    user_model: Optional[Type[Any]] = Field(None, description="Concrete User model class")
    
    # Database
    database_url: str = Field(..., description="Database connection URL")
    database_echo: bool = Field(False, description="Echo SQL statements")
    
    # JWT Settings
    jwt_secret: str = Field(..., description="Secret key for JWT encoding")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(7, description="Refresh token expiration in days")
    
    # Passkey Settings
    passkey_rp_id: str = Field("localhost", description="Relying Party ID for WebAuthn")
    passkey_rp_name: str = Field("Auth Kit", description="Relying Party Name for WebAuthn")
    passkey_origin: str = Field("http://localhost:3000", description="Origin for WebAuthn")
    passkey_timeout_ms: int = Field(60000, description="WebAuthn timeout in milliseconds")
    
    # Email Settings
    email_from: Optional[str] = Field(None, description="From email address")
    email_from_name: Optional[str] = Field("Auth Kit", description="From name")
    smtp_host: Optional[str] = Field(None, description="SMTP server host")
    smtp_port: Optional[int] = Field(587, description="SMTP server port")
    smtp_user: Optional[str] = Field(None, description="SMTP username")
    smtp_password: Optional[str] = Field(None, description="SMTP password")
    smtp_tls: bool = Field(True, description="Use TLS for SMTP")
    
    # Security Settings
    bcrypt_rounds: int = Field(12, description="Bcrypt hashing rounds")
    password_min_length: int = Field(8, description="Minimum password length")
    password_require_uppercase: bool = Field(True, description="Require uppercase in password")
    password_require_lowercase: bool = Field(True, description="Require lowercase in password")
    password_require_numbers: bool = Field(True, description="Require numbers in password")
    password_require_special: bool = Field(True, description="Require special characters in password")
    
    # 2FA Settings
    totp_issuer: str = Field("Auth Kit", description="TOTP issuer name")
    totp_digits: int = Field(6, description="TOTP code length")
    totp_period: int = Field(30, description="TOTP period in seconds")
    totp_window: int = Field(1, description="TOTP validation window")
    recovery_codes_count: int = Field(10, description="Number of recovery codes to generate")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")
    rate_limit_requests: int = Field(10, description="Max requests per window")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")
    
    # Features
    features: Dict[str, Any] = Field(
        default_factory=lambda: {
            "passkeys": True,
            "two_factor": True,
            "email_verification": True,
            "social_login": []
        },
        description="Feature flags"
    )
    
    # CORS Settings
    cors_origins: List[str] = Field(
        ["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(True, description="Allow credentials in CORS")
    
    # Session Settings
    session_lifetime_seconds: int = Field(86400, description="Session lifetime in seconds")

    # OAuth Token Encryption
    oauth_token_encryption_key: Optional[str] = Field(
        None,
        description="Base64-encoded 32-byte key for OAuth token encryption (AES-256-GCM)"
    )

    # OAuth State Signing
    oauth_state_signing_key: Optional[str] = Field(
        None,
        description="Key for signing OAuth state JWTs. Falls back to jwt_secret if not set."
    )
    oauth_state_expiry_seconds: int = Field(
        600,
        description="OAuth state JWT expiration in seconds (default: 10 minutes)"
    )

    # Google OAuth
    oauth_google_client_id: Optional[str] = Field(None, description="Google OAuth Client ID")
    oauth_google_client_secret: Optional[str] = Field(None, description="Google OAuth Client Secret")

    # GitHub OAuth
    oauth_github_client_id: Optional[str] = Field(None, description="GitHub OAuth Client ID")
    oauth_github_client_secret: Optional[str] = Field(None, description="GitHub OAuth Client Secret")

    # Apple OAuth
    oauth_apple_client_id: Optional[str] = Field(None, description="Apple OAuth Client ID (Service ID)")
    oauth_apple_team_id: Optional[str] = Field(None, description="Apple Team ID")
    oauth_apple_key_id: Optional[str] = Field(None, description="Apple Key ID")
    oauth_apple_private_key: Optional[str] = Field(
        None,
        description="Apple Private Key (PEM format, newlines as \\n)"
    )

    @validator("user_model")
    def validate_user_model(cls, v):
        """Validate that user_model is provided and is a proper class"""
        if v is None:
            raise ValueError("user_model must be provided")
        return v
    
    @validator("features")
    def validate_features(cls, v):
        """Validate feature configuration"""
        valid_features = {
            "passkeys", "two_factor", "email_verification",
            "social_login", "rate_limiting", "audit_logs"
        }

        for key in v:
            if key not in valid_features:
                raise ValueError(f"Invalid feature: {key}")

        # Validate social login providers
        if "social_login" in v and isinstance(v["social_login"], list):
            valid_providers = {"google", "github", "apple"}
            for provider in v["social_login"]:
                if provider not in valid_providers:
                    raise ValueError(f"Invalid social login provider: {provider}. Valid: {valid_providers}")

        return v

    @validator("oauth_token_encryption_key")
    def validate_oauth_encryption_key(cls, v):
        """Validate OAuth token encryption key format (must be 32 bytes when base64 decoded)"""
        if v is None:
            return v
        try:
            key_bytes = base64.b64decode(v)
            if len(key_bytes) != 32:
                raise ValueError(
                    f"OAUTH_TOKEN_ENCRYPTION_KEY must decode to 32 bytes for AES-256-GCM, got {len(key_bytes)}"
                )
        except Exception as e:
            if "must decode to 32 bytes" in str(e):
                raise
            raise ValueError(f"OAUTH_TOKEN_ENCRYPTION_KEY must be valid base64: {e}")
        return v
    
    class Config:
        env_prefix = "AUTH_KIT_"
        case_sensitive = False
        
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.features.get(feature, False)
    
    def get_social_providers(self) -> List[str]:
        """Get enabled social login providers"""
        social = self.features.get("social_login", [])
        return social if isinstance(social, list) else []

    def _provider_has_credentials(self, provider: str) -> bool:
        """Check if required credentials are present for a provider."""
        if provider == "google":
            return bool(self.oauth_google_client_id and self.oauth_google_client_secret)
        if provider == "github":
            return bool(self.oauth_github_client_id and self.oauth_github_client_secret)
        if provider == "apple":
            return bool(
                self.oauth_apple_client_id
                and self.oauth_apple_team_id
                and self.oauth_apple_key_id
                and self.oauth_apple_private_key
            )
        return False

    def get_social_provider_info(self) -> List[Dict[str, Any]]:
        """Get provider info with display names and enabled status."""
        display_names = {
            "google": "Google",
            "github": "GitHub",
            "apple": "Apple",
        }
        enabled_providers = set(self.get_social_providers())
        providers = []
        for provider in ["google", "github", "apple"]:
            providers.append({
                "name": provider,
                "display_name": display_names.get(provider, provider.title()),
                "enabled": provider in enabled_providers and self._provider_has_credentials(provider),
            })
        return providers

    def validate_oauth_config(self) -> None:
        """
        Validate OAuth configuration at startup.
        Raises ValueError if social_login is enabled but required config is missing.
        """
        providers = self.get_social_providers()
        if not providers:
            return

        # Require encryption key when any provider is enabled
        if not self.oauth_token_encryption_key:
            raise ValueError(
                "OAUTH_TOKEN_ENCRYPTION_KEY is required when social_login providers are enabled"
            )

        # Validate provider-specific credentials
        for provider in providers:
            if provider == "google":
                if not self._provider_has_credentials("google"):
                    raise ValueError(
                        "OAUTH_GOOGLE_CLIENT_ID and OAUTH_GOOGLE_CLIENT_SECRET required for Google OAuth"
                    )
            elif provider == "github":
                if not self._provider_has_credentials("github"):
                    raise ValueError(
                        "OAUTH_GITHUB_CLIENT_ID and OAUTH_GITHUB_CLIENT_SECRET required for GitHub OAuth"
                    )
            elif provider == "apple":
                missing = []
                if not self.oauth_apple_client_id:
                    missing.append("OAUTH_APPLE_CLIENT_ID")
                if not self.oauth_apple_team_id:
                    missing.append("OAUTH_APPLE_TEAM_ID")
                if not self.oauth_apple_key_id:
                    missing.append("OAUTH_APPLE_KEY_ID")
                if not self.oauth_apple_private_key:
                    missing.append("OAUTH_APPLE_PRIVATE_KEY")
                if missing:
                    raise ValueError(f"Apple OAuth requires: {', '.join(missing)}")

    def get_oauth_state_signing_key(self) -> str:
        """Get the signing key for OAuth state JWTs. Falls back to jwt_secret."""
        return self.oauth_state_signing_key or self.jwt_secret

    def get_oauth_provider_credentials(self, provider: str) -> dict:
        """Get credentials for a specific OAuth provider"""
        if provider == "google":
            return {
                "client_id": self.oauth_google_client_id,
                "client_secret": self.oauth_google_client_secret,
            }
        elif provider == "github":
            return {
                "client_id": self.oauth_github_client_id,
                "client_secret": self.oauth_github_client_secret,
            }
        elif provider == "apple":
            return {
                "client_id": self.oauth_apple_client_id,
                "team_id": self.oauth_apple_team_id,
                "key_id": self.oauth_apple_key_id,
                "private_key": self.oauth_apple_private_key,
            }
        return {}
