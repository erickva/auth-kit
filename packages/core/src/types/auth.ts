/**
 * Core authentication types used across Auth Kit packages
 */

export interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  fullName?: string;
  phoneNumber?: string;
  avatar?: string;
  role?: string;
  isActive: boolean;
  isVerified: boolean;
  isSuperuser?: boolean;
  twoFactorEnabled?: boolean;
  createdAt: string;
  updatedAt?: string;
  lastLoginAt?: string;
  metadata?: Record<string, any>;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
  tokenType: string;
  expiresIn?: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  acceptTerms?: boolean;
  metadata?: Record<string, any>;
}

export interface LoginResponse {
  user: User;
  tokens: AuthTokens;
  message?: string;
  requires2FA?: boolean;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  accessToken: string | null;
  error: AuthError | null;
}

export interface AuthError {
  code: string;
  message: string;
  details?: any;
}

export interface PasswordChangeData {
  currentPassword: string;
  newPassword: string;
}

export interface PasswordResetData {
  email: string;
}

export interface PasswordResetConfirmData {
  token: string;
  newPassword: string;
}

export interface EmailVerificationData {
  token: string;
}

export type AuthEventType = 
  | 'login'
  | 'logout'
  | 'register'
  | 'tokenRefresh'
  | 'tokenRefreshFailed'
  | 'passwordChange'
  | 'passwordReset'
  | 'emailVerified'
  | '2faEnabled'
  | '2faDisabled'
  | 'passkeyAdded'
  | 'passkeyRemoved';

export interface AuthEvent {
  type: AuthEventType;
  timestamp: Date;
  data?: any;
}

export interface AuthConfig {
  api: {
    baseUrl: string;
    endpoints?: {
      login?: string;
      logout?: string;
      register?: string;
      refresh?: string;
      profile?: string;
      passwordChange?: string;
      passwordReset?: string;
      passwordResetConfirm?: string;
      emailVerify?: string;
      emailResend?: string;
    };
    headers?: Record<string, string>;
    timeout?: number;
  };
  storage?: {
    tokenKey?: string;
    refreshTokenKey?: string;
    userKey?: string;
    driver?: 'localStorage' | 'sessionStorage' | 'cookie' | 'memory';
  };
  features?: {
    passkeys?: boolean;
    twoFactor?: boolean;
    emailVerification?: boolean;
    socialLogin?: string[];
    rememberMe?: boolean;
    sessionTimeout?: number;
  };
  events?: {
    onLogin?: (user: User) => void;
    onLogout?: () => void;
    onTokenRefresh?: (tokens: AuthTokens) => void;
    onAuthError?: (error: AuthError) => void;
  };
}