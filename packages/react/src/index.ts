/**
 * @auth-kit/react
 * 
 * React components and hooks for Auth Kit
 */

// Export context and provider
export { AuthProvider, useAuth } from './contexts/AuthContext';
export type { AuthProviderProps } from './contexts/AuthContext';

// Export all hooks
export * from './hooks';

// Export all components
export * from './components';

// Export API clients for advanced usage
export { authAPI } from './api/auth';
export { passkeyAPI } from './api/passkey';
export { twoFactorAPI } from './api/twoFactor';

// Re-export useful types from core
export type {
  User,
  AuthConfig,
  AuthState,
  AuthError,
  LoginCredentials,
  RegisterData,
  LoginResponse,
  AuthTokens,
  AuthEventType,
  AuthEvent
} from '@auth-kit/core';

// Package version
export const VERSION = '1.0.0';