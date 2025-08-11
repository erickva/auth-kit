# React Hooks API Reference

Auth Kit provides a comprehensive set of React hooks for authentication management.

## useAuth

The main authentication hook providing auth state and methods.

### Usage

```tsx
import { useAuth } from '@auth-kit/react'

function Component() {
  const {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,
    
    // Methods
    login,
    logout,
    register,
    refreshToken,
    updateUser,
    
    // Utilities
    getAuthHeaders,
    checkAuth,
  } = useAuth()
}
```

### Properties

#### State Properties

**user** `User | null`
- Current authenticated user object
- `null` when not authenticated

**isAuthenticated** `boolean`
- `true` when user is authenticated
- `false` otherwise

**isLoading** `boolean`
- `true` during authentication operations
- Useful for showing loading states

**error** `AuthError | null`
- Contains error information from last operation
- `null` when no error

#### Methods

**login** `(credentials: LoginCredentials) => Promise<LoginResponse>`
- Authenticates user with email/password
- Handles 2FA flow automatically
- Stores tokens based on storage configuration

```tsx
const handleLogin = async () => {
  try {
    const response = await login({
      email: 'user@example.com',
      password: 'password',
      rememberMe: true,
    })
    
    if (response.requires_2fa) {
      // Handle 2FA flow
    }
  } catch (error) {
    console.error('Login failed:', error)
  }
}
```

**logout** `() => Promise<void>`
- Logs out current user
- Clears stored tokens
- Resets auth state

```tsx
const handleLogout = async () => {
  await logout()
  router.push('/login')
}
```

**register** `(data: RegisterData) => Promise<User>`
- Creates new user account
- Automatically logs in after registration
- Returns created user object

```tsx
const handleRegister = async () => {
  try {
    const user = await register({
      email: 'new@example.com',
      password: 'securepassword',
      firstName: 'John',
      lastName: 'Doe',
    })
    console.log('Registered:', user)
  } catch (error) {
    console.error('Registration failed:', error)
  }
}
```

**refreshToken** `() => Promise<void>`
- Manually refreshes access token
- Usually called automatically
- Useful for preemptive refresh

**updateUser** `(data: Partial<User>) => Promise<User>`
- Updates current user's profile
- Returns updated user object

```tsx
const handleUpdateProfile = async () => {
  const updated = await updateUser({
    firstName: 'Jane',
    lastName: 'Smith',
  })
}
```

**getAuthHeaders** `() => Record<string, string>`
- Returns headers with auth token
- Use for authenticated API calls

```tsx
const fetchProtectedData = async () => {
  const response = await fetch('/api/protected', {
    headers: getAuthHeaders(),
  })
  return response.json()
}
```

**checkAuth** `() => Promise<boolean>`
- Verifies current authentication status
- Refreshes token if needed
- Returns authentication status

### Advanced Usage

#### Custom Error Handling

```tsx
function LoginForm() {
  const { login, error } = useAuth()
  
  const getErrorMessage = () => {
    if (!error) return null
    
    switch (error.code) {
      case 'INVALID_CREDENTIALS':
        return 'Invalid email or password'
      case 'ACCOUNT_LOCKED':
        return 'Account is locked. Please contact support.'
      case 'EMAIL_NOT_VERIFIED':
        return 'Please verify your email first'
      default:
        return 'An error occurred. Please try again.'
    }
  }
  
  return (
    <>
      {error && <Alert type="error">{getErrorMessage()}</Alert>}
      {/* Login form */}
    </>
  )
}
```

#### Conditional Rendering

```tsx
function Navigation() {
  const { isAuthenticated, isLoading, user } = useAuth()
  
  if (isLoading) {
    return <Skeleton />
  }
  
  return (
    <nav>
      {isAuthenticated ? (
        <>
          <span>Welcome, {user?.firstName}!</span>
          <LogoutButton />
        </>
      ) : (
        <>
          <Link to="/login">Login</Link>
          <Link to="/register">Sign Up</Link>
        </>
      )}
    </nav>
  )
}
```

## usePasskey

Hook for managing WebAuthn/Passkey authentication.

### Usage

```tsx
import { usePasskey } from '@auth-kit/react'

function PasskeyAuth() {
  const {
    // State
    isSupported,
    isRegistering,
    isAuthenticating,
    passkeys,
    hasPasskeys,
    
    // Methods
    registerPasskey,
    authenticateWithPasskey,
    deletePasskey,
    updatePasskey,
  } = usePasskey()
}
```

### Properties

**isSupported** `boolean`
- Whether device supports WebAuthn
- Check before showing passkey UI

**isRegistering** `boolean`
- `true` during passkey registration

**isAuthenticating** `boolean`
- `true` during passkey authentication

**passkeys** `Passkey[]`
- List of user's registered passkeys
- Empty array when none registered

**hasPasskeys** `boolean`
- Whether user has any passkeys

### Methods

**registerPasskey** `(options?: RegisterPasskeyOptions) => Promise<Passkey>`

```tsx
const handleRegisterPasskey = async () => {
  try {
    const passkey = await registerPasskey({
      displayName: 'MacBook Pro',
      requireUserVerification: true,
    })
    console.log('Passkey registered:', passkey.id)
  } catch (error) {
    console.error('Registration failed:', error)
  }
}
```

**authenticateWithPasskey** `(options?: AuthenticateOptions) => Promise<void>`

```tsx
const handlePasskeyLogin = async () => {
  try {
    await authenticateWithPasskey({
      // Optional: specify credential ID
      credentialId: savedCredentialId,
    })
    // User is now logged in
  } catch (error) {
    console.error('Authentication failed:', error)
  }
}
```

**deletePasskey** `(passkeyId: string) => Promise<void>`

```tsx
const handleDeletePasskey = async (id: string) => {
  if (confirm('Remove this passkey?')) {
    await deletePasskey(id)
  }
}
```

**updatePasskey** `(passkeyId: string, data: UpdatePasskeyData) => Promise<Passkey>`

```tsx
const handleRenamePasskey = async (id: string, newName: string) => {
  await updatePasskey(id, { name: newName })
}
```

## use2FA

Hook for managing two-factor authentication.

### Usage

```tsx
import { use2FA } from '@auth-kit/react'

function TwoFactorSettings() {
  const {
    // State
    is2FAEnabled,
    isSettingUp,
    isVerifying,
    
    // Methods
    enable2FA,
    verify2FASetup,
    disable2FA,
    verify2FACode,
    regenerateRecoveryCodes,
  } = use2FA()
}
```

### Properties

**is2FAEnabled** `boolean`
- Whether 2FA is enabled for current user

**isSettingUp** `boolean`
- `true` during 2FA setup process

**isVerifying** `boolean`
- `true` during code verification

### Methods

**enable2FA** `() => Promise<Setup2FAResponse>`

```tsx
const handleEnable2FA = async () => {
  const { secret, qr_code, recovery_codes } = await enable2FA()
  // Show QR code and recovery codes to user
}
```

**verify2FASetup** `(code: string) => Promise<void>`

```tsx
const handleVerifySetup = async (code: string) => {
  await verify2FASetup(code)
  // 2FA is now enabled
}
```

**disable2FA** `(password: string) => Promise<void>`

```tsx
const handleDisable2FA = async () => {
  const password = prompt('Enter your password to disable 2FA:')
  if (password) {
    await disable2FA(password)
  }
}
```

**verify2FACode** `(code: string) => Promise<boolean>`

```tsx
const handleVerifyCode = async (code: string) => {
  const isValid = await verify2FACode(code)
  return isValid
}
```

**regenerateRecoveryCodes** `() => Promise<string[]>`

```tsx
const handleRegenerateRecoveryCodes = async () => {
  const newCodes = await regenerateRecoveryCodes()
  // Show new codes to user
}
```

## usePasswordReset

Hook for password reset functionality.

### Usage

```tsx
import { usePasswordReset } from '@auth-kit/react'

function PasswordResetFlow() {
  const {
    // State
    isRequesting,
    isResetting,
    
    // Methods
    requestPasswordReset,
    resetPassword,
    validateResetToken,
  } = usePasswordReset()
}
```

### Methods

**requestPasswordReset** `(email: string) => Promise<void>`

```tsx
const handleRequestReset = async (email: string) => {
  await requestPasswordReset(email)
  // Email sent
}
```

**resetPassword** `(token: string, newPassword: string) => Promise<void>`

```tsx
const handleResetPassword = async () => {
  await resetPassword(token, newPassword)
  // Password reset successful
}
```

**validateResetToken** `(token: string) => Promise<boolean>`

```tsx
const isValidToken = await validateResetToken(token)
if (!isValidToken) {
  // Show error: token expired or invalid
}
```

## useEmailVerification

Hook for email verification functionality.

### Usage

```tsx
import { useEmailVerification } from '@auth-kit/react'

function EmailVerification() {
  const {
    // State
    isEmailVerified,
    isVerifying,
    isSending,
    
    // Methods
    verifyEmail,
    resendVerificationEmail,
  } = useEmailVerification()
}
```

### Properties

**isEmailVerified** `boolean`
- Whether current user's email is verified

**isVerifying** `boolean`
- `true` during email verification

**isSending** `boolean`
- `true` while sending verification email

### Methods

**verifyEmail** `(token: string) => Promise<void>`

```tsx
const handleVerifyEmail = async (token: string) => {
  await verifyEmail(token)
  // Email verified
}
```

**resendVerificationEmail** `() => Promise<void>`

```tsx
const handleResendEmail = async () => {
  await resendVerificationEmail()
  // Verification email sent
}
```

## useSession

Hook for session management.

### Usage

```tsx
import { useSession } from '@auth-kit/react'

function SessionManager() {
  const {
    // State
    sessions,
    currentSessionId,
    
    // Methods
    getSessions,
    revokeSession,
    revokeAllSessions,
  } = useSession()
}
```

### Properties

**sessions** `Session[]`
- List of active sessions

**currentSessionId** `string | null`
- ID of current session

### Methods

**getSessions** `() => Promise<Session[]>`

```tsx
const sessions = await getSessions()
// Display active sessions
```

**revokeSession** `(sessionId: string) => Promise<void>`

```tsx
const handleRevokeSession = async (id: string) => {
  await revokeSession(id)
  // Session revoked
}
```

**revokeAllSessions** `() => Promise<void>`

```tsx
const handleLogoutEverywhere = async () => {
  await revokeAllSessions()
  // All sessions revoked except current
}
```

## Custom Hooks

### useRequireAuth

Require authentication for a component:

```tsx
import { useRequireAuth } from '@auth-kit/react'

function ProtectedPage() {
  const { user } = useRequireAuth({
    redirectTo: '/login',
    // Optional: require specific permissions
    permissions: ['admin', 'editor'],
  })
  
  return <div>Welcome {user.email}</div>
}
```

### useAuthRedirect

Redirect based on auth state:

```tsx
import { useAuthRedirect } from '@auth-kit/react'

function LoginPage() {
  // Redirect to dashboard if already logged in
  useAuthRedirect({
    redirectTo: '/dashboard',
    when: 'authenticated',
  })
  
  return <LoginForm />
}
```

## TypeScript Support

All hooks are fully typed:

```tsx
import { User, AuthError, LoginCredentials } from '@auth-kit/core'
import { useAuth } from '@auth-kit/react'

function TypedComponent() {
  const { user, error, login } = useAuth()
  
  // user is typed as User | null
  const userName: string = user?.firstName ?? 'Guest'
  
  // error is typed as AuthError | null
  const errorCode: string | undefined = error?.code
  
  // login accepts typed credentials
  const handleLogin = async (creds: LoginCredentials) => {
    await login(creds)
  }
}
```

## Best Practices

### 1. Handle Loading States

```tsx
function AuthenticatedApp() {
  const { isLoading, isAuthenticated } = useAuth()
  
  if (isLoading) {
    return <LoadingSpinner />
  }
  
  return isAuthenticated ? <Dashboard /> : <LoginPage />
}
```

### 2. Error Boundaries

```tsx
function AuthErrorBoundary({ children }: { children: React.ReactNode }) {
  const { error } = useAuth()
  
  if (error?.code === 'NETWORK_ERROR') {
    return <OfflineMessage />
  }
  
  return <>{children}</>
}
```

### 3. Optimistic Updates

```tsx
function ProfileEditor() {
  const { user, updateUser } = useAuth()
  const [optimisticUser, setOptimisticUser] = useState(user)
  
  const handleUpdate = async (data: Partial<User>) => {
    // Optimistic update
    setOptimisticUser({ ...optimisticUser, ...data })
    
    try {
      await updateUser(data)
    } catch (error) {
      // Revert on error
      setOptimisticUser(user)
    }
  }
}
```

## Next Steps

- Explore [React Components](./react-components.md)
- Learn about [Events](./events.md)
- Review [TypeScript Types](./types.md)