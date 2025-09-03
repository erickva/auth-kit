import React, { useState } from 'react';
import { useAuth, usePasskey } from '../hooks';
import { validateEmail, validatePassword } from '@erickva/auth-kit-core';

export interface LoginFormProps {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  showPasskey?: boolean;
  showRememberMe?: boolean;
  showForgotPassword?: boolean;
  showSignupLink?: boolean;
  signupUrl?: string;
  forgotPasswordUrl?: string;
  className?: string;
  children?: React.ReactNode;
  submitButtonText?: string;
  passkeyButtonText?: string;
}

export function LoginForm({
  onSuccess,
  onError,
  showPasskey = true,
  showRememberMe = true,
  showForgotPassword = true,
  showSignupLink = true,
  signupUrl = '/signup',
  forgotPasswordUrl = '/forgot-password',
  className = '',
  children,
  submitButtonText = 'Sign In',
  passkeyButtonText = 'Sign in with Passkey'
}: LoginFormProps) {
  const { login, verifyTwoFactor, config, error: authError, clearError } = useAuth();
  const { authenticateWithPasskey, isSupported: passkeySupported } = usePasskey();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // 2FA state
  const [show2FA, setShow2FA] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    const emailValidation = validateEmail(formData.email);
    if (!emailValidation.isValid) {
      newErrors.email = emailValidation.errors[0];
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    clearError();
    
    try {
      const response = await login({
        email: formData.email,
        password: formData.password,
        rememberMe: formData.rememberMe
      });
      
      if (response.requires2FA) {
        setTempToken(response.tokens.accessToken);
        setShow2FA(true);
      } else {
        onSuccess?.();
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Login failed');
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!twoFactorCode || twoFactorCode.length !== 6) {
      setErrors({ twoFactor: 'Please enter a 6-digit code' });
      return;
    }
    
    setIsLoading(true);
    clearError();
    
    try {
      await verifyTwoFactor(twoFactorCode, tempToken);
      onSuccess?.();
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Invalid verification code');
      setErrors({ twoFactor: err.message });
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasskeyLogin = async () => {
    setIsLoading(true);
    clearError();
    
    try {
      await authenticateWithPasskey(formData.email || undefined);
      onSuccess?.();
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Passkey authentication failed');
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  };

  if (show2FA) {
    return (
      <form onSubmit={handle2FASubmit} className={className}>
        <div className="auth-kit-form-group">
          <label htmlFor="twoFactorCode" className="auth-kit-label">
            Verification Code
          </label>
          <input
            id="twoFactorCode"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={twoFactorCode}
            onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ''))}
            className="auth-kit-input"
            placeholder="000000"
            autoComplete="one-time-code"
            disabled={isLoading}
          />
          {errors.twoFactor && (
            <p className="auth-kit-error">{errors.twoFactor}</p>
          )}
        </div>

        {authError && (
          <div className="auth-kit-alert auth-kit-alert-error">
            {authError.message}
          </div>
        )}

        <button
          type="submit"
          className="auth-kit-button auth-kit-button-primary"
          disabled={isLoading}
        >
          {isLoading ? 'Verifying...' : 'Verify'}
        </button>

        <button
          type="button"
          onClick={() => setShow2FA(false)}
          className="auth-kit-button auth-kit-button-text"
          disabled={isLoading}
        >
          Back to login
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="auth-kit-form-group">
        <label htmlFor="email" className="auth-kit-label">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          className="auth-kit-input"
          placeholder="you@example.com"
          autoComplete="email"
          disabled={isLoading}
        />
        {errors.email && (
          <p className="auth-kit-error">{errors.email}</p>
        )}
      </div>

      <div className="auth-kit-form-group">
        <label htmlFor="password" className="auth-kit-label">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          className="auth-kit-input"
          placeholder="••••••••"
          autoComplete="current-password"
          disabled={isLoading}
        />
        {errors.password && (
          <p className="auth-kit-error">{errors.password}</p>
        )}
      </div>

      {showRememberMe && config.features?.rememberMe !== false && (
        <div className="auth-kit-form-group">
          <label className="auth-kit-checkbox-label">
            <input
              type="checkbox"
              checked={formData.rememberMe}
              onChange={(e) => setFormData({ ...formData, rememberMe: e.target.checked })}
              className="auth-kit-checkbox"
              disabled={isLoading}
            />
            <span>Remember me</span>
          </label>
        </div>
      )}

      {authError && (
        <div className="auth-kit-alert auth-kit-alert-error">
          {authError.message}
        </div>
      )}

      <div className="auth-kit-form-actions">
        <button
          type="submit"
          className="auth-kit-button auth-kit-button-primary"
          disabled={isLoading}
        >
          {isLoading ? 'Signing in...' : submitButtonText}
        </button>

        {showPasskey && config.features?.passkeys && passkeySupported && (
          <button
            type="button"
            onClick={handlePasskeyLogin}
            className="auth-kit-button auth-kit-button-secondary"
            disabled={isLoading}
          >
            {passkeyButtonText}
          </button>
        )}
      </div>

      {(showForgotPassword || showSignupLink) && (
        <div className="auth-kit-form-footer">
          {showForgotPassword && (
            <a href={forgotPasswordUrl} className="auth-kit-link">
              Forgot password?
            </a>
          )}
          {showSignupLink && (
            <span>
              Don't have an account?{' '}
              <a href={signupUrl} className="auth-kit-link">
                Sign up
              </a>
            </span>
          )}
        </div>
      )}

      {children}
    </form>
  );
}