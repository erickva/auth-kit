# Auth Kit FastAPI Backend Example

This example demonstrates how to create a FastAPI backend using `auth-kit-fastapi`.

## Features

- 🔐 Complete JWT authentication system
- 🔑 Passkey/WebAuthn support
- 📱 Two-factor authentication (TOTP)
- 📧 Email verification and password reset
- 🎯 Event-driven architecture
- 🛡️ Protected endpoints
- 🔄 Token refresh mechanism
- 📊 Session management

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL (optional, SQLite used by default)
- Redis (optional, for production)

### Installation

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the example environment file:

```bash
cp .env.example .env
```

4. Update `.env` with your configuration

5. Run database migrations (if using PostgreSQL):

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

6. Start the server:

```bash
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

Once running, you can access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

The application is configured through environment variables:

### Required Configuration

- `JWT_SECRET`: Secret key for JWT tokens (change in production!)
- `DATABASE_URL`: Database connection string

### Optional Configuration

- `SMTP_*`: Email server settings for sending emails
- `REDIS_URL`: Redis connection for caching (production)
- `CORS_ORIGINS`: Allowed CORS origins

### Feature Flags

Enable/disable features through environment variables:
- `ENABLE_EMAIL_VERIFICATION`: Require email verification
- `ENABLE_PASSWORD_RESET`: Allow password reset
- `ENABLE_2FA`: Enable two-factor authentication
- `ENABLE_PASSKEYS`: Enable passkey support

## Event System

The example demonstrates auth event handling:

```python
@auth_events.on("user_registered")
async def handle_user_registered(event):
    # Custom logic when user registers
    pass
```

Available events:
- `user_registered`
- `user_logged_in`
- `user_logged_out`
- `password_changed`
- `email_verified`
- `2fa_enabled`
- `passkey_registered`

## Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user

### Passkeys
- `GET /api/passkeys/` - List user passkeys
- `POST /api/passkeys/register/begin` - Start passkey registration
- `POST /api/passkeys/register/complete` - Complete passkey registration
- `POST /api/passkeys/authenticate/begin` - Start passkey authentication
- `POST /api/passkeys/authenticate/complete` - Complete passkey authentication
- `DELETE /api/passkeys/{id}` - Delete passkey

### Two-Factor Authentication
- `GET /api/2fa/status` - Get 2FA status
- `POST /api/2fa/setup/begin` - Start 2FA setup
- `POST /api/2fa/setup/verify` - Verify and enable 2FA
- `POST /api/2fa/disable` - Disable 2FA
- `POST /api/2fa/verify/login` - Verify 2FA during login

## Customization

### Custom User Model

Extend the base user model:

```python
from auth_kit_fastapi.models import BaseUser
from sqlalchemy import Column, String

class User(BaseUser):
    __tablename__ = "users"
    
    # Add custom fields
    company_name = Column(String(255))
    role = Column(String(50), default="user")
```

### Custom Endpoints

Add your own protected endpoints:

```python
@app.get("/api/users/{user_id}")
async def get_user(
    user_id: str,
    current_user: BaseUser = Depends(get_current_active_user)
):
    # Your logic here
    pass
```

## Production Deployment

1. **Database**: Use PostgreSQL instead of SQLite
2. **Redis**: Enable Redis for session/cache storage
3. **HTTPS**: Deploy behind HTTPS (required for passkeys)
4. **Secrets**: Use strong, unique secrets
5. **Email**: Configure real email server
6. **Monitoring**: Add logging and monitoring

## Docker Support

Build and run with Docker:

```bash
docker build -t auth-kit-backend .
docker run -p 8000:8000 --env-file .env auth-kit-backend
```

## Testing

Run tests:

```bash
pytest tests/
```

## Troubleshooting

### Common Issues

1. **CORS errors**: Check `CORS_ORIGINS` in `.env`
2. **Database errors**: Ensure database is running and migrations applied
3. **Email not sending**: Check SMTP configuration
4. **Passkeys not working**: Ensure HTTPS in production

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```