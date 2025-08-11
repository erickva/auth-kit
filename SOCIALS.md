# Social Login (OAuth) Implementation Guide

This document outlines the implementation plan for adding social login support to Auth Kit.

## Current State

Social login is currently scaffolded but not implemented:

- ✅ Configuration types defined in `AuthConfig`
- ✅ CLI mentions social login as an option
- ✅ Provider list defined (Google, GitHub, Facebook, Microsoft, Apple)
- ❌ No OAuth flow implementation
- ❌ No provider services
- ❌ No UI components
- ❌ No database schema for social accounts

## Implementation Plan

### Phase 1: Backend Foundation

#### 1.1 Database Schema

Create new tables and relationships:

```sql
-- Social provider accounts linked to users
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    avatar_url TEXT,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);

-- OAuth state for CSRF protection
CREATE TABLE oauth_states (
    state VARCHAR(255) PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    redirect_uri TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

#### 1.2 OAuth Service Architecture

```python
# auth_kit_fastapi/services/oauth/base.py
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

class OAuthProvider(ABC):
    """Base class for OAuth providers"""
    
    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get the OAuth authorization URL"""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for access token"""
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from provider"""
        pass
    
    @abstractmethod
    def extract_user_data(self, provider_data: Dict) -> Tuple[str, str, Optional[str]]:
        """Extract (id, email, name) from provider data"""
        pass
```

#### 1.3 Provider Implementations

```python
# auth_kit_fastapi/services/oauth/providers/google.py
import httpx
from typing import Dict, Optional, Tuple
from ..base import OAuthProvider

class GoogleOAuthProvider(OAuthProvider):
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        # Build URL with params
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    def extract_user_data(self, provider_data: Dict) -> Tuple[str, str, Optional[str]]:
        return (
            provider_data["id"],
            provider_data["email"],
            provider_data.get("name")
        )
```

Similar implementations for:
- `GitHubOAuthProvider`
- `FacebookOAuthProvider`
- `MicrosoftOAuthProvider`
- `AppleOAuthProvider`

#### 1.4 API Endpoints

```python
# auth_kit_fastapi/api/oauth.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import secrets
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    redirect_uri: str = Query(...),
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Initiate OAuth flow"""
    # Validate provider
    if provider not in config.get_social_providers():
        raise HTTPException(status_code=400, detail="Provider not supported")
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Store state in database
    oauth_state = OAuthState(
        state=state,
        provider=provider,
        redirect_uri=redirect_uri,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(oauth_state)
    db.commit()
    
    # Get provider service
    provider_service = get_oauth_provider(provider, config)
    auth_url = provider_service.get_authorization_url(state, redirect_uri)
    
    return {"authorization_url": auth_url}

@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    config = Depends(get_config)
):
    """Handle OAuth callback"""
    # Verify state
    oauth_state = db.query(OAuthState).filter(
        OAuthState.state == state,
        OAuthState.provider == provider,
        OAuthState.expires_at > datetime.utcnow()
    ).first()
    
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    # Exchange code for token
    provider_service = get_oauth_provider(provider, config)
    token_data = await provider_service.exchange_code_for_token(
        code, oauth_state.redirect_uri
    )
    
    # Get user info
    user_info = await provider_service.get_user_info(token_data["access_token"])
    provider_user_id, email, name = provider_service.extract_user_data(user_info)
    
    # Check if social account exists
    social_account = db.query(SocialAccount).filter(
        SocialAccount.provider == provider,
        SocialAccount.provider_user_id == provider_user_id
    ).first()
    
    if social_account:
        # Existing social account - log them in
        user = social_account.user
    else:
        # New social account - check if user with email exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                first_name=name.split()[0] if name else None,
                last_name=" ".join(name.split()[1:]) if name and len(name.split()) > 1 else None,
                is_active=True,
                email_verified=True  # Trust OAuth provider's email
            )
            db.add(user)
            db.flush()
        
        # Link social account
        social_account = SocialAccount(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            expires_at=datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600)),
            raw_data=user_info
        )
        db.add(social_account)
    
    # Clean up state
    db.delete(oauth_state)
    db.commit()
    
    # Generate auth tokens
    access_token = create_access_token(user_id=str(user.id))
    refresh_token = create_refresh_token(user_id=str(user.id))
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": UserResponse.from_orm(user)
    }

@router.delete("/oauth/{provider}/disconnect")
async def oauth_disconnect(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect a social account"""
    # Check if user has a password set
    if not current_user.password_hash:
        # Count remaining social accounts
        social_count = db.query(SocialAccount).filter(
            SocialAccount.user_id == current_user.id
        ).count()
        
        if social_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot disconnect last social account without a password"
            )
    
    # Find and delete social account
    social_account = db.query(SocialAccount).filter(
        SocialAccount.user_id == current_user.id,
        SocialAccount.provider == provider
    ).first()
    
    if not social_account:
        raise HTTPException(status_code=404, detail="Social account not found")
    
    db.delete(social_account)
    db.commit()
    
    return {"message": f"{provider} account disconnected"}
```

### Phase 2: Frontend Implementation

#### 2.1 React Components

```tsx
// packages/react/src/components/SocialLoginButtons.tsx
import React from 'react'
import { useAuth } from '../hooks/useAuth'

interface SocialLoginButtonsProps {
  providers?: string[]
  redirectUri?: string
  onSuccess?: () => void
  onError?: (error: Error) => void
}

export function SocialLoginButtons({
  providers = ['google', 'github', 'facebook'],
  redirectUri = window.location.origin + '/auth/callback',
  onSuccess,
  onError
}: SocialLoginButtonsProps) {
  const { apiUrl } = useAuth()
  
  const handleSocialLogin = async (provider: string) => {
    try {
      const response = await fetch(
        `${apiUrl}/api/auth/oauth/${provider}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`
      )
      const data = await response.json()
      
      // Redirect to OAuth provider
      window.location.href = data.authorization_url
    } catch (error) {
      onError?.(error as Error)
    }
  }
  
  return (
    <div className="social-login-buttons">
      {providers.includes('google') && (
        <button
          onClick={() => handleSocialLogin('google')}
          className="social-button google"
        >
          <GoogleIcon />
          Continue with Google
        </button>
      )}
      {providers.includes('github') && (
        <button
          onClick={() => handleSocialLogin('github')}
          className="social-button github"
        >
          <GitHubIcon />
          Continue with GitHub
        </button>
      )}
      {providers.includes('facebook') && (
        <button
          onClick={() => handleSocialLogin('facebook')}
          className="social-button facebook"
        >
          <FacebookIcon />
          Continue with Facebook
        </button>
      )}
    </div>
  )
}
```

```tsx
// packages/react/src/components/OAuthCallback.tsx
import React, { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login, apiUrl } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const provider = window.location.pathname.split('/').pop()
      
      if (!code || !state) {
        setError('Missing authorization code or state')
        setLoading(false)
        return
      }
      
      try {
        const response = await fetch(
          `${apiUrl}/api/auth/oauth/${provider}/callback?code=${code}&state=${state}`
        )
        
        if (!response.ok) {
          throw new Error('OAuth callback failed')
        }
        
        const data = await response.json()
        
        // Log the user in
        await login({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          user: data.user
        })
        
        // Redirect to dashboard or intended destination
        navigate('/dashboard')
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
    }
    
    handleCallback()
  }, [searchParams, navigate, login, apiUrl])
  
  if (loading) {
    return <div>Completing sign in...</div>
  }
  
  if (error) {
    return (
      <div>
        <h2>Sign in failed</h2>
        <p>{error}</p>
        <button onClick={() => navigate('/login')}>
          Back to login
        </button>
      </div>
    )
  }
  
  return null
}
```

#### 2.2 React Hooks

```tsx
// packages/react/src/hooks/useSocialLogin.ts
import { useState } from 'react'
import { useAuth } from './useAuth'

export function useSocialLogin() {
  const { apiUrl } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  
  const loginWithProvider = async (
    provider: string,
    redirectUri: string = window.location.origin + '/auth/callback'
  ) => {
    setIsLoading(true)
    setError(null)
    
    try {
      const response = await fetch(
        `${apiUrl}/api/auth/oauth/${provider}/authorize?redirect_uri=${encodeURIComponent(redirectUri)}`
      )
      
      if (!response.ok) {
        throw new Error('Failed to initiate OAuth flow')
      }
      
      const data = await response.json()
      window.location.href = data.authorization_url
    } catch (err) {
      setError(err as Error)
      setIsLoading(false)
    }
  }
  
  return {
    loginWithProvider,
    isLoading,
    error,
    loginWithGoogle: (redirectUri?: string) => loginWithProvider('google', redirectUri),
    loginWithGitHub: (redirectUri?: string) => loginWithProvider('github', redirectUri),
    loginWithFacebook: (redirectUri?: string) => loginWithProvider('facebook', redirectUri),
  }
}
```

### Phase 3: Configuration Updates

#### 3.1 Backend Configuration

```python
# auth_kit_fastapi/core/config.py
class AuthConfig(BaseSettings):
    # ... existing fields ...
    
    # OAuth Provider Settings
    oauth_providers: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    
    @validator('oauth_providers')
    def validate_oauth_providers(cls, v):
        """Validate OAuth provider configuration"""
        required_fields = ['client_id', 'client_secret']
        
        for provider, config in v.items():
            if provider not in ['google', 'github', 'facebook', 'microsoft', 'apple']:
                raise ValueError(f"Unknown OAuth provider: {provider}")
            
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing {field} for {provider} OAuth provider")
        
        return v
    
    class Config:
        env_nested_delimiter = '__'  # Allows OAUTH_PROVIDERS__GOOGLE__CLIENT_ID
```

#### 3.2 Environment Variables

```env
# OAuth Providers
OAUTH_PROVIDERS__GOOGLE__CLIENT_ID=your-google-client-id
OAUTH_PROVIDERS__GOOGLE__CLIENT_SECRET=your-google-client-secret

OAUTH_PROVIDERS__GITHUB__CLIENT_ID=your-github-client-id
OAUTH_PROVIDERS__GITHUB__CLIENT_SECRET=your-github-client-secret

OAUTH_PROVIDERS__FACEBOOK__CLIENT_ID=your-facebook-app-id
OAUTH_PROVIDERS__FACEBOOK__CLIENT_SECRET=your-facebook-app-secret
```

### Phase 4: CLI Updates

Update the CLI to properly handle social login configuration:

```typescript
// packages/cli/src/utils/env.ts
if (config.features.includes('socialLogin')) {
  // Add OAuth provider templates
  backendEnv['# OAuth Providers'] = ''
  backendEnv['# Google OAuth'] = ''
  backendEnv['OAUTH_PROVIDERS__GOOGLE__CLIENT_ID'] = 'your-google-client-id'
  backendEnv['OAUTH_PROVIDERS__GOOGLE__CLIENT_SECRET'] = 'your-google-client-secret'
  backendEnv['# GitHub OAuth'] = ''
  backendEnv['OAUTH_PROVIDERS__GITHUB__CLIENT_ID'] = 'your-github-client-id'
  backendEnv['OAUTH_PROVIDERS__GITHUB__CLIENT_SECRET'] = 'your-github-client-secret'
}
```

## Security Considerations

### 1. CSRF Protection
- Use state parameter for all OAuth flows
- Validate state on callback
- Expire states after 10 minutes

### 2. Token Security
- Store OAuth tokens encrypted in database
- Implement token refresh when needed
- Clear expired tokens regularly

### 3. Account Linking
- Verify email ownership before linking accounts
- Allow users to manage linked accounts
- Prevent account takeover attacks

### 4. Provider Security
- Always use HTTPS for callbacks
- Validate redirect URIs
- Implement proper error handling

## Provider-Specific Setup

### Google OAuth 2.0
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs
6. Copy Client ID and Client Secret

### GitHub OAuth
1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Click "New OAuth App"
3. Fill in application details
4. Add callback URL: `https://yourapp.com/auth/callback/github`
5. Copy Client ID and Client Secret

### Facebook Login
1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Add Facebook Login product
4. Configure OAuth redirect URIs
5. Copy App ID and App Secret

### Microsoft Identity Platform
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register new application
3. Add redirect URIs
4. Create client secret
5. Copy Application ID and Client Secret

## Testing Social Login

### Local Development
Use ngrok or similar to test OAuth locally:
```bash
ngrok http 3000
# Use the HTTPS URL for OAuth redirect URIs
```

### Test Scenarios
1. New user registration via social login
2. Existing user linking social account
3. Multiple social accounts per user
4. Disconnecting social accounts
5. Email conflict handling
6. Token refresh flows

## Migration Path

For existing Auth Kit users to add social login:

1. Run database migrations to add social_accounts table
2. Update configuration with OAuth providers
3. Add social login buttons to UI
4. Set up OAuth apps with providers
5. Test thoroughly before enabling in production

## Future Enhancements

- [ ] Social login analytics
- [ ] Provider-specific features (e.g., Google Calendar access)
- [ ] Social account merging
- [ ] Enterprise SSO support (SAML, OpenID Connect)
- [ ] Social login rate limiting
- [ ] A/B testing for social login buttons