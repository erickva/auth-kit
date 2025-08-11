# Email Verification Guide

This guide covers implementing email verification in your Auth Kit application.

## Quick Setup with CLI

If you're creating a new project, the CLI can set up email verification automatically:

```bash
# During project creation, select "Email verification" when prompted
npx @auth-kit/cli create my-app

# Or add email verification to existing project
npx @auth-kit/cli add email
```

The CLI will:
- Configure backend email verification endpoints
- Set up SMTP configuration in environment files
- Create verification page components
- Add email verification routes

## Overview

Email verification ensures that users own the email addresses they register with. This guide covers:
- Enabling email verification
- Customizing verification emails
- Handling verification flows
- Best practices

## Prerequisites

- Auth Kit configured with email support
- SMTP server or email service configured
- Frontend and backend properly connected

## Backend Configuration

### 1. Enable Email Verification

Configure your backend to require email verification:

```python
from auth_kit_fastapi import AuthConfig

config = AuthConfig(
    jwt_secret="your-secret-key",
    features={
        "email_verification": True,
        "registration": True,
    },
    # Email configuration
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_username="your-email@gmail.com",
    smtp_password="your-app-password",
    email_from="My App <noreply@myapp.com>",
    
    # Verification settings
    email_verification_expire_hours=24,  # Link expires in 24 hours
    require_email_verification=True,     # Block login until verified
)
```

### 2. Email Service Setup

The email service is automatically configured when you enable email verification. You can customize it:

```python
# auth_kit_fastapi/services/email_service.py customization
from auth_kit_fastapi.services import EmailService

class CustomEmailService(EmailService):
    async def send_verification_email(self, email: str, token: str):
        verification_url = f"{self.config.app_url}/verify-email?token={token}"
        
        html_content = f"""
        <h2>Verify Your Email</h2>
        <p>Thanks for signing up! Please verify your email address by clicking the link below:</p>
        <a href="{verification_url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
            Verify Email
        </a>
        <p>Or copy this link: {verification_url}</p>
        <p>This link will expire in 24 hours.</p>
        """
        
        await self.send_email(
            to=email,
            subject="Verify your email address",
            html_content=html_content
        )
```

### 3. API Endpoints

Auth Kit provides these email verification endpoints:

```python
# Automatically included when email verification is enabled

# Send verification email
POST /api/auth/verify-email/send
Headers: Authorization: Bearer <token>

# Verify email with token
POST /api/auth/verify-email/confirm
Body: { "token": "verification-token" }

# Check verification status
GET /api/auth/verify-email/status
Headers: Authorization: Bearer <token>
```

## Frontend Implementation

### 1. Registration with Email Verification

Update your registration flow to handle email verification:

```tsx
import { useAuth, useEmailVerification } from '@auth-kit/react'
import { useState } from 'react'

function RegistrationFlow() {
  const { register } = useAuth()
  const { resendVerificationEmail } = useEmailVerification()
  const [showVerificationMessage, setShowVerificationMessage] = useState(false)
  const [email, setEmail] = useState('')

  const handleRegister = async (data: RegisterData) => {
    try {
      await register(data)
      setEmail(data.email)
      setShowVerificationMessage(true)
    } catch (error) {
      console.error('Registration failed:', error)
    }
  }

  if (showVerificationMessage) {
    return (
      <div className="verification-message">
        <h2>Check Your Email</h2>
        <p>We've sent a verification link to {email}</p>
        <p>Please check your email and click the link to verify your account.</p>
        <button onClick={() => resendVerificationEmail()}>
          Resend Verification Email
        </button>
      </div>
    )
  }

  return <RegistrationForm onSubmit={handleRegister} />
}
```

### 2. Email Verification Page

Create a verification page using the CLI:

```bash
# Generate email verification page
npx @auth-kit/cli generate page verify-email
```

Or create it manually:

```tsx
import { useEmailVerification } from '@auth-kit/react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

function VerifyEmailPage() {
  const { verifyEmail } = useEmailVerification()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    
    if (!token) {
      setStatus('error')
      setError('No verification token provided')
      return
    }

    verifyEmail(token)
      .then(() => {
        setStatus('success')
        setTimeout(() => navigate('/login'), 3000)
      })
      .catch((err) => {
        setStatus('error')
        setError(err.message || 'Verification failed')
      })
  }, [searchParams, verifyEmail, navigate])

  return (
    <div className="verify-email-page">
      {status === 'verifying' && (
        <div>
          <h2>Verifying Your Email...</h2>
          <p>Please wait while we verify your email address.</p>
        </div>
      )}
      
      {status === 'success' && (
        <div>
          <h2>Email Verified! ✓</h2>
          <p>Your email has been successfully verified.</p>
          <p>Redirecting to login...</p>
        </div>
      )}
      
      {status === 'error' && (
        <div>
          <h2>Verification Failed</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/resend-verification')}>
            Request New Verification Email
          </button>
        </div>
      )}
    </div>
  )
}
```

### 3. Resend Verification Email

Allow users to request a new verification email:

```tsx
import { useEmailVerification } from '@auth-kit/react'
import { useState } from 'react'

function ResendVerificationPage() {
  const { resendVerificationEmail, isSending } = useEmailVerification()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setMessage(null)

    try {
      await resendVerificationEmail(email)
      setMessage('Verification email sent! Please check your inbox.')
    } catch (err) {
      setError(err.message || 'Failed to send verification email')
    }
  }

  return (
    <form onSubmit={handleResend}>
      <h2>Resend Verification Email</h2>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Enter your email"
        required
        disabled={isSending}
      />
      <button type="submit" disabled={isSending}>
        {isSending ? 'Sending...' : 'Resend Email'}
      </button>
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}
    </form>
  )
}
```

### 4. Block Unverified Users

Prevent unverified users from accessing protected content:

```tsx
import { useAuth } from '@auth-kit/react'
import { Navigate } from 'react-router-dom'

function ProtectedPage() {
  const { user, isAuthenticated } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" />
  }

  if (!user?.emailVerified) {
    return (
      <div className="unverified-warning">
        <h2>Email Verification Required</h2>
        <p>Please verify your email address to access this content.</p>
        <ResendVerificationButton />
      </div>
    )
  }

  return <div>Protected content here</div>
}
```

## Customization

### Email Templates

Create custom email templates:

```python
# backend/templates/emails/verification.html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #007bff; 
                  color: white; text-decoration: none; border-radius: 5px; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to {{ app_name }}!</h1>
        <p>Hi {{ user_name }},</p>
        <p>Thanks for signing up! Please verify your email address by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{{ verification_url }}" class="button">Verify Email Address</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all;">{{ verification_url }}</p>
        <p>This link will expire in {{ expire_hours }} hours.</p>
        <div class="footer">
            <p>If you didn't create an account with {{ app_name }}, you can safely ignore this email.</p>
        </div>
    </div>
</body>
</html>
```

Use the template in your email service:

```python
from jinja2 import Template

async def send_verification_email(self, user: User, token: str):
    with open("templates/emails/verification.html") as f:
        template = Template(f.read())
    
    html_content = template.render(
        app_name=self.config.app_name,
        user_name=user.first_name or user.email,
        verification_url=f"{self.config.app_url}/verify-email?token={token}",
        expire_hours=self.config.email_verification_expire_hours
    )
    
    await self.send_email(
        to=user.email,
        subject=f"Verify your {self.config.app_name} account",
        html_content=html_content
    )
```

### Verification Settings

Configure verification behavior:

```python
config = AuthConfig(
    # ... other settings ...
    
    # Verification behavior
    require_email_verification=True,      # Block login until verified
    allow_unverified_login=False,         # Alternative: allow login but limit features
    email_verification_expire_hours=24,   # Token expiration
    max_verification_attempts=3,          # Prevent brute force
    verification_cooldown_minutes=5,      # Rate limiting
)
```

## Best Practices

### 1. User Experience

- **Clear messaging**: Tell users to check their email immediately after registration
- **Resend option**: Always provide a way to resend the verification email
- **Check spam folder**: Remind users to check their spam folder
- **Progress indicators**: Show loading states during verification

### 2. Security

- **Token expiration**: Use reasonable expiration times (24-48 hours)
- **One-time tokens**: Invalidate tokens after use
- **Rate limiting**: Prevent abuse of resend functionality
- **Secure tokens**: Use cryptographically secure random tokens

### 3. Email Delivery

- **SPF/DKIM**: Configure email authentication to improve deliverability
- **From address**: Use a recognizable from address
- **Subject line**: Make it clear this is a verification email
- **Plain text fallback**: Include a plain text version

### 4. Error Handling

Handle common scenarios gracefully:

```tsx
function VerificationErrorHandler({ error }: { error: Error }) {
  switch (error.code) {
    case 'TOKEN_EXPIRED':
      return (
        <div>
          <p>This verification link has expired.</p>
          <ResendVerificationButton />
        </div>
      )
    
    case 'TOKEN_INVALID':
      return <p>This verification link is invalid.</p>
    
    case 'ALREADY_VERIFIED':
      return (
        <div>
          <p>Your email is already verified!</p>
          <Link to="/login">Go to Login</Link>
        </div>
      )
    
    default:
      return <p>An error occurred during verification.</p>
  }
}
```

## Testing Email Verification

### Development Environment

Use a test email service for development:

1. **MailHog**: Local SMTP testing server
   ```bash
   docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
   ```
   Configuration:
   ```python
   smtp_host="localhost"
   smtp_port=1025
   smtp_use_tls=False
   ```

2. **Mailtrap**: Cloud-based email testing
   ```python
   smtp_host="smtp.mailtrap.io"
   smtp_port=2525
   smtp_username="your-mailtrap-username"
   smtp_password="your-mailtrap-password"
   ```

### Test Scenarios

1. **Happy path**: User registers → receives email → clicks link → verified
2. **Expired token**: Wait for token to expire → click link → show error
3. **Already verified**: Click verification link twice
4. **Invalid token**: Modify token in URL → show error
5. **Resend flow**: Request new email → verify old link fails
6. **Rate limiting**: Repeatedly request verification emails

### Unit Tests

```python
# Test email verification
async def test_email_verification(client, db):
    # Register user
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    
    # Check user is unverified
    user = db.query(User).filter(User.email == "test@example.com").first()
    assert not user.email_verified
    
    # Generate verification token
    token = generate_email_verification_token(user.id)
    
    # Verify email
    response = await client.post("/api/auth/verify-email/confirm", json={
        "token": token
    })
    assert response.status_code == 200
    
    # Check user is verified
    db.refresh(user)
    assert user.email_verified
```

## Troubleshooting

### Common Issues

**Emails not being sent**
- Check SMTP configuration
- Verify credentials
- Check firewall/port blocking
- Look for errors in logs

**Emails going to spam**
- Configure SPF/DKIM records
- Use a reputable email service
- Avoid spam trigger words
- Include unsubscribe option

**Verification links not working**
- Check APP_URL configuration
- Ensure frontend route exists
- Verify token generation/validation

**Token expiration issues**
- Check server time synchronization
- Verify expiration settings
- Consider user's timezone

## Next Steps

- Implement [Password Reset](./password-reset.md)
- Add [Two-Factor Authentication](./two-factor.md)
- Configure [Custom User Models](./custom-users.md)