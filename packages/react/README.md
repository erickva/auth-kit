# @auth-kit/react

React authentication library with hooks and components for Auth Kit.

## Quick Start with CLI

The easiest way to start using Auth Kit React is with our CLI:

```bash
# Create a new React app with Auth Kit
npx @auth-kit/cli create my-app --template react-spa

# Or add to existing React project
npx @auth-kit/cli add --framework react
```

## Manual Installation

```bash
npm install @auth-kit/core @auth-kit/react
# or
yarn add @auth-kit/core @auth-kit/react
# or
pnpm add @auth-kit/core @auth-kit/react
```

## Quick Start

Wrap your application with the `AuthProvider`:

```tsx
import { AuthProvider } from '@auth-kit/react'
import { StorageType } from '@auth-kit/core'

function App() {
  return (
    <AuthProvider
      config={{
        apiUrl: 'http://localhost:8000',
        storageType: StorageType.LocalStorage,
        tokenRefreshThreshold: 300, // Refresh token when < 5 minutes remain
      }}
    >
      {/* Your app components */}
    </AuthProvider>
  )
}
```

## Configuration

The `AuthProvider` accepts the following configuration options:

```typescript
interface AuthConfig {
  // Required
  apiUrl: string                    // Your backend API URL
  
  // Storage
  storageType?: StorageType         // LocalStorage (default), SessionStorage, Cookies, Memory
  storagePrefix?: string            // Prefix for storage keys (default: 'authkit_')
  
  // Token Management
  tokenRefreshThreshold?: number    // Seconds before expiry to refresh (default: 300)
  enableAutoRefresh?: boolean       // Auto-refresh tokens (default: true)
  
  // Features
  enablePasskeys?: boolean          // Enable passkey support (default: true)
  enable2FA?: boolean              // Enable 2FA support (default: true)
  
  // Callbacks
  onAuthStateChange?: (user: User | null, isAuthenticated: boolean) => void
  onTokenRefresh?: (tokens: AuthTokens) => void
  onSessionExpire?: () => void
  
  // Advanced
  debug?: boolean                  // Enable debug logging (default: false)
}
```

## Hooks

### useAuth

The main authentication hook providing auth state and methods.

```tsx
import { useAuth } from '@auth-kit/react'

function Component() {
  const {
    // State
    user,              // Current user object or null
    isAuthenticated,   // Boolean auth status
    isLoading,        // Loading state
    error,            // Last error or null
    
    // Methods
    login,            // Login with email/password
    logout,           // Logout user
    register,         // Register new user
    refreshToken,     // Manually refresh token
    updateUser,       // Update user profile
    
    // Utilities
    getAuthHeaders,   // Get headers for API calls
    checkAuth,        // Check auth status
  } = useAuth()
}
```

### usePasskey

Manage WebAuthn/Passkey authentication.

```tsx
import { usePasskey } from '@auth-kit/react'

function PasskeyComponent() {
  const {
    // State
    isSupported,             // Browser supports WebAuthn
    isRegistering,          // Registration in progress
    isAuthenticating,       // Authentication in progress
    passkeys,               // User's registered passkeys
    hasPasskeys,            // User has passkeys
    
    // Methods
    registerPasskey,        // Register new passkey
    authenticateWithPasskey, // Login with passkey
    deletePasskey,          // Remove passkey
    updatePasskey,          // Update passkey name
  } = usePasskey()
}
```

### use2FA

Manage two-factor authentication.

```tsx
import { use2FA } from '@auth-kit/react'

function TwoFactorComponent() {
  const {
    // State
    is2FAEnabled,           // 2FA enabled for user
    isSettingUp,           // Setup in progress
    isVerifying,           // Verification in progress
    
    // Methods
    enable2FA,             // Start 2FA setup
    verify2FASetup,        // Complete setup with code
    disable2FA,            // Disable 2FA
    verify2FACode,         // Verify 2FA code
    regenerateRecoveryCodes, // Get new recovery codes
  } = use2FA()
}
```

### usePasswordReset

Handle password reset flows.

```tsx
import { usePasswordReset } from '@auth-kit/react'

function PasswordResetComponent() {
  const {
    // State
    isRequesting,          // Request in progress
    isResetting,          // Reset in progress
    
    // Methods
    requestPasswordReset,  // Send reset email
    resetPassword,        // Reset with token
    validateResetToken,   // Check token validity
  } = usePasswordReset()
}
```

### useEmailVerification

Manage email verification.

```tsx
import { useEmailVerification } from '@auth-kit/react'

function EmailVerificationComponent() {
  const {
    // State
    isEmailVerified,       // Email verification status
    isVerifying,          // Verification in progress
    isSending,            // Sending email
    
    // Methods
    verifyEmail,          // Verify with token
    resendVerificationEmail, // Resend email
  } = useEmailVerification()
}
```

## Components

You can generate these components using the CLI:

```bash
# Generate a login form component
npx @auth-kit/cli generate component LoginForm

# Generate other components
npx @auth-kit/cli g component SignupForm
npx @auth-kit/cli g component PasswordResetForm
```

### LoginForm

Pre-built login form with email/password and optional passkey support.

```tsx
import { LoginForm } from '@auth-kit/react'

function LoginPage() {
  return (
    <LoginForm
      onSuccess={() => router.push('/dashboard')}
      onError={(error) => console.error(error)}
      showPasskey={true}
      showRememberMe={true}
      className="custom-login-form"
      submitButtonText="Sign In"
    />
  )
}
```

Props:
- `onSuccess?: () => void` - Called after successful login
- `onError?: (error: Error) => void` - Called on login error
- `showPasskey?: boolean` - Show passkey login option
- `showRememberMe?: boolean` - Show remember me checkbox
- `showForgotPassword?: boolean` - Show forgot password link
- `className?: string` - CSS class for form container
- `submitButtonText?: string` - Custom submit button text

### SignupForm

Registration form with validation and optional features.

```tsx
import { SignupForm } from '@auth-kit/react'

function SignupPage() {
  return (
    <SignupForm
      onSuccess={() => router.push('/verify-email')}
      onError={(error) => console.error(error)}
      showPasswordStrength={true}
      requireEmailVerification={true}
      fields={['email', 'password', 'firstName', 'lastName']}
      className="custom-signup-form"
    />
  )
}
```

Props:
- `onSuccess?: (user: User) => void` - Called after successful registration
- `onError?: (error: Error) => void` - Called on registration error
- `showPasswordStrength?: boolean` - Show password strength indicator
- `requireEmailVerification?: boolean` - Require email verification
- `fields?: string[]` - Fields to include in form
- `className?: string` - CSS class for form container

### ProtectedRoute

Wrapper component for protected routes.

```tsx
import { ProtectedRoute } from '@auth-kit/react'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute redirectTo="/login">
            <Dashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
```

Props:
- `children: React.ReactNode` - Protected content
- `redirectTo?: string` - Where to redirect if not authenticated
- `permissions?: string[]` - Required permissions
- `fallback?: React.ReactNode` - Loading state component

## Usage Examples

### Basic Authentication Flow

```tsx
function LoginExample() {
  const { login, isLoading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login({ email, password })
      // Redirect or update UI
    } catch (err) {
      // Error is also available in error state
    }
  }
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        disabled={isLoading}
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        disabled={isLoading}
      />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Signing in...' : 'Sign In'}
      </button>
      {error && <p className="error">{error.message}</p>}
    </form>
  )
}
```

### Passkey Registration

```tsx
function PasskeySetup() {
  const { user } = useAuth()
  const { registerPasskey, isSupported, isRegistering } = usePasskey()
  
  if (!isSupported) {
    return <p>Your browser doesn't support passkeys</p>
  }
  
  const handleRegister = async () => {
    try {
      await registerPasskey({
        displayName: user?.email || 'My Device',
        requireUserVerification: true,
      })
      alert('Passkey registered successfully!')
    } catch (error) {
      console.error('Failed to register passkey:', error)
    }
  }
  
  return (
    <button onClick={handleRegister} disabled={isRegistering}>
      {isRegistering ? 'Setting up...' : 'Add Passkey'}
    </button>
  )
}
```

### Protected API Calls

```tsx
function UserProfile() {
  const { getAuthHeaders } = useAuth()
  const [profile, setProfile] = useState(null)
  
  useEffect(() => {
    fetch('/api/profile', {
      headers: getAuthHeaders(),
    })
      .then(res => res.json())
      .then(setProfile)
      .catch(console.error)
  }, [])
  
  return profile ? <div>{profile.name}</div> : <div>Loading...</div>
}
```

### Custom Storage Adapter

```tsx
import { StorageAdapter } from '@auth-kit/core'

class SecureStorageAdapter implements StorageAdapter {
  async getItem(key: string): Promise<string | null> {
    // Your secure storage implementation
    return await SecureStorage.get(key)
  }
  
  async setItem(key: string, value: string): Promise<void> {
    await SecureStorage.set(key, value)
  }
  
  async removeItem(key: string): Promise<void> {
    await SecureStorage.remove(key)
  }
  
  async clear(): Promise<void> {
    await SecureStorage.clear()
  }
}

// Use in AuthProvider
<AuthProvider
  config={{
    apiUrl: '...',
    storageAdapter: new SecureStorageAdapter(),
  }}
>
```

## TypeScript Support

All hooks and components are fully typed. Import types from `@auth-kit/core`:

```typescript
import type { User, AuthTokens, LoginCredentials } from '@auth-kit/core'
```

## Error Handling

Auth Kit provides detailed error information:

```typescript
interface AuthError {
  code: string           // Error code (e.g., 'INVALID_CREDENTIALS')
  message: string        // Human-readable message
  statusCode?: number    // HTTP status code
  details?: any          // Additional error details
}
```

Common error codes:
- `INVALID_CREDENTIALS` - Wrong email/password
- `USER_NOT_FOUND` - User doesn't exist
- `EMAIL_NOT_VERIFIED` - Email verification required
- `ACCOUNT_LOCKED` - Too many failed attempts
- `NETWORK_ERROR` - Connection issues
- `TOKEN_EXPIRED` - Session expired

## Best Practices

1. **Always handle loading states**
   ```tsx
   const { isLoading } = useAuth()
   if (isLoading) return <Spinner />
   ```

2. **Use error boundaries**
   ```tsx
   <ErrorBoundary fallback={<ErrorPage />}>
     <AuthProvider config={config}>
       <App />
     </AuthProvider>
   </ErrorBoundary>
   ```

3. **Implement proper logout**
   ```tsx
   const handleLogout = async () => {
     await logout()
     router.push('/login')
     // Clear any app-specific data
   }
   ```

4. **Secure sensitive routes**
   ```tsx
   <ProtectedRoute permissions={['admin']}>
     <AdminPanel />
   </ProtectedRoute>
   ```

## License

MIT