# Auth Kit FastAPI

FastAPI authentication backend for Auth Kit. Provides a complete authentication solution with JWT tokens, passkeys, 2FA, and more.

## Installation

```bash
pip install auth-kit-fastapi
```

## Quick Start

```python
from fastapi import FastAPI
from auth_kit_fastapi import create_auth_app, AuthConfig

app = FastAPI()

# Configure authentication
auth_config = AuthConfig(
    database_url="postgresql://localhost/myapp",
    jwt_secret="your-secret-key",
    features={
        "passkeys": True,
        "two_factor": True,
        "email_verification": True
    }
)

# Create auth app
auth_app = create_auth_app(auth_config)

# Mount auth routes
app.mount("/api/auth", auth_app)
```

## Features

- 🔐 JWT-based authentication with refresh tokens
- 🔑 WebAuthn/Passkey support
- 🔒 Two-factor authentication (TOTP)
- 📧 Email verification
- 🔄 Password reset flow
- 👤 User management
- 🗄️ SQLAlchemy ORM support
- 🔍 Extensible user model
- 🛡️ Security best practices

## Configuration

```python
from auth_kit_fastapi import AuthConfig

config = AuthConfig(
    # Database
    database_url="postgresql://user:pass@localhost/db",
    
    # JWT Settings
    jwt_secret="your-secret-key",
    jwt_algorithm="HS256",
    access_token_expire_minutes=30,
    refresh_token_expire_days=7,
    
    # Passkey Settings
    passkey_rp_id="localhost",
    passkey_rp_name="My App",
    passkey_origin="http://localhost:3000",
    
    # Email Settings
    email_from="noreply@example.com",
    email_from_name="My App",
    
    # Features
    features={
        "passkeys": True,
        "two_factor": True,
        "email_verification": True,
        "social_login": ["google", "github"]
    }
)
```

## Custom User Model

Extend the base User model with your own fields:

```python
from auth_kit_fastapi import BaseUser
from sqlalchemy import Column, String

class User(BaseUser):
    __tablename__ = "users"
    
    # Add custom fields
    company_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
```

## API Endpoints

All endpoints are mounted under your chosen prefix (e.g., `/api/auth`):

### Authentication
- `POST /register` - Register new user
- `POST /login` - Login with email/password
- `POST /logout` - Logout user
- `POST /refresh` - Refresh access token
- `GET /me` - Get current user

### Password Management
- `POST /password/change` - Change password
- `POST /password/reset` - Request password reset
- `POST /password/reset/confirm` - Confirm password reset

### Email Verification
- `GET /verify-email/{token}` - Verify email
- `POST /resend-verification` - Resend verification email

### Passkeys
- `GET /passkeys` - List user's passkeys
- `POST /passkeys/register/begin` - Begin passkey registration
- `POST /passkeys/register/complete` - Complete passkey registration
- `POST /passkeys/authenticate/begin` - Begin passkey authentication
- `POST /passkeys/authenticate/complete` - Complete passkey authentication
- `DELETE /passkeys/{id}` - Delete passkey

### Two-Factor Authentication
- `POST /2fa/setup/begin` - Begin 2FA setup
- `POST /2fa/setup/verify` - Verify and enable 2FA
- `POST /2fa/disable` - Disable 2FA
- `POST /2fa/verify/login` - Verify 2FA during login
- `POST /2fa/recovery-codes` - Regenerate recovery codes

## Middleware & Dependencies

Use the provided dependencies to protect your routes:

```python
from fastapi import Depends
from auth_kit_fastapi import get_current_user, require_verified_user

@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"message": f"Hello {user.email}"}

@app.get("/verified-only")
async def verified_only(user = Depends(require_verified_user)):
    return {"message": "Only verified users can see this"}
```

## Events & Hooks

Subscribe to authentication events:

```python
from auth_kit_fastapi import auth_events

@auth_events.on("user_registered")
async def on_user_registered(user):
    # Send welcome email
    print(f"New user registered: {user.email}")

@auth_events.on("user_logged_in")
async def on_user_logged_in(user):
    # Log login event
    print(f"User logged in: {user.email}")
```

## License

MIT License