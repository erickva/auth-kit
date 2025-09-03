"""
Configuration for Auth Kit FastAPI
"""

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
            if key not in valid_features and key != "social_login":
                raise ValueError(f"Invalid feature: {key}")
        
        # Validate social login providers
        if "social_login" in v and isinstance(v["social_login"], list):
            valid_providers = {"google", "github", "facebook", "twitter", "microsoft"}
            for provider in v["social_login"]:
                if provider not in valid_providers:
                    raise ValueError(f"Invalid social login provider: {provider}")
        
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