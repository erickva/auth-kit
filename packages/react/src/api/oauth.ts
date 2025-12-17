import {
  OAuthProvider,
  OAuthProviderInfo,
  OAuthAuthorizeResponse,
  LoginResponse,
  LinkedAccount,
  DEFAULT_ENDPOINTS,
  AuthConfig
} from '@erickva/auth-kit-core';

/**
 * OAuth providers list response
 */
export interface OAuthProvidersResponse {
  providers: OAuthProviderInfo[];
}

/**
 * OAuth linked accounts response
 */
export interface OAuthLinksResponse {
  accounts: LinkedAccount[];
  hasUsablePassword: boolean;
}

class OAuthAPI {
  private baseUrl: string = '';
  private endpoints: typeof DEFAULT_ENDPOINTS;
  private headers: Record<string, string> = {};
  private timeout: number = 30000;

  constructor() {
    this.endpoints = { ...DEFAULT_ENDPOINTS };
  }

  configure(apiConfig: AuthConfig['api']) {
    this.baseUrl = apiConfig.baseUrl;
    this.endpoints = { ...DEFAULT_ENDPOINTS, ...apiConfig.endpoints };
    this.headers = apiConfig.headers || {};
    this.timeout = apiConfig.timeout || 30000;
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}, accessToken?: string) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const headers: Record<string, string> = {
        ...this.headers,
        ...options.headers as Record<string, string>
      };

      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
      }

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        const errorMessage = typeof error.detail === 'string'
          ? error.detail
          : error.message || 'Request failed';
        throw new Error(errorMessage);
      }

      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  /**
   * Get available OAuth providers
   */
  async getProviders(): Promise<OAuthProvidersResponse> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.OAUTH_PROVIDERS}`
    );
    return response.json();
  }

  /**
   * Start OAuth authorization flow
   * Returns the authorization URL and state to redirect to
   */
  async authorize(
    provider: OAuthProvider,
    codeChallenge: string,
    redirectUri: string,
    mode: 'login' | 'link' = 'login',
    accessToken?: string
  ): Promise<OAuthAuthorizeResponse> {
    const url = `${this.baseUrl}${this.endpoints.OAUTH_AUTHORIZE.replace(':provider', provider)}`;

    const response = await this.fetchWithAuth(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code_challenge: codeChallenge,
          redirect_uri: redirectUri,
          mode
        }),
      },
      accessToken
    );

    const data = await response.json();
    return {
      authorizationUrl: data.authorization_url,
      state: data.state,
      codeChallenge: data.code_challenge
    };
  }

  /**
   * Complete OAuth flow by exchanging code for tokens
   */
  async callback(
    provider: OAuthProvider,
    code: string,
    state: string,
    codeVerifier: string,
    redirectUri: string
  ): Promise<LoginResponse> {
    const url = `${this.baseUrl}${this.endpoints.OAUTH_CALLBACK.replace(':provider', provider)}`;

    const response = await this.fetchWithAuth(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          state,
          code_verifier: codeVerifier,
          redirect_uri: redirectUri
        }),
      }
    );

    const data = await response.json();
    // Normalize response to match LoginResponse interface
    return {
      user: data.user,
      tokens: {
        accessToken: data.tokens.access_token,
        refreshToken: data.tokens.refresh_token,
        tokenType: data.tokens.token_type || 'Bearer',
        expiresIn: data.tokens.expires_in
      },
      message: data.message
    };
  }

  /**
   * Get linked social accounts for authenticated user
   */
  async getLinkedAccounts(accessToken: string): Promise<OAuthLinksResponse> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.OAUTH_LINKS}`,
      {},
      accessToken
    );

    const data = await response.json();
    return {
      accounts: data.accounts.map((acc: any) => ({
        provider: acc.provider,
        providerUserId: acc.provider_user_id,
        providerEmail: acc.provider_email,
        providerUsername: acc.provider_username,
        linkedAt: acc.linked_at
      })),
      hasUsablePassword: data.has_usable_password
    };
  }

  /**
   * Link a social account to authenticated user
   */
  async linkAccount(
    provider: OAuthProvider,
    code: string,
    state: string,
    codeVerifier: string,
    redirectUri: string,
    accessToken: string
  ): Promise<{ message: string; account: LinkedAccount }> {
    const url = `${this.baseUrl}${this.endpoints.OAUTH_LINK_PROVIDER.replace(':provider', provider)}`;

    const response = await this.fetchWithAuth(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code,
          state,
          code_verifier: codeVerifier,
          redirect_uri: redirectUri
        }),
      },
      accessToken
    );

    const data = await response.json();
    return {
      message: data.message,
      account: {
        provider: data.account.provider,
        providerUserId: data.account.provider_user_id,
        providerEmail: data.account.provider_email,
        providerUsername: data.account.provider_username,
        linkedAt: data.account.linked_at
      }
    };
  }

  /**
   * Unlink a social account from authenticated user
   */
  async unlinkAccount(
    provider: OAuthProvider,
    accessToken: string
  ): Promise<{ message: string }> {
    const url = `${this.baseUrl}${this.endpoints.OAUTH_UNLINK_PROVIDER.replace(':provider', provider)}`;

    const response = await this.fetchWithAuth(
      url,
      {
        method: 'DELETE',
      },
      accessToken
    );

    return response.json();
  }
}

export const oauthAPI = new OAuthAPI();
