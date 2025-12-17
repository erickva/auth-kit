/**
 * Default constants for Auth Kit
 */

// Storage keys
export const DEFAULT_STORAGE_KEYS = {
  ACCESS_TOKEN: 'auth_access_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USER: 'auth_user',
  RETURN_URL: 'auth_return_url',
  DEVICE_ID: 'auth_device_id',
  REMEMBER_ME: 'auth_remember_me',
  // OAuth PKCE storage prefix (state appended as suffix)
  OAUTH_PKCE_PREFIX: 'auth_oauth_pkce_',
  OAUTH_STATE_PREFIX: 'auth_oauth_state_'
} as const;

// API endpoints
export const DEFAULT_ENDPOINTS = {
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REGISTER: '/auth/register',
  REFRESH: '/auth/refresh',
  PROFILE: '/auth/me',
  PASSWORD_CHANGE: '/auth/password/change',
  PASSWORD_RESET: '/auth/password/reset',
  PASSWORD_RESET_CONFIRM: '/auth/password/reset/confirm',
  EMAIL_VERIFY: '/auth/verify-email',
  EMAIL_RESEND: '/auth/resend-verification',
  // Passkey endpoints
  PASSKEY_LIST: '/auth/passkeys',
  PASSKEY_REGISTER_BEGIN: '/auth/passkeys/register/begin',
  PASSKEY_REGISTER_COMPLETE: '/auth/passkeys/register/complete',
  PASSKEY_AUTH_BEGIN: '/auth/passkeys/authenticate/begin',
  PASSKEY_AUTH_COMPLETE: '/auth/passkeys/authenticate/complete',
  PASSKEY_DELETE: '/auth/passkeys/:id',
  // 2FA endpoints
  TWO_FACTOR_SETUP_BEGIN: '/auth/2fa/setup/begin',
  TWO_FACTOR_SETUP_VERIFY: '/auth/2fa/setup/verify',
  TWO_FACTOR_DISABLE: '/auth/2fa/disable',
  TWO_FACTOR_VERIFY_LOGIN: '/auth/2fa/verify/login',
  TWO_FACTOR_RECOVERY_CODES: '/auth/2fa/recovery-codes',
  // OAuth endpoints
  OAUTH_PROVIDERS: '/auth/oauth/providers',
  OAUTH_AUTHORIZE: '/auth/oauth/:provider/authorize',
  OAUTH_CALLBACK: '/auth/oauth/:provider/callback',
  OAUTH_LINKS: '/auth/oauth/links',
  OAUTH_LINK_PROVIDER: '/auth/oauth/links/:provider/link',
  OAUTH_UNLINK_PROVIDER: '/auth/oauth/links/:provider'
} as const;

// Token settings
export const TOKEN_SETTINGS = {
  ACCESS_TOKEN_BUFFER_SECONDS: 300, // 5 minutes
  REFRESH_RETRY_DELAY: 1000, // 1 second
  REFRESH_MAX_RETRIES: 3,
  TOKEN_TYPE: 'Bearer'
} as const;

// Validation settings
export const VALIDATION_SETTINGS = {
  PASSWORD_MIN_LENGTH: 8,
  PASSWORD_MAX_LENGTH: 128,
  EMAIL_MAX_LENGTH: 255,
  NAME_MIN_LENGTH: 2,
  NAME_MAX_LENGTH: 50,
  PHONE_MIN_LENGTH: 10,
  PHONE_MAX_LENGTH: 15,
  TOTP_CODE_LENGTH: 6,
  RECOVERY_CODE_FORMAT: /^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/
} as const;

// WebAuthn settings
export const WEBAUTHN_SETTINGS = {
  TIMEOUT_MS: 60000, // 1 minute
  USER_VERIFICATION: 'preferred' as const,
  AUTHENTICATOR_ATTACHMENT: 'platform' as const,
  RESIDENT_KEY: 'preferred' as const,
  ATTESTATION: 'none' as const
} as const;

// 2FA settings
export const TWO_FACTOR_SETTINGS = {
  TOTP_WINDOW: 1,
  TOTP_DIGITS: 6,
  TOTP_PERIOD: 30,
  RECOVERY_CODES_COUNT: 10,
  RECOVERY_CODE_LENGTH: 16
} as const;

// Error codes
export const ERROR_CODES = {
  // Authentication errors
  INVALID_CREDENTIALS: 'INVALID_CREDENTIALS',
  USER_NOT_FOUND: 'USER_NOT_FOUND',
  USER_INACTIVE: 'USER_INACTIVE',
  USER_NOT_VERIFIED: 'USER_NOT_VERIFIED',
  EMAIL_ALREADY_EXISTS: 'EMAIL_ALREADY_EXISTS',
  
  // Token errors
  INVALID_TOKEN: 'INVALID_TOKEN',
  TOKEN_EXPIRED: 'TOKEN_EXPIRED',
  REFRESH_TOKEN_EXPIRED: 'REFRESH_TOKEN_EXPIRED',
  
  // 2FA errors
  INVALID_2FA_CODE: 'INVALID_2FA_CODE',
  TWO_FACTOR_REQUIRED: 'TWO_FACTOR_REQUIRED',
  TWO_FACTOR_SETUP_REQUIRED: 'TWO_FACTOR_SETUP_REQUIRED',
  
  // Passkey errors
  PASSKEY_NOT_SUPPORTED: 'PASSKEY_NOT_SUPPORTED',
  PASSKEY_REGISTRATION_FAILED: 'PASSKEY_REGISTRATION_FAILED',
  PASSKEY_AUTHENTICATION_FAILED: 'PASSKEY_AUTHENTICATION_FAILED',

  // OAuth errors
  OAUTH_INVALID_STATE: 'OAUTH_INVALID_STATE',
  OAUTH_PROVIDER_ERROR: 'OAUTH_PROVIDER_ERROR',
  OAUTH_ACCOUNT_EXISTS: 'OAUTH_ACCOUNT_EXISTS',
  OAUTH_LINK_FAILED: 'OAUTH_LINK_FAILED',
  OAUTH_UNLINK_FAILED: 'OAUTH_UNLINK_FAILED',
  OAUTH_LAST_AUTH_METHOD: 'OAUTH_LAST_AUTH_METHOD',

  // Network errors
  NETWORK_ERROR: 'NETWORK_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  
  // Validation errors
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_EMAIL: 'INVALID_EMAIL',
  INVALID_PASSWORD: 'INVALID_PASSWORD',
  PASSWORD_TOO_WEAK: 'PASSWORD_TOO_WEAK'
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Successfully logged in',
  LOGOUT_SUCCESS: 'Successfully logged out',
  REGISTER_SUCCESS: 'Account created successfully',
  PASSWORD_CHANGED: 'Password changed successfully',
  PASSWORD_RESET_SENT: 'Password reset instructions sent to your email',
  EMAIL_VERIFIED: 'Email verified successfully',
  EMAIL_VERIFICATION_SENT: 'Verification email sent',
  TWO_FACTOR_ENABLED: 'Two-factor authentication enabled',
  TWO_FACTOR_DISABLED: 'Two-factor authentication disabled',
  PASSKEY_ADDED: 'Passkey added successfully',
  PASSKEY_REMOVED: 'Passkey removed successfully',
  OAUTH_ACCOUNT_LINKED: 'Social account linked successfully',
  OAUTH_ACCOUNT_UNLINKED: 'Social account unlinked successfully',
  OAUTH_LOGIN_SUCCESS: 'Successfully logged in with social account'
} as const;