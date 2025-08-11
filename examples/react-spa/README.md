# Auth Kit React SPA Example

This example demonstrates how to integrate `@auth-kit/react` into a single-page React application.

## Features Demonstrated

- 🔐 JWT authentication with automatic token refresh
- 🔑 Passkey/WebAuthn support
- 📱 Two-factor authentication (2FA)
- 👤 User profile management
- 🛡️ Protected routes
- 📧 Email verification flow
- 🔄 Password reset functionality

## Getting Started

### Prerequisites

- Node.js 18+
- A running backend server with auth-kit-fastapi (see backend example)

### Installation

1. From the auth-kit root directory, install dependencies:

```bash
npm install
```

2. Start the backend server (from the backend example directory):

```bash
cd examples/fastapi-backend
uvicorn main:app --reload
```

3. Start the React development server:

```bash
cd examples/react-spa
npm run dev
```

4. Open http://localhost:3000 in your browser

## Project Structure

```
src/
├── components/
│   ├── Layout.tsx          # Main layout with navigation
│   └── ProtectedRoute.tsx  # Route guard for authenticated routes
├── pages/
│   ├── HomePage.tsx        # Landing page
│   ├── LoginPage.tsx       # Login with email/password and passkeys
│   ├── RegisterPage.tsx    # User registration
│   ├── DashboardPage.tsx   # Protected dashboard
│   ├── ProfilePage.tsx     # User profile management
│   └── SettingsPage.tsx    # Security settings (2FA, passkeys)
├── App.tsx                 # Main app component with routing
└── main.tsx               # Application entry point
```

## Key Implementation Details

### Authentication Setup

The app wraps the entire component tree with `AuthProvider`:

```tsx
import { AuthProvider } from '@auth-kit/react'

const authConfig = {
  apiUrl: '/api',
  storageType: StorageType.LocalStorage,
  refreshInterval: 4 * 60 * 1000,
  enableAutoRefresh: true
}

function App() {
  return (
    <AuthProvider config={authConfig}>
      {/* Your app */}
    </AuthProvider>
  )
}
```

### Protected Routes

Use the `ProtectedRoute` component to guard authenticated pages:

```tsx
<Route element={<ProtectedRoute />}>
  <Route path="dashboard" element={<DashboardPage />} />
  <Route path="profile" element={<ProfilePage />} />
</Route>
```

### Using Auth Hooks

Access authentication state and methods with hooks:

```tsx
import { useAuth } from '@auth-kit/react'

function Component() {
  const { user, isAuthenticated, login, logout } = useAuth()
  // ...
}
```

### Pre-built Components

The example uses several pre-built components from `@auth-kit/react`:

- `LoginForm` - Complete login form with passkey support
- `RegisterForm` - Registration form with validation
- `UpdateProfileForm` - Profile update form
- `ChangePasswordForm` - Password change form
- `PasskeyList` - Manage user passkeys
- `TwoFactorSetup` - Enable 2FA

## Customization

All components accept customization props:

- `className` - Custom CSS classes
- `onSuccess` - Success callback
- `onError` - Error callback
- Various feature flags (e.g., `showPasskey`, `showRememberMe`)

## Production Considerations

1. **API URL**: Update the `apiUrl` in auth configuration
2. **HTTPS**: Ensure your production site uses HTTPS (required for passkeys)
3. **Storage**: Consider using secure storage options
4. **Error Handling**: Implement comprehensive error handling
5. **Loading States**: Add loading indicators for better UX

## Next Steps

- Implement email verification flow
- Add password reset functionality
- Integrate social login providers
- Add session management UI
- Implement remember me functionality