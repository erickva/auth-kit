# Setting up Two-Factor Authentication (2FA)

This guide covers implementing two-factor authentication using Time-based One-Time Passwords (TOTP) in your application.

## Quick Setup with CLI

Enable 2FA support when creating your project:

```bash
# Select "Two-factor authentication" during project setup
npx @auth-kit/cli create my-app

# Generate 2FA components for existing projects
npx @auth-kit/cli generate component TwoFactorSetup
npx @auth-kit/cli generate component TwoFactorLogin
```

The CLI will configure all necessary endpoints and create UI components for 2FA management.

## Overview

Two-factor authentication adds an extra layer of security by requiring:
1. Something you know (password)
2. Something you have (authenticator app)

## Prerequisites

- Auth Kit configured and working
- User authentication implemented
- HTTPS enabled (required for security)

## Basic Implementation

### 1. Enable 2FA in Configuration

**Backend:**
```python
from auth_kit_fastapi import AuthConfig

config = AuthConfig(
    jwt_secret="your-secret",
    features={
        "two_factor": True
    },
    # Optional: customize 2FA settings
    totp_issuer="My App",  # Shows in authenticator apps
    totp_algorithm="SHA1",  # SHA1, SHA256, or SHA512
    totp_digits=6,  # 6 or 8 digits
    totp_period=30,  # seconds
)
```

**Frontend:**
```typescript
<AuthProvider
  config={{
    apiUrl: 'https://api.example.com',
    enable2FA: true,
  }}
>
```

### 2. 2FA Setup Flow

Create a component for users to enable 2FA:

```tsx
import { use2FA } from '@auth-kit/react'
import { useState } from 'react'
import QRCode from 'qrcode.react'

function Setup2FA() {
  const { 
    enable2FA, 
    verify2FASetup, 
    disable2FA,
    is2FAEnabled,
    isSettingUp 
  } = use2FA()
  
  const [secret, setSecret] = useState<string | null>(null)
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [verificationCode, setVerificationCode] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const handleEnable2FA = async () => {
    try {
      const { secret, qr_code, recovery_codes } = await enable2FA()
      setSecret(secret)
      setQrCode(qr_code)
      setRecoveryCodes(recovery_codes)
    } catch (err) {
      setError('Failed to initialize 2FA setup')
    }
  }

  const handleVerifySetup = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await verify2FASetup(verificationCode)
      // 2FA is now enabled!
      alert('2FA enabled successfully!')
    } catch (err) {
      setError('Invalid code. Please try again.')
    }
  }

  if (is2FAEnabled) {
    return (
      <div className="2fa-enabled">
        <h3>Two-Factor Authentication is Enabled</h3>
        <p>Your account is protected with 2FA.</p>
        <button onClick={() => disable2FA()} className="danger-button">
          Disable 2FA
        </button>
      </div>
    )
  }

  if (!secret) {
    return (
      <div className="2fa-setup">
        <h3>Enable Two-Factor Authentication</h3>
        <p>Add an extra layer of security to your account.</p>
        <button onClick={handleEnable2FA} disabled={isSettingUp}>
          {isSettingUp ? 'Setting up...' : 'Enable 2FA'}
        </button>
      </div>
    )
  }

  return (
    <div className="2fa-verification">
      <h3>Set Up Two-Factor Authentication</h3>
      
      {/* Step 1: Show QR Code */}
      <div className="step">
        <h4>Step 1: Scan QR Code</h4>
        <p>Scan this QR code with your authenticator app:</p>
        {qrCode && <QRCode value={qrCode} size={200} />}
        <details>
          <summary>Can't scan? Enter manually</summary>
          <code>{secret}</code>
        </details>
      </div>

      {/* Step 2: Save Recovery Codes */}
      <div className="step">
        <h4>Step 2: Save Recovery Codes</h4>
        <p>Save these codes in a safe place. You can use them to access your account if you lose your device.</p>
        <div className="recovery-codes">
          {recoveryCodes.map((code, index) => (
            <code key={index}>{code}</code>
          ))}
        </div>
        <button onClick={() => navigator.clipboard.writeText(recoveryCodes.join('\n'))}>
          Copy Codes
        </button>
      </div>

      {/* Step 3: Verify */}
      <div className="step">
        <h4>Step 3: Verify Setup</h4>
        <p>Enter the 6-digit code from your authenticator app:</p>
        <form onSubmit={handleVerifySetup}>
          <input
            type="text"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
            placeholder="000000"
            pattern="[0-9]{6}"
            maxLength={6}
            required
          />
          <button type="submit">Verify and Enable</button>
        </form>
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  )
}
```

### 3. Login with 2FA

Update your login flow to handle 2FA:

```tsx
import { useAuth } from '@auth-kit/react'
import { useState } from 'react'

function LoginWith2FA() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [requires2FA, setRequires2FA] = useState(false)
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [tempToken, setTempToken] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleInitialLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const result = await login({ email, password })
      
      if (result.requires_2fa) {
        // User has 2FA enabled
        setRequires2FA(true)
        setTempToken(result.temp_token)
      } else {
        // Login successful, no 2FA required
        router.push('/dashboard')
      }
    } catch (err) {
      setError('Invalid credentials')
    }
  }

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login({
        email,
        password,
        twoFactorCode,
        tempToken
      })
      // Login successful!
      router.push('/dashboard')
    } catch (err) {
      setError('Invalid 2FA code')
    }
  }

  if (requires2FA) {
    return (
      <form onSubmit={handleVerify2FA}>
        <h3>Enter Verification Code</h3>
        <p>Enter the 6-digit code from your authenticator app:</p>
        <input
          type="text"
          value={twoFactorCode}
          onChange={(e) => setTwoFactorCode(e.target.value)}
          placeholder="000000"
          pattern="[0-9]{6}"
          maxLength={6}
          required
          autoFocus
        />
        <button type="submit">Verify</button>
        {error && <p className="error">{error}</p>}
      </form>
    )
  }

  return (
    <form onSubmit={handleInitialLogin}>
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
      <button type="submit">Sign In</button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}
```

## Advanced Features

### Recovery Codes

Implement recovery code usage:

```tsx
import { useAuth } from '@auth-kit/react'

function LoginWithRecoveryCode() {
  const { loginWithRecoveryCode } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await loginWithRecoveryCode({
        email,
        password,
        recoveryCode: recoveryCode.replace(/\s/g, '') // Remove spaces
      })
      router.push('/dashboard')
    } catch (err) {
      setError('Invalid recovery code')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h3>Use Recovery Code</h3>
      <p>Lost access to your authenticator app? Use a recovery code:</p>
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
      <input
        type="text"
        value={recoveryCode}
        onChange={(e) => setRecoveryCode(e.target.value)}
        placeholder="Recovery code"
        pattern="[A-Z0-9-]+"
        required
      />
      <button type="submit">Sign In</button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}
```

### Regenerate Recovery Codes

Allow users to generate new recovery codes:

```tsx
import { use2FA } from '@auth-kit/react'

function RecoveryCodesManager() {
  const { regenerateRecoveryCodes } = use2FA()
  const [newCodes, setNewCodes] = useState<string[]>([])
  const [showCodes, setShowCodes] = useState(false)

  const handleRegenerate = async () => {
    if (!confirm('This will invalidate your old recovery codes. Continue?')) {
      return
    }

    try {
      const codes = await regenerateRecoveryCodes()
      setNewCodes(codes)
      setShowCodes(true)
    } catch (error) {
      console.error('Failed to regenerate codes:', error)
    }
  }

  return (
    <div>
      <h3>Recovery Codes</h3>
      <p>Recovery codes can be used to access your account if you lose your device.</p>
      
      <button onClick={handleRegenerate}>
        Generate New Recovery Codes
      </button>

      {showCodes && (
        <div className="recovery-codes-display">
          <h4>Your New Recovery Codes</h4>
          <p className="warning">⚠️ Save these codes now! They won't be shown again.</p>
          <div className="codes-grid">
            {newCodes.map((code, index) => (
              <code key={index}>{code}</code>
            ))}
          </div>
          <button onClick={() => navigator.clipboard.writeText(newCodes.join('\n'))}>
            Copy All Codes
          </button>
          <button onClick={() => setShowCodes(false)}>
            I've Saved These Codes
          </button>
        </div>
      )}
    </div>
  )
}
```

### Custom 2FA Input Component

Create a better UX for code entry:

```tsx
function TwoFactorCodeInput({ onComplete }: { onComplete: (code: string) => void }) {
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  const handleChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return // Only digits

    const newDigits = [...digits]
    newDigits[index] = value

    setDigits(newDigits)

    // Auto-advance to next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus()
    }

    // Check if complete
    const code = newDigits.join('')
    if (code.length === 6) {
      onComplete(code)
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const pastedData = e.clipboardData.getData('text').slice(0, 6)
    const pastedDigits = pastedData.split('').filter(char => /\d/.test(char))
    
    const newDigits = [...digits]
    pastedDigits.forEach((digit, i) => {
      if (i < 6) newDigits[i] = digit
    })
    
    setDigits(newDigits)
    if (pastedDigits.length === 6) {
      onComplete(newDigits.join(''))
    }
  }

  return (
    <div className="code-input-container">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={el => inputRefs.current[index] = el}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={index === 0 ? handlePaste : undefined}
          className="code-input-digit"
          autoFocus={index === 0}
        />
      ))}
    </div>
  )
}
```

## Backend Implementation

### Setup Endpoint

```python
from pyotp import random_base32, totp
import qrcode
from io import BytesIO
import base64

@router.post("/2fa/setup")
async def setup_2fa(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Generate secret
    secret = random_base32()
    
    # Generate QR code
    provisioning_uri = totp.TOTP(secret).provisioning_uri(
        name=user.email,
        issuer_name=config.totp_issuer
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    qr_code = base64.b64encode(buf.getvalue()).decode()
    
    # Generate recovery codes
    recovery_codes = [
        f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        for _ in range(8)
    ]
    
    # Store temporarily (user must verify to activate)
    cache.set(
        f"2fa_setup_{user.id}",
        {
            "secret": secret,
            "recovery_codes": recovery_codes
        },
        ttl=600  # 10 minutes
    )
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code}",
        "recovery_codes": recovery_codes
    }

@router.post("/2fa/verify-setup")
async def verify_2fa_setup(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get setup data
    setup_data = cache.get(f"2fa_setup_{user.id}")
    if not setup_data:
        raise HTTPException(status_code=400, detail="Setup expired")
    
    # Verify code
    totp_instance = totp.TOTP(setup_data["secret"])
    if not totp_instance.verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")
    
    # Enable 2FA for user
    user.two_factor_secret = setup_data["secret"]
    user.recovery_codes = setup_data["recovery_codes"]
    user.two_factor_enabled = True
    db.commit()
    
    # Clear setup data
    cache.delete(f"2fa_setup_{user.id}")
    
    return {"success": True}
```

### Login with 2FA

```python
@router.post("/login")
async def login_with_2fa(
    form_data: OAuth2PasswordRequestForm = Depends(),
    two_factor_code: Optional[str] = Form(None),
    temp_token: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Standard authentication
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if 2FA is enabled
    if user.two_factor_enabled:
        if not two_factor_code:
            # Generate temporary token
            temp_token = create_temp_token(user_id=str(user.id))
            return {
                "requires_2fa": True,
                "temp_token": temp_token
            }
        
        # Verify 2FA code
        if temp_token:
            # Verify temp token
            payload = verify_temp_token(temp_token)
            if payload.get("user_id") != str(user.id):
                raise HTTPException(status_code=401, detail="Invalid token")
        
        # Check TOTP code
        totp_instance = totp.TOTP(user.two_factor_secret)
        if not totp_instance.verify(two_factor_code, valid_window=1):
            # Check recovery code
            if two_factor_code not in user.recovery_codes:
                raise HTTPException(status_code=401, detail="Invalid 2FA code")
            
            # Remove used recovery code
            user.recovery_codes.remove(two_factor_code)
            db.commit()
    
    # Generate tokens
    access_token = create_access_token(user_id=str(user.id))
    refresh_token = create_refresh_token(user_id=str(user.id))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }
```

## Security Best Practices

### 1. Rate Limiting
Protect against brute force:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/2fa/verify")
@limiter.limit("5/minute")  # 5 attempts per minute
async def verify_2fa_code(...):
    # Implementation
```

### 2. Code Window
Allow for time drift:
```python
# Allow 1 window before/after (±30 seconds)
totp_instance.verify(code, valid_window=1)
```

### 3. Secure Storage
Encrypt 2FA secrets:
```python
from cryptography.fernet import Fernet

def encrypt_secret(secret: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted: str) -> str:
    f = Fernet(settings.ENCRYPTION_KEY)
    return f.decrypt(encrypted.encode()).decode()
```

### 4. Backup Methods
Always provide alternatives:
- Recovery codes
- SMS backup (less secure)
- Admin override (with proper authorization)

## User Experience Tips

### 1. Clear Instructions
```tsx
<div className="instructions">
  <h4>Recommended Authenticator Apps:</h4>
  <ul>
    <li>Google Authenticator</li>
    <li>Microsoft Authenticator</li>
    <li>Authy</li>
    <li>1Password</li>
  </ul>
</div>
```

### 2. Remember Device Option
```tsx
function LoginWith2FA() {
  const [rememberDevice, setRememberDevice] = useState(false)
  
  // After successful 2FA
  if (rememberDevice) {
    // Set secure cookie for 30 days
    document.cookie = `device_token=${deviceToken}; max-age=2592000; secure; samesite=strict`
  }
}
```

### 3. Grace Period
Allow recently authenticated users to skip 2FA:
```python
def require_2fa(last_verified: datetime) -> bool:
    # Skip 2FA if verified in last 15 minutes
    if datetime.utcnow() - last_verified < timedelta(minutes=15):
        return False
    return True
```

## Testing 2FA

### Manual Testing
1. Use a real authenticator app
2. Test with correct and incorrect codes
3. Test recovery codes
4. Test time drift scenarios

### Automated Testing
```python
import pyotp
from datetime import datetime

def test_2fa_setup():
    # Setup 2FA
    response = client.post("/api/2fa/setup", headers=auth_headers)
    assert response.status_code == 200
    secret = response.json()["secret"]
    
    # Generate valid code
    totp_instance = pyotp.TOTP(secret)
    code = totp_instance.now()
    
    # Verify setup
    response = client.post(
        "/api/2fa/verify-setup",
        json={"code": code},
        headers=auth_headers
    )
    assert response.status_code == 200

def test_login_with_2fa():
    # Initial login
    response = client.post("/api/login", data={
        "username": "test@example.com",
        "password": "password"
    })
    assert response.json()["requires_2fa"] == True
    temp_token = response.json()["temp_token"]
    
    # Complete with 2FA
    code = pyotp.TOTP(user_secret).now()
    response = client.post("/api/login", data={
        "username": "test@example.com",
        "password": "password",
        "two_factor_code": code,
        "temp_token": temp_token
    })
    assert "access_token" in response.json()
```

## Troubleshooting

### Common Issues

**"Invalid code" errors**
- Check time synchronization
- Verify secret is correctly stored
- Ensure QR code was scanned properly

**Recovery codes not working**
- Check formatting (remove spaces/dashes)
- Verify codes haven't been used
- Ensure codes are stored correctly

**QR code not scanning**
- Increase QR code size
- Check contrast/colors
- Provide manual entry option

## Next Steps

- Implement [Email Verification](./email-verification.md)
- Add [Password Reset](./password-reset.md)
- Review [Security Best Practices](../concepts/security.md)