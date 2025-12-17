import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { oauthAPI, OAuthProvidersResponse, OAuthLinksResponse } from '../api/oauth';
import {
  OAuthProvider,
  OAuthProviderInfo,
  LinkedAccount,
  OAuthStateData,
  LoginResponse,
  authEvents,
  DEFAULT_STORAGE_KEYS
} from '@erickva/auth-kit-core';

export interface UseSocialLoginReturn {
  providers: OAuthProviderInfo[];
  linkedAccounts: LinkedAccount[];
  hasUsablePassword: boolean;
  isLoading: boolean;
  error: string | null;
  startLogin: (provider: OAuthProvider, redirectUri?: string) => Promise<void>;
  startLink: (provider: OAuthProvider, redirectUri?: string) => Promise<void>;
  completeOAuth: (provider: OAuthProvider, code: string, state: string) => Promise<LoginResponse | null>;
  unlinkAccount: (provider: OAuthProvider) => Promise<void>;
  refreshProviders: () => Promise<void>;
  refreshLinkedAccounts: () => Promise<void>;
  clearError: () => void;
}

/**
 * Generate a cryptographically random string for PKCE code verifier
 */
function generateCodeVerifier(length: number = 64): string {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, byte => characters[byte % characters.length]).join('');
}

/**
 * Generate SHA-256 code challenge from verifier (PKCE S256)
 */
async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  // Convert to base64url encoding
  const base64 = btoa(String.fromCharCode(...new Uint8Array(digest)));
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Store OAuth state data in sessionStorage
 */
function storeOAuthState(state: string, data: OAuthStateData): void {
  const key = `${DEFAULT_STORAGE_KEYS.OAUTH_STATE_PREFIX}${state}`;
  sessionStorage.setItem(key, JSON.stringify(data));
}

/**
 * Retrieve and clear OAuth state data from sessionStorage
 */
function retrieveOAuthState(state: string): OAuthStateData | null {
  const key = `${DEFAULT_STORAGE_KEYS.OAUTH_STATE_PREFIX}${state}`;
  const data = sessionStorage.getItem(key);
  if (!data) return null;

  sessionStorage.removeItem(key);

  try {
    const parsed = JSON.parse(data) as OAuthStateData;
    // Check if state is expired (10 minutes)
    if (Date.now() - parsed.timestamp > 10 * 60 * 1000) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function useSocialLogin(): UseSocialLoginReturn {
  const { accessToken, loginWithPasskey, config } = useAuth();
  const [providers, setProviders] = useState<OAuthProviderInfo[]>([]);
  const [linkedAccounts, setLinkedAccounts] = useState<LinkedAccount[]>([]);
  const [hasUsablePassword, setHasUsablePassword] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Configure API with auth config
  useEffect(() => {
    oauthAPI.configure(config.api);
  }, [config.api]);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Fetch available providers
  const refreshProviders = useCallback(async () => {
    if (!config.features?.socialLogin?.length) return;

    try {
      const response = await oauthAPI.getProviders();
      setProviders(response.providers);
    } catch (err) {
      console.error('Failed to fetch OAuth providers:', err);
    }
  }, [config.features?.socialLogin]);

  // Fetch linked accounts (requires authentication)
  const refreshLinkedAccounts = useCallback(async () => {
    if (!accessToken) return;

    try {
      const response = await oauthAPI.getLinkedAccounts(accessToken);
      setLinkedAccounts(response.accounts);
      setHasUsablePassword(response.hasUsablePassword);
    } catch (err) {
      console.error('Failed to fetch linked accounts:', err);
    }
  }, [accessToken]);

  // Load providers on mount
  useEffect(() => {
    refreshProviders();
  }, [refreshProviders]);

  // Load linked accounts when authenticated
  useEffect(() => {
    if (accessToken) {
      refreshLinkedAccounts();
    }
  }, [accessToken, refreshLinkedAccounts]);

  /**
   * Start OAuth login flow (redirect to provider)
   */
  const startLogin = useCallback(async (
    provider: OAuthProvider,
    redirectUri?: string
  ) => {
    setIsLoading(true);
    setError(null);

    try {
      // Generate PKCE values
      const codeVerifier = generateCodeVerifier();
      const codeChallenge = await generateCodeChallenge(codeVerifier);

      // Default redirect URI to current origin + /auth/callback
      const finalRedirectUri = redirectUri || `${window.location.origin}/auth/callback`;

      // Get authorization URL from server
      const response = await oauthAPI.authorize(
        provider,
        codeChallenge,
        finalRedirectUri,
        'login'
      );

      // Store state data for callback
      storeOAuthState(response.state, {
        provider,
        codeVerifier,
        redirectUri: finalRedirectUri,
        mode: 'login',
        returnUrl: window.location.href,
        timestamp: Date.now()
      });

      // Redirect to provider
      window.location.href = response.authorizationUrl;
    } catch (err: any) {
      console.error('OAuth login failed:', err);
      setError(err.message || 'Failed to start login');
      setIsLoading(false);
      throw err;
    }
  }, []);

  /**
   * Start OAuth account linking flow (requires authentication)
   */
  const startLink = useCallback(async (
    provider: OAuthProvider,
    redirectUri?: string
  ) => {
    if (!accessToken) {
      setError('Must be authenticated to link accounts');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Generate PKCE values
      const codeVerifier = generateCodeVerifier();
      const codeChallenge = await generateCodeChallenge(codeVerifier);

      // Default redirect URI to current origin + /auth/callback
      const finalRedirectUri = redirectUri || `${window.location.origin}/auth/callback`;

      // Get authorization URL from server (with access token for link mode)
      const response = await oauthAPI.authorize(
        provider,
        codeChallenge,
        finalRedirectUri,
        'link',
        accessToken
      );

      // Store state data for callback
      storeOAuthState(response.state, {
        provider,
        codeVerifier,
        redirectUri: finalRedirectUri,
        mode: 'link',
        returnUrl: window.location.href,
        timestamp: Date.now()
      });

      // Redirect to provider
      window.location.href = response.authorizationUrl;
    } catch (err: any) {
      console.error('OAuth link failed:', err);
      setError(err.message || 'Failed to start account linking');
      setIsLoading(false);
      throw err;
    }
  }, [accessToken]);

  /**
   * Complete OAuth flow after callback
   * Call this from your callback page with the code and state from URL params
   */
  const completeOAuth = useCallback(async (
    provider: OAuthProvider,
    code: string,
    state: string
  ): Promise<LoginResponse | null> => {
    setIsLoading(true);
    setError(null);

    try {
      // Retrieve stored state
      const storedState = retrieveOAuthState(state);
      if (!storedState) {
        throw new Error('Invalid or expired OAuth state');
      }

      // Verify provider matches
      if (storedState.provider !== provider) {
        throw new Error('Provider mismatch');
      }

      if (storedState.mode === 'link') {
        // Link account flow
        if (!accessToken) {
          throw new Error('Must be authenticated to link accounts');
        }

        await oauthAPI.linkAccount(
          provider,
          code,
          state,
          storedState.codeVerifier,
          storedState.redirectUri,
          accessToken
        );

        // Refresh linked accounts
        await refreshLinkedAccounts();

        // Emit event
        authEvents.emit('passkeyAdded', { provider }); // Reuse passkey event for now

        setIsLoading(false);
        return null;
      } else {
        // Login flow
        const response = await oauthAPI.callback(
          provider,
          code,
          state,
          storedState.codeVerifier,
          storedState.redirectUri
        );

        // Use the loginWithPasskey method from AuthContext (reusing for OAuth)
        await loginWithPasskey(response);

        // Emit event
        authEvents.emit('login', response.user);

        setIsLoading(false);
        return response;
      }
    } catch (err: any) {
      console.error('OAuth callback failed:', err);
      setError(err.message || 'Failed to complete OAuth');
      setIsLoading(false);
      throw err;
    }
  }, [accessToken, loginWithPasskey, refreshLinkedAccounts]);

  /**
   * Unlink a social account
   */
  const unlinkAccount = useCallback(async (provider: OAuthProvider) => {
    if (!accessToken) {
      setError('Must be authenticated to unlink accounts');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await oauthAPI.unlinkAccount(provider, accessToken);

      // Refresh linked accounts
      await refreshLinkedAccounts();

      // Emit event
      authEvents.emit('passkeyRemoved', { provider }); // Reuse passkey event for now
    } catch (err: any) {
      console.error('Failed to unlink account:', err);
      setError(err.message || 'Failed to unlink account');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, refreshLinkedAccounts]);

  return {
    providers,
    linkedAccounts,
    hasUsablePassword,
    isLoading,
    error,
    startLogin,
    startLink,
    completeOAuth,
    unlinkAccount,
    refreshProviders,
    refreshLinkedAccounts,
    clearError
  };
}
