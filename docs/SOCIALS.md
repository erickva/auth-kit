# Social OAuth Integration

Auth Kit provides built-in support for OAuth/social login with Google, GitHub, and Apple. This document covers the implementation details, configuration, and usage.

## Overview

The social OAuth implementation uses:
- **PKCE S256** (Proof Key for Code Exchange) for secure authorization code flows
- **AES-256-GCM** encrypted token storage for OAuth tokens at rest
- **JWT-signed state tokens** for CSRF protection (no database table required)
- **Account linking/unlinking** with lockout prevention

## Flow Diagram

```
┌──────────────┐     1. Click "Login with Google"     ┌──────────────┐
│              │ ─────────────────────────────────────▶│              │
│   Frontend   │                                       │   Backend    │
│   (React)    │◀───────────────────────────────────── │   (FastAPI)  │
│              │     2. Returns authorization_url      │              │
└──────┬───────┘         + state (JWT)                 └──────────────┘
       │
       │ 3. Redirect to provider
       ▼
┌──────────────┐
│   Provider   │
│  (Google)    │
└──────┬───────┘
       │
       │ 4. Callback with code + state
       ▼
┌──────────────┐     5. POST code, state, verifier    ┌──────────────┐
│              │ ─────────────────────────────────────▶│              │
│   Frontend   │                                       │   Backend    │
│  (Callback)  │◀───────────────────────────────────── │   (FastAPI)  │
│              │     6. Returns user + tokens          │              │
└──────────────┘                                       └──────────────┘
```

## Environment Variables

### Required Variables

```env
# Encryption key for OAuth tokens (32 bytes, base64 encoded)
# Generate with: python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
OAUTH_TOKEN_ENCRYPTION_KEY=your-32-byte-base64-key

# State signing key (defaults to JWT_SECRET if not set)
OAUTH_STATE_SIGNING_KEY=optional-separate-key
```

### Provider Configuration

#### Google OAuth

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Navigate to APIs & Services > Credentials
4. Create OAuth 2.0 Client ID (Web application)
5. Add authorized redirect URI: `https://your-domain.com/auth/callback`

#### GitHub OAuth

```env
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set Authorization callback URL: `https://your-domain.com/auth/callback`

#### Apple Sign In

```env
APPLE_CLIENT_ID=your-apple-service-id
APPLE_TEAM_ID=your-apple-team-id
APPLE_KEY_ID=your-apple-key-id
APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
```

1. Go to [Apple Developer Portal](https://developer.apple.com/)
2. Create a Services ID (this is your client_id)
3. Create a Sign In with Apple key
4. Configure domains and redirect URIs

## API Endpoints

### GET /auth/oauth/providers

Returns list of available OAuth providers.

**Response:**
```json
{
  "providers": [
    {"name": "google", "display_name": "Google", "enabled": true},
    {"name": "github", "display_name": "GitHub", "enabled": true},
    {"name": "apple", "display_name": "Apple", "enabled": false}
  ]
}
```

### POST /auth/oauth/{provider}/authorize

Initiates OAuth flow. Returns authorization URL to redirect user.

**Request:**
```json
{
  "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
  "redirect_uri": "https://your-app.com/auth/callback",
  "mode": "login"  // or "link" for account linking
}
```

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
}
```

### POST /auth/oauth/{provider}/callback

Exchanges authorization code for tokens. Returns user and auth tokens.

**Request:**
```json
{
  "code": "authorization-code-from-provider",
  "state": "state-from-authorize",
  "code_verifier": "original-pkce-verifier",
  "redirect_uri": "https://your-app.com/auth/callback"
}
```

**Response (login mode):**
```json
{
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_verified": true
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "refresh-token",
    "token_type": "Bearer",
    "expires_in": 3600
  },
  "is_new_user": false,
  "message": "Login successful"
}
```

### GET /auth/oauth/links

Returns linked social accounts for authenticated user.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "accounts": [
    {
      "provider": "google",
      "provider_user_id": "google-user-id",
      "provider_email": "user@gmail.com",
      "provider_username": null,
      "linked_at": "2024-01-15T10:30:00Z"
    }
  ],
  "has_usable_password": true
}
```

### POST /auth/oauth/links/{provider}/link

Links a social account to authenticated user.

**Headers:** `Authorization: Bearer <access_token>`

**Request:** Same as callback endpoint

**Response:**
```json
{
  "message": "Account linked successfully",
  "account": {
    "provider": "github",
    "provider_user_id": "github-user-id",
    "provider_email": "user@github.com",
    "linked_at": "2024-01-15T10:35:00Z"
  }
}
```

### DELETE /auth/oauth/links/{provider}

Unlinks a social account.

**Headers:** `Authorization: Bearer <access_token>`

**Response:**
```json
{
  "message": "Account unlinked successfully"
}
```

**Error (lockout prevention):**
```json
{
  "detail": "Cannot unlink: this is your only authentication method"
}
```

## Account Linking Rules

### Lockout Prevention

Users cannot unlink their last authentication method. The system checks:

```
remaining_auth_methods = (
  remaining_social_accounts +
  passkey_count +
  (1 if has_usable_password else 0)
)

if remaining_auth_methods <= 1:
    raise HTTPException(400, "Cannot unlink: this is your only authentication method")
```

### has_usable_password Field

- `True` by default for users who registered with email/password
- `False` for users created via OAuth-only registration
- Used to determine if user can authenticate with password

### Email Verification Behavior

When a user is created via OAuth login:

- The `is_verified` field is set based on the OAuth provider's `email_verified` claim
- Google, GitHub, and Apple all return email verification status
- If the provider confirms the email is verified, the user is automatically marked as verified
- This avoids requiring users to verify emails that are already verified by the OAuth provider

## Token Encryption

OAuth provider tokens (access_token, refresh_token, id_token) are encrypted at rest using AES-256-GCM.

### Format

```
v1:<base64(nonce || ciphertext || tag)>
```

- `v1:` - Version prefix for future-proofing
- `nonce` - 12 random bytes
- `ciphertext` - Encrypted token
- `tag` - 16-byte authentication tag (included in ciphertext by GCM)

### Generating Encryption Key

```bash
# Python
python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# OpenSSL
openssl rand -base64 32
```

## React Usage

### Installation

The social login components are included in `@erickva/auth-kit-react`.

### SocialLoginButtons Component

```tsx
import { SocialLoginButtons } from '@erickva/auth-kit-react';

// Login page
function LoginPage() {
  return (
    <div>
      <h1>Sign In</h1>

      {/* Social login buttons */}
      <SocialLoginButtons
        mode="login"
        redirectUri="https://your-app.com/auth/callback"
        onError={(error) => console.error(error)}
      />

      {/* Or with customization */}
      <SocialLoginButtons
        mode="login"
        providers={['google', 'github']}  // Only show specific providers
        direction="horizontal"
        size="large"
        showLabels={true}
      />
    </div>
  );
}
```

### OAuthCallback Component

```tsx
import { OAuthCallback } from '@erickva/auth-kit-react';
import { useNavigate } from 'react-router-dom';

// Callback page (/auth/callback)
function CallbackPage() {
  const navigate = useNavigate();

  return (
    <OAuthCallback
      onSuccess={(user) => {
        console.log('Logged in as:', user.email);
        navigate('/dashboard');
      }}
      onError={(error) => {
        console.error('Login failed:', error);
        navigate('/login', { state: { error } });
      }}
      loadingComponent={<CustomSpinner />}
    />
  );
}
```

### useSocialLogin Hook

For custom implementations:

```tsx
import { useSocialLogin } from '@erickva/auth-kit-react';

function CustomSocialLogin() {
  const {
    providers,
    linkedAccounts,
    hasUsablePassword,
    isLoading,
    error,
    startLogin,
    startLink,
    completeOAuth,
    unlinkAccount
  } = useSocialLogin();

  // Start login flow
  const handleGoogleLogin = () => {
    startLogin('google', 'https://your-app.com/auth/callback');
  };

  // Link account (when authenticated)
  const handleLinkGitHub = () => {
    startLink('github', 'https://your-app.com/auth/callback');
  };

  // Unlink account
  const handleUnlink = async (provider) => {
    try {
      await unlinkAccount(provider);
    } catch (err) {
      if (err.message.includes('only authentication method')) {
        alert('Cannot unlink - this is your only login method!');
      }
    }
  };

  return (
    <div>
      {providers.map(p => (
        <button key={p.name} onClick={() => startLogin(p.name)}>
          Login with {p.displayName}
        </button>
      ))}
    </div>
  );
}
```

### Router Setup Example

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@erickva/auth-kit-react';
import { OAuthCallback } from '@erickva/auth-kit-react';

function App() {
  return (
    <AuthProvider config={authConfig}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<CallbackPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

function CallbackPage() {
  const navigate = useNavigate();
  return (
    <OAuthCallback
      onSuccess={() => navigate('/dashboard')}
      onError={(err) => navigate('/login', { state: { error: err } })}
    />
  );
}
```

## Database Schema

### social_accounts Table

```sql
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    provider_username VARCHAR(255),
    access_token_enc TEXT,
    refresh_token_enc TEXT,
    id_token_enc TEXT,
    token_type VARCHAR(50),
    scope TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(provider, provider_user_id),
    UNIQUE(user_id, provider)
);

CREATE INDEX ix_social_accounts_user_id ON social_accounts(user_id);
CREATE INDEX ix_social_accounts_provider ON social_accounts(provider);
```

### User Model Addition

```sql
ALTER TABLE users ADD COLUMN has_usable_password BOOLEAN DEFAULT TRUE;
```

## Security Considerations

1. **PKCE S256**: All OAuth flows use PKCE with SHA-256 code challenge to prevent authorization code interception attacks.

2. **State Token**: JWT-signed state tokens prevent CSRF attacks. State tokens:
   - Expire after 10 minutes
   - Are bound to the PKCE code challenge
   - Include the redirect URI for validation

3. **Token Encryption**: OAuth provider tokens are encrypted with AES-256-GCM before storage, preventing exposure if the database is compromised.

4. **Link Mode Security**: When linking accounts, the user ID is included in the JWT state to prevent CSRF-style account linking attacks.

5. **Lockout Prevention**: Users cannot remove their last authentication method, preventing account lockout.

6. **Server-side PKCE Binding**: The backend verifies that the `code_verifier` in the callback matches the `code_challenge` stored in the signed state JWT, preventing code injection attacks.

7. **Apple ID Token Verification**: Apple id_tokens are cryptographically verified using Apple's JWKS public keys (RS256). Keys are cached for 1 hour for performance.

## Troubleshooting

### "Invalid or expired OAuth state"

- The state token has expired (10 minute TTL)
- The user took too long to complete the OAuth flow
- Solution: Start the OAuth flow again

### "Provider mismatch"

- The callback was received for a different provider than expected
- This could indicate a CSRF attack or misconfiguration
- Solution: Verify redirect URIs are correct

### "Cannot unlink: this is your only authentication method"

- User is trying to remove their last login method
- Solution: Link another account or set a password first

### "PKCE verification failed"

- The code_verifier doesn't match the code_challenge
- Could be caused by session storage issues
- Solution: Clear browser storage and try again

### "A different {provider} account is already linked to this user"

- You're trying to link a provider account, but a different account from that provider is already linked
- Each user can only have one account linked per provider
- Solution: Unlink the existing account first, then link the new one

## Migration Guide

### From Previous Versions

1. Run the database migration:
   ```bash
   alembic upgrade head
   ```

2. Set the encryption key environment variable:
   ```bash
   export OAUTH_TOKEN_ENCRYPTION_KEY=$(python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())")
   ```

3. Configure at least one OAuth provider (Google, GitHub, or Apple)

4. Update your React app to include the OAuth callback route
