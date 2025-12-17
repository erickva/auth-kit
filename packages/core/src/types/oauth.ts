/**
 * OAuth / Social Login types used across Auth Kit packages
 */

/**
 * Supported OAuth providers
 */
export type OAuthProvider = 'google' | 'github' | 'apple';

/**
 * OAuth provider information
 */
export interface OAuthProviderInfo {
  name: OAuthProvider;
  displayName: string;
  enabled: boolean;
}

/**
 * OAuth authorization response from server
 */
export interface OAuthAuthorizeResponse {
  authorizationUrl: string;
  state: string;
  codeChallenge: string;
}

/**
 * OAuth callback request to exchange code for tokens
 */
export interface OAuthCallbackRequest {
  code: string;
  state: string;
  codeVerifier: string;
  redirectUri: string;
}

/**
 * Linked social account information
 */
export interface LinkedAccount {
  provider: OAuthProvider;
  providerUserId: string;
  providerEmail?: string;
  providerUsername?: string;
  linkedAt: string;
}

/**
 * PKCE data stored during OAuth flow
 */
export interface PKCEData {
  codeVerifier: string;
  codeChallenge: string;
  state: string;
  redirectUri: string;
  timestamp: number;
}

/**
 * OAuth state information stored in sessionStorage
 */
export interface OAuthStateData {
  provider: OAuthProvider;
  codeVerifier: string;
  redirectUri: string;
  mode: 'login' | 'link';
  returnUrl?: string;
  timestamp: number;
}
