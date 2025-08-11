# Common Issues and Solutions

This guide covers frequently encountered issues and their solutions.

## Installation Issues

### Module not found errors

**Problem:**
```
Error: Cannot find module '@auth-kit/react'
```

**Solution:**
1. Ensure packages are installed:
   ```bash
   npm install @auth-kit/core @auth-kit/react
   ```
2. Check your import paths
3. If using TypeScript, ensure `tsconfig.json` includes the modules

### Type errors in TypeScript

**Problem:**
```
Type error: Cannot find module '@auth-kit/react' or its corresponding type declarations
```

**Solution:**
1. Install latest versions of packages
2. Add to `tsconfig.json`:
   ```json
   {
     "compilerOptions": {
       "moduleResolution": "node",
       "esModuleInterop": true
     }
   }
   ```

## Authentication Issues

### Login fails with "Network Error"

**Problem:**
User gets network error when trying to login.

**Solutions:**
1. Check API URL configuration:
   ```tsx
   <AuthProvider config={{ apiUrl: 'https://api.example.com' }}>
   ```
2. Verify CORS is properly configured on backend
3. Check if API is running and accessible
4. Look for mixed content (HTTP/HTTPS) issues

### Token refresh fails

**Problem:**
Users get logged out unexpectedly.

**Solutions:**
1. Check token expiration settings
2. Ensure refresh endpoint is working
3. Verify storage configuration:
   ```tsx
   // Use cookies for better persistence
   storageType: StorageType.Cookies
   ```

### "Invalid credentials" on correct password

**Problem:**
Login fails even with correct credentials.

**Possible causes:**
1. Email not verified (if enabled)
2. Account locked
3. Case sensitivity in email
4. Password was changed elsewhere

**Solution:**
```python
# Check user status in backend
user = db.query(User).filter(User.email == email.lower()).first()
if user and not user.is_active:
    raise HTTPException(status_code=403, detail="Account inactive")
```

## Passkey Issues

### "NotAllowedError" during passkey registration

**Problem:**
```
NotAllowedError: The operation either timed out or was not allowed
```

**Solutions:**
1. Ensure using HTTPS (required for WebAuthn)
2. Check RP ID matches domain:
   ```python
   passkey_rp_id="example.com"  # Not "www.example.com"
   ```
3. User may have cancelled the operation
4. Browser permissions might be blocked

### Passkey authentication fails

**Problem:**
Passkey login doesn't work after registration.

**Solutions:**
1. Verify origin configuration:
   ```python
   passkey_origin="https://app.example.com"
   ```
2. Check credential storage in database
3. Ensure user verification is consistent
4. Clear browser's WebAuthn state and try again

### "InvalidStateError" when registering passkey

**Problem:**
```
InvalidStateError: A credential with this ID already exists
```

**Solution:**
User is trying to register the same authenticator twice. Either:
1. Delete existing credential first
2. Use different authenticator
3. Clear browser data related to WebAuthn

## Two-Factor Authentication Issues

### QR code won't scan

**Problem:**
Authenticator app can't scan the QR code.

**Solutions:**
1. Increase QR code size
2. Ensure proper contrast
3. Provide manual entry option:
   ```tsx
   <details>
     <summary>Can't scan? Enter manually</summary>
     <code>{secret}</code>
   </details>
   ```

### "Invalid code" errors

**Problem:**
2FA codes are always invalid.

**Solutions:**
1. Check device time synchronization
2. Increase valid window:
   ```python
   totp.verify(code, valid_window=2)  # ±2 time steps
   ```
3. Verify secret is stored correctly
4. Test with multiple authenticator apps

### Recovery codes not working

**Problem:**
Recovery codes are rejected during login.

**Solutions:**
1. Remove formatting (spaces, dashes)
2. Check if code was already used
3. Verify codes are stored correctly
4. Ensure case sensitivity is handled

## CORS Issues

### "CORS policy" errors

**Problem:**
```
Access to fetch at 'https://api.example.com' from origin 'https://app.example.com' has been blocked by CORS policy
```

**Solution:**
Configure CORS properly in FastAPI:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Cookies not being set cross-domain

**Problem:**
Authentication works locally but not in production.

**Solution:**
1. Use same domain for frontend and backend
2. Or configure cookies properly:
   ```python
   response.set_cookie(
       key="auth_token",
       value=token,
       httponly=True,
       secure=True,  # HTTPS only
       samesite="none",  # For cross-origin
       domain=".example.com"  # For subdomains
   )
   ```

## Database Issues

### "Table does not exist" errors

**Problem:**
```
sqlalchemy.exc.OperationalError: no such table: users
```

**Solution:**
Run migrations:
```python
from auth_kit_fastapi import Base
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
```

### Connection pool exhausted

**Problem:**
```
TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Solution:**
Configure pool size:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)
```

## Performance Issues

### Slow authentication

**Problem:**
Login takes several seconds.

**Solutions:**
1. Reduce bcrypt rounds:
   ```python
   bcrypt_rounds=10  # Default is 12
   ```
2. Add database indexes:
   ```sql
   CREATE INDEX idx_users_email ON users(email);
   ```
3. Use connection pooling
4. Cache user lookups

### High memory usage

**Problem:**
Application uses too much memory.

**Solutions:**
1. Limit session storage
2. Configure token cleanup:
   ```python
   # Clean expired tokens periodically
   @app.on_event("startup")
   @repeat_every(seconds=3600)
   async def cleanup_tokens():
       # Implementation
   ```

## Email Issues

### Emails not being sent

**Problem:**
Password reset or verification emails don't arrive.

**Solutions:**
1. Check SMTP configuration
2. Use app-specific passwords for Gmail
3. Check spam folders
4. Test with different email provider:
   ```python
   # Test SMTP connection
   import smtplib
   server = smtplib.SMTP(smtp_host, smtp_port)
   server.starttls()
   server.login(smtp_username, smtp_password)
   ```

### Email templates not found

**Problem:**
```
FileNotFoundError: Email template not found
```

**Solution:**
Ensure templates are in correct location:
```
templates/
  emails/
    verification.html
    password_reset.html
```

## React/Frontend Issues

### useAuth returns null user

**Problem:**
`user` is always null even after login.

**Solutions:**
1. Check if tokens are being stored
2. Verify AuthProvider wraps your app
3. Check for multiple AuthProvider instances
4. Ensure storage permissions

### Infinite redirect loops

**Problem:**
App keeps redirecting between login and dashboard.

**Solution:**
```tsx
// Add loading check
function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()
  
  if (isLoading) return <Loading />
  if (!isAuthenticated) return <Navigate to="/login" />
  
  return children
}
```

### State not updating after login

**Problem:**
UI doesn't update after successful login.

**Solution:**
1. Check if using correct context
2. Ensure no duplicate providers
3. Use the callback:
   ```tsx
   <AuthProvider
     config={{
       apiUrl: '...',
       onAuthStateChange: (user, isAuth) => {
         console.log('Auth changed:', { user, isAuth })
       }
     }}
   >
   ```

## Production Issues

### Works locally but not in production

**Checklist:**
1. Environment variables are set
2. HTTPS is configured
3. Database migrations are run
4. CORS origins are correct
5. API URL is accessible
6. Cookies have correct domain

### Security warnings

**Problem:**
Browser shows security warnings.

**Solutions:**
1. Use HTTPS everywhere
2. Set secure cookie flags
3. Configure CSP headers
4. Use environment variables for secrets

## Getting Help

If your issue isn't covered here:

1. Check the [GitHub Issues](https://github.com/yourusername/auth-kit/issues)
2. Join our [Discord community](https://discord.gg/authkit)
3. Review the [API documentation](../api/)
4. Enable debug mode for more information:
   ```tsx
   <AuthProvider config={{ debug: true }}>
   ```

## Debug Mode

Enable comprehensive logging:

```typescript
// Frontend
<AuthProvider
  config={{
    apiUrl: '...',
    debug: true,
    logLevel: 'verbose',
  }}
>

// Backend
config = AuthConfig(
    jwt_secret="...",
    debug=True,
    log_level=logging.DEBUG,
)
```

This will log:
- All API requests/responses
- Token operations
- Storage operations
- WebAuthn flow details
- Error stack traces