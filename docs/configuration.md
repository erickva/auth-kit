# Configuration Guide

Auth Kit provides flexible configuration options to customize authentication for your application's needs.

## Core Configuration

### React/Frontend Configuration

Configure the AuthProvider with these options:

```typescript
import { AuthProvider, StorageType } from '@auth-kit/react'

<AuthProvider
  config={{
    // Required
    apiUrl: 'https://api.example.com',
    
    // Storage configuration
    storageType: StorageType.LocalStorage, // or Cookies, SessionStorage, Memory
    storagePrefix: 'authkit_', // prefix for storage keys
    
    // Token configuration
    tokenRefreshThreshold: 300, // refresh token when < 5 minutes remain
    
    // Feature flags
    enablePasskeys: true,
    enable2FA: true,
    
    // URLs
    loginUrl: '/login',
    logoutUrl: '/logout',
    
    // Callbacks
    onAuthStateChange: (user, isAuthenticated) => {
      console.log('Auth state changed:', { user, isAuthenticated })
    },
  }}
>
  {children}
</AuthProvider>
```

### FastAPI/Backend Configuration

Configure the backend with AuthConfig:

```python
from auth_kit_fastapi import AuthConfig, init_auth

config = AuthConfig(
    # JWT Configuration (required)
    jwt_secret="your-secret-key",  # Use strong secret in production
    jwt_algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=30,
    
    # Passkey Configuration
    passkey_rp_id="example.com",  # Your domain
    passkey_rp_name="My App",
    passkey_origin="https://example.com",
    
    # Email Configuration
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_username="noreply@example.com",
    smtp_password="your-app-password",
    email_from="My App <noreply@example.com>",
    
    # Feature Configuration
    features={
        "registration": True,
        "login": True,
        "logout": True,
        "refresh_token": True,
        "password_reset": True,
        "email_verification": True,
        "two_factor": True,
        "passkeys": True,
    },
    
    # Security Configuration
    bcrypt_rounds=12,  # Password hashing rounds
    password_min_length=8,
    password_require_uppercase=True,
    password_require_numbers=True,
    password_require_special=False,
    
    # Session Configuration
    session_lifetime_seconds=86400,  # 24 hours
    max_sessions_per_user=5,
    
    # Rate Limiting
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window=3600,  # 1 hour
    
    # CORS Configuration
    cors_origins=["https://app.example.com"],
    cors_allow_credentials=True,
)

# Initialize with FastAPI app
init_auth(app, config, database_session_factory)
```

## Storage Options

### LocalStorage (Default)
Best for single-page applications:

```typescript
storageType: StorageType.LocalStorage
```

**Pros:**
- Simple to implement
- Persists across browser sessions
- Good performance

**Cons:**
- Not accessible server-side
- Vulnerable to XSS attacks
- Not shared across subdomains

### Cookies
Best for server-side rendering and enhanced security:

```typescript
storageType: StorageType.Cookies
```

**Pros:**
- Accessible server-side
- Can be httpOnly for security
- Works across subdomains
- Supports secure flag

**Cons:**
- Size limitations
- Sent with every request

### SessionStorage
Best for temporary authentication:

```typescript
storageType: StorageType.SessionStorage
```

**Pros:**
- Cleared when tab closes
- More secure for sensitive apps
- Not shared between tabs

**Cons:**
- Lost on page refresh in some cases
- Not persistent

### Memory
Best for testing or special use cases:

```typescript
storageType: StorageType.Memory
```

**Pros:**
- Most secure
- Fast
- No persistence

**Cons:**
- Lost on page refresh
- Not practical for most apps

## Feature Configuration

### Enable/Disable Features

Control which features are available:

```python
config = AuthConfig(
    jwt_secret="...",
    features={
        "registration": True,      # Allow new user registration
        "login": True,            # Allow login
        "logout": True,           # Allow logout
        "refresh_token": True,    # Enable token refresh
        "password_reset": True,   # Allow password reset
        "email_verification": True, # Require email verification
        "two_factor": False,      # Disable 2FA
        "passkeys": False,        # Disable passkeys
    }
)
```

### Password Requirements

Configure password complexity:

```python
config = AuthConfig(
    jwt_secret="...",
    password_min_length=12,
    password_require_uppercase=True,
    password_require_lowercase=True,
    password_require_numbers=True,
    password_require_special=True,
    password_special_chars="!@#$%^&*",
)
```

### Email Templates

Customize email templates:

```python
config = AuthConfig(
    jwt_secret="...",
    email_templates={
        "verification": {
            "subject": "Verify your email",
            "template": "emails/verification.html",
        },
        "password_reset": {
            "subject": "Reset your password",
            "template": "emails/password_reset.html",
        },
        "two_factor": {
            "subject": "Your 2FA code",
            "template": "emails/two_factor.html",
        },
    }
)
```

## Environment Variables

### Frontend Environment Variables

```env
# .env.local (Next.js) or .env (React)

# API Configuration
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_APP_URL=https://app.example.com

# Feature Flags
NEXT_PUBLIC_ENABLE_PASSKEYS=true
NEXT_PUBLIC_ENABLE_2FA=true
NEXT_PUBLIC_ENABLE_SOCIAL_LOGIN=false

# Analytics (optional)
NEXT_PUBLIC_GA_ID=UA-XXXXXXXXX
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
```

### Backend Environment Variables

```env
# .env

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/authkit
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Security
JWT_SECRET=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
BCRYPT_ROUNDS=12

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
EMAIL_VERIFICATION_EXPIRE_HOURS=24
PASSWORD_RESET_EXPIRE_HOURS=1

# Passkeys
PASSKEY_RP_ID=example.com
PASSKEY_RP_NAME=My App
PASSKEY_ORIGIN=https://example.com

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@example.com
SMTP_PASSWORD=app-specific-password
SMTP_USE_TLS=true
EMAIL_FROM=My App <noreply@example.com>

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600

# CORS
CORS_ORIGINS=https://app.example.com,https://www.example.com
CORS_ALLOW_CREDENTIALS=true

# Application
APP_NAME=My App
APP_URL=https://app.example.com
APP_ENV=production
DEBUG=false
```

## Advanced Configuration

### Custom User Model

Extend the base user model:

```python
from auth_kit_fastapi.models import BaseUser
from sqlalchemy import Column, String, DateTime

class User(BaseUser):
    __tablename__ = "users"
    
    # Add custom fields
    phone_number = Column(String(20))
    date_of_birth = Column(DateTime)
    subscription_tier = Column(String(50))
    
    # Custom methods
    def get_display_name(self):
        return self.first_name or self.email.split('@')[0]
```

### Custom Storage Adapter

Implement a custom storage adapter:

```typescript
import { StorageAdapter } from '@auth-kit/core'

class CustomStorageAdapter implements StorageAdapter {
  async getItem(key: string): Promise<string | null> {
    // Custom implementation
  }
  
  async setItem(key: string, value: string): Promise<void> {
    // Custom implementation
  }
  
  async removeItem(key: string): Promise<void> {
    // Custom implementation
  }
  
  async clear(): Promise<void> {
    // Custom implementation
  }
}

// Use in AuthProvider
<AuthProvider
  config={{
    apiUrl: '...',
    storageAdapter: new CustomStorageAdapter(),
  }}
>
```

### Event Handlers

Configure authentication event handlers:

```typescript
<AuthProvider
  config={{
    apiUrl: '...',
    onAuthStateChange: (user, isAuthenticated) => {
      // Track auth state changes
      analytics.track('auth_state_change', {
        isAuthenticated,
        userId: user?.id,
      })
    },
    onTokenRefresh: (newTokens) => {
      // Handle token refresh
      console.log('Tokens refreshed')
    },
    onSessionExpire: () => {
      // Handle session expiration
      showNotification('Session expired, please login again')
    },
  }}
>
```

### Multi-Environment Configuration

Use different configs for different environments:

```typescript
const getConfig = () => {
  const env = process.env.NODE_ENV
  
  const baseConfig = {
    apiUrl: process.env.NEXT_PUBLIC_API_URL!,
  }
  
  if (env === 'production') {
    return {
      ...baseConfig,
      storageType: StorageType.Cookies,
      tokenRefreshThreshold: 300,
    }
  }
  
  return {
    ...baseConfig,
    storageType: StorageType.LocalStorage,
    tokenRefreshThreshold: 60,
  }
}

<AuthProvider config={getConfig()}>
  {children}
</AuthProvider>
```

## Security Best Practices

### JWT Secret

Generate a strong JWT secret:

```bash
# Generate a 64-character secret
openssl rand -hex 32
```

### HTTPS Only

Always use HTTPS in production:

```python
config = AuthConfig(
    jwt_secret="...",
    # Force secure cookies
    cookie_secure=True,
    cookie_samesite="strict",
)
```

### Rate Limiting

Configure appropriate rate limits:

```python
config = AuthConfig(
    jwt_secret="...",
    rate_limit_enabled=True,
    rate_limit_requests=100,  # requests
    rate_limit_window=3600,   # per hour
    # Different limits for different endpoints
    rate_limits={
        "/auth/login": (5, 300),      # 5 requests per 5 minutes
        "/auth/register": (3, 3600),   # 3 requests per hour
        "/auth/password-reset": (3, 3600),
    }
)
```

### Session Security

Configure secure sessions:

```python
config = AuthConfig(
    jwt_secret="...",
    # Limit concurrent sessions
    max_sessions_per_user=3,
    # Short session lifetime
    session_lifetime_seconds=3600,  # 1 hour
    # Require re-authentication for sensitive operations
    require_reauthentication_after=1800,  # 30 minutes
)
```

## Monitoring and Logging

### Configure Logging

```python
import logging

config = AuthConfig(
    jwt_secret="...",
    # Set log level
    log_level=logging.INFO,
    # Log authentication events
    log_auth_events=True,
    # Mask sensitive data
    log_mask_sensitive=True,
)
```

### Metrics and Analytics

Track authentication metrics:

```python
config = AuthConfig(
    jwt_secret="...",
    # Enable metrics
    metrics_enabled=True,
    # Custom metrics handler
    metrics_handler=custom_metrics_handler,
)
```

## Next Steps

- Review [Security Best Practices](./concepts/security.md)
- Learn about [Multi-Tenancy](./guides/multi-tenancy.md)
- Explore [Advanced Topics](./advanced/deployment.md)