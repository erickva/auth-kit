# Implementing Passkeys

Passkeys provide a passwordless authentication method using WebAuthn. This guide covers implementing passkeys in your application.

## Quick Setup with CLI

The easiest way to add passkey support is during project creation:

```bash
# Select "Passkeys (WebAuthn)" when prompted for features
npx @auth-kit/cli create my-app

# Or generate passkey components for existing projects
npx @auth-kit/cli generate component PasskeyButton
npx @auth-kit/cli generate component PasskeyManager
```

## What are Passkeys?

Passkeys are:
- Cryptographic key pairs stored on your device
- More secure than passwords (phishing-resistant)
- Easier to use (no passwords to remember)
- Supported by modern browsers and devices
- Based on WebAuthn/FIDO2 standards

## Prerequisites

### Browser Support
- Chrome 67+
- Firefox 60+
- Safari 14+
- Edge 18+

### Requirements
- HTTPS (required for WebAuthn)
- User verification capability (biometrics, PIN, etc.)

## Basic Implementation

### 1. Enable Passkeys in Configuration

**Backend:**
```python
from auth_kit_fastapi import AuthConfig

config = AuthConfig(
    jwt_secret="your-secret",
    passkey_rp_id="example.com",  # Your domain
    passkey_rp_name="My App",     # Display name
    passkey_origin="https://example.com",
    features={
        "passkeys": True
    }
)
```

**Frontend:**
```typescript
<AuthProvider
  config={{
    apiUrl: 'https://api.example.com',
    enablePasskeys: true,
  }}
>
```

### 2. Registration Flow

Add passkey registration to your registration form:

```tsx
import { usePasskey } from '@auth-kit/react'

function RegisterWithPasskey() {
  const { registerPasskey, isSupported, isRegistering } = usePasskey()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [usePasskey, setUsePasskey] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      // First register the user
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (!response.ok) throw new Error('Registration failed')
      
      // Then register passkey if requested
      if (usePasskey && isSupported) {
        await registerPasskey({
          displayName: email,
          requireUserVerification: true
        })
      }
      
      // Success!
      router.push('/dashboard')
    } catch (error) {
      console.error('Registration error:', error)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      
      {isSupported && (
        <label>
          <input
            type="checkbox"
            checked={usePasskey}
            onChange={(e) => setUsePasskey(e.target.checked)}
          />
          Enable passwordless login with passkey
        </label>
      )}
      
      <button type="submit" disabled={isRegistering}>
        {isRegistering ? 'Setting up passkey...' : 'Register'}
      </button>
    </form>
  )
}
```

### 3. Login with Passkey

Implement passkey login:

```tsx
import { useAuth, usePasskey } from '@auth-kit/react'

function LoginWithPasskey() {
  const { login } = useAuth()
  const { authenticateWithPasskey, isSupported, isAuthenticating } = usePasskey()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login({ email, password })
    } catch (err) {
      setError('Invalid credentials')
    }
  }

  const handlePasskeyLogin = async () => {
    try {
      await authenticateWithPasskey()
      // User is now logged in
    } catch (err) {
      setError('Passkey authentication failed')
    }
  }

  return (
    <div>
      {/* Passkey login button */}
      {isSupported && (
        <button
          onClick={handlePasskeyLogin}
          disabled={isAuthenticating}
          className="passkey-button"
        >
          {isAuthenticating ? 'Authenticating...' : 'Sign in with Passkey'}
        </button>
      )}
      
      <div className="divider">OR</div>
      
      {/* Traditional login form */}
      <form onSubmit={handlePasswordLogin}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          required
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          required
        />
        <button type="submit">Sign in with Password</button>
      </form>
      
      {error && <p className="error">{error}</p>}
    </div>
  )
}
```

## Advanced Features

### Managing Multiple Passkeys

Allow users to register multiple devices:

```tsx
import { usePasskey } from '@auth-kit/react'

function PasskeyManager() {
  const { passkeys, registerPasskey, deletePasskey, isSupported } = usePasskey()
  const [deviceName, setDeviceName] = useState('')

  const handleAddPasskey = async () => {
    try {
      await registerPasskey({
        displayName: deviceName || 'My Device',
        requireUserVerification: true
      })
      setDeviceName('')
    } catch (error) {
      console.error('Failed to add passkey:', error)
    }
  }

  if (!isSupported) {
    return <p>Passkeys are not supported on this device</p>
  }

  return (
    <div>
      <h3>Manage Passkeys</h3>
      
      {/* List existing passkeys */}
      <div className="passkey-list">
        {passkeys.map((passkey) => (
          <div key={passkey.id} className="passkey-item">
            <div>
              <strong>{passkey.name}</strong>
              <p>Added: {new Date(passkey.createdAt).toLocaleDateString()}</p>
              <p>Last used: {passkey.lastUsedAt ? new Date(passkey.lastUsedAt).toLocaleDateString() : 'Never'}</p>
            </div>
            <button
              onClick={() => deletePasskey(passkey.id)}
              className="delete-button"
            >
              Remove
            </button>
          </div>
        ))}
      </div>
      
      {/* Add new passkey */}
      <div className="add-passkey">
        <input
          type="text"
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          placeholder="Device name (optional)"
        />
        <button onClick={handleAddPasskey}>
          Add New Passkey
        </button>
      </div>
    </div>
  )
}
```

### Conditional UI Based on Passkey Availability

Show different UI based on passkey support:

```tsx
import { usePasskey } from '@auth-kit/react'

function SmartAuthForm() {
  const { isSupported, hasPasskeys } = usePasskey()

  if (!isSupported) {
    // Show traditional login only
    return <TraditionalLoginForm />
  }

  if (hasPasskeys) {
    // User has passkeys, show passkey-first UI
    return <PasskeyFirstLogin />
  }

  // Show option to set up passkey
  return <LoginWithPasskeyOption />
}
```

### Custom Passkey UI

Create a custom passkey button:

```tsx
function CustomPasskeyButton() {
  const { authenticateWithPasskey, isAuthenticating } = usePasskey()
  
  return (
    <button
      onClick={authenticateWithPasskey}
      disabled={isAuthenticating}
      className="custom-passkey-btn"
    >
      <svg className="icon" viewBox="0 0 24 24">
        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
      </svg>
      {isAuthenticating ? (
        <span>Verifying...</span>
      ) : (
        <span>Continue with Face ID / Touch ID</span>
      )}
    </button>
  )
}
```

## Backend Implementation Details

### Passkey Registration Endpoint

The registration process:

```python
@router.post("/passkeys/register/begin")
async def begin_passkey_registration(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Generate registration options
    options = generate_registration_options(
        rp_id=config.passkey_rp_id,
        rp_name=config.passkey_rp_name,
        user_id=str(user.id),
        user_name=user.email,
        user_display_name=user.email,
        require_user_verification=True
    )
    
    # Store challenge for verification
    cache.set(f"passkey_challenge_{user.id}", options.challenge, ttl=300)
    
    return options

@router.post("/passkeys/register/complete")
async def complete_passkey_registration(
    credential: PasskeyRegistrationCredential,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify the credential
    verified = verify_registration_response(
        credential=credential,
        expected_challenge=cache.get(f"passkey_challenge_{user.id}"),
        expected_origin=config.passkey_origin,
        expected_rp_id=config.passkey_rp_id
    )
    
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid credential")
    
    # Save the passkey
    passkey = Passkey(
        user_id=user.id,
        credential_id=credential.id,
        public_key=credential.public_key,
        name=credential.name or "My Passkey"
    )
    db.add(passkey)
    db.commit()
    
    return {"success": true, "passkey_id": passkey.id}
```

### Passkey Authentication Endpoint

The authentication process:

```python
@router.post("/passkeys/authenticate/begin")
async def begin_passkey_authentication(
    email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Get allowed credentials for user
    allowed_credentials = []
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            passkeys = db.query(Passkey).filter(Passkey.user_id == user.id).all()
            allowed_credentials = [p.credential_id for p in passkeys]
    
    # Generate authentication options
    options = generate_authentication_options(
        rp_id=config.passkey_rp_id,
        allowed_credentials=allowed_credentials,
        require_user_verification=True
    )
    
    # Store challenge
    cache.set(f"auth_challenge_{session_id}", options.challenge, ttl=300)
    
    return options

@router.post("/passkeys/authenticate/complete")
async def complete_passkey_authentication(
    credential: PasskeyAuthenticationCredential,
    db: Session = Depends(get_db)
):
    # Find the passkey
    passkey = db.query(Passkey).filter(
        Passkey.credential_id == credential.id
    ).first()
    
    if not passkey:
        raise HTTPException(status_code=404, detail="Passkey not found")
    
    # Verify the assertion
    verified = verify_authentication_response(
        credential=credential,
        expected_challenge=cache.get(f"auth_challenge_{session_id}"),
        expected_origin=config.passkey_origin,
        expected_rp_id=config.passkey_rp_id,
        public_key=passkey.public_key
    )
    
    if not verified:
        raise HTTPException(status_code=400, detail="Authentication failed")
    
    # Update last used
    passkey.last_used_at = datetime.utcnow()
    db.commit()
    
    # Generate tokens
    user = passkey.user
    access_token = create_access_token(user_id=str(user.id))
    refresh_token = create_refresh_token(user_id=str(user.id))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }
```

## Security Considerations

### 1. Always Use HTTPS
WebAuthn requires a secure context:
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

### 2. Verify RP ID
Ensure the RP ID matches your domain:
```python
# Correct
passkey_rp_id="example.com"  # Works for example.com and *.example.com

# Incorrect
passkey_rp_id="app.example.com"  # Only works for app.example.com
```

### 3. User Verification
Always require user verification for sensitive operations:
```typescript
await registerPasskey({
  requireUserVerification: true  // Requires biometric or PIN
})
```

### 4. Backup Authentication Methods
Always provide fallback options:
```tsx
function LoginPage() {
  return (
    <div>
      <PasskeyLogin />
      <Divider>or</Divider>
      <PasswordLogin />
      <Link href="/forgot-password">Forgot password?</Link>
    </div>
  )
}
```

## Troubleshooting

### Common Issues

**"NotAllowedError: The operation is not allowed"**
- User cancelled the operation
- Permissions not granted
- Not in a secure context (HTTPS)

**"NotSupportedError: The operation is not supported"**
- Browser doesn't support WebAuthn
- Device doesn't have authenticator

**"InvalidStateError: The credential already exists"**
- User trying to register same authenticator twice
- Clear existing credentials first

### Debug Mode

Enable debug logging:
```typescript
<AuthProvider
  config={{
    apiUrl: '...',
    enablePasskeys: true,
    debug: true,  // Enables WebAuthn debug logs
  }}
>
```

## Best Practices

### 1. Progressive Enhancement
Start with passwords, add passkeys:
```tsx
function ProgressiveAuth() {
  const { isSupported } = usePasskey()
  
  // Always show password option
  // Show passkey only if supported
  return (
    <>
      <PasswordForm />
      {isSupported && <PasskeyOption />}
    </>
  )
}
```

### 2. Clear User Communication
Explain what passkeys are:
```tsx
<div className="passkey-info">
  <h4>What are passkeys?</h4>
  <p>Passkeys let you sign in with Face ID, Touch ID, or your device PIN - no password needed!</p>
  <ul>
    <li>More secure than passwords</li>
    <li>Can't be phished or stolen</li>
    <li>Work across your devices</li>
  </ul>
</div>
```

### 3. Device Naming
Let users name their passkeys:
```tsx
await registerPasskey({
  displayName: "iPhone 15 Pro",  // User-friendly name
  requireUserVerification: true
})
```

### 4. Account Recovery
Provide recovery options:
- Email verification
- Backup codes
- Admin support

## Platform-Specific Notes

### iOS/macOS
- Passkeys sync via iCloud Keychain
- Require iOS 16+ / macOS 13+
- Work with Face ID / Touch ID

### Android
- Passkeys sync via Google Password Manager
- Require Android 9+
- Work with fingerprint / face unlock

### Windows
- Windows Hello integration
- Require Windows 10 1903+
- Work with PIN / fingerprint / face

## Next Steps

- Learn about [Two-Factor Authentication](./two-factor.md)
- Implement [Email Verification](./email-verification.md)
- Review [Security Best Practices](../concepts/security.md)