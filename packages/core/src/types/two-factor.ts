/**
 * Two-Factor Authentication types
 */

export interface TwoFactorSetupResponse {
  secret: string;
  qrCode: string;
  manualEntryKey: string;
  message?: string;
}

export interface TwoFactorEnableResponse {
  recoveryCodes: string[];
  message: string;
}

export interface TwoFactorVerifyRequest {
  code: string;
  isRecoveryCode?: boolean;
}

export interface TwoFactorDisableRequest {
  password: string;
}

export interface RecoveryCodesResponse {
  recoveryCodes: string[];
  message: string;
}

export interface TwoFactorStatus {
  enabled: boolean;
  method?: 'totp' | 'sms' | 'email';
  backedUpAt?: string;
  recoveryCodesRemaining?: number;
}