import React, { useState } from 'react';
import { useAuth } from '../hooks';
import { validateEmail, validatePassword, getPasswordStrength } from '@auth-kit/core';

export interface SignupFormProps {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  showPasswordStrength?: boolean;
  showTermsCheckbox?: boolean;
  termsUrl?: string;
  privacyUrl?: string;
  showLoginLink?: boolean;
  loginUrl?: string;
  className?: string;
  children?: React.ReactNode;
  submitButtonText?: string;
  fields?: Array<'firstName' | 'lastName' | 'phoneNumber'>;
}

export function SignupForm({
  onSuccess,
  onError,
  showPasswordStrength = true,
  showTermsCheckbox = true,
  termsUrl = '/terms',
  privacyUrl = '/privacy',
  showLoginLink = true,
  loginUrl = '/login',
  className = '',
  children,
  submitButtonText = 'Create Account',
  fields = ['firstName', 'lastName']
}: SignupFormProps) {
  const { register, error: authError, clearError } = useAuth();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    phoneNumber: '',
    acceptTerms: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const passwordStrength = showPasswordStrength ? getPasswordStrength(formData.password) : null;

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    // Email validation
    const emailValidation = validateEmail(formData.email);
    if (!emailValidation.isValid) {
      newErrors.email = emailValidation.errors[0];
    }
    
    // Password validation
    const passwordValidation = validatePassword(formData.password);
    if (!passwordValidation.isValid) {
      newErrors.password = passwordValidation.errors[0];
    }
    
    // Confirm password
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    // Required fields
    if (fields.includes('firstName') && !formData.firstName) {
      newErrors.firstName = 'First name is required';
    }
    
    if (fields.includes('lastName') && !formData.lastName) {
      newErrors.lastName = 'Last name is required';
    }
    
    // Terms acceptance
    if (showTermsCheckbox && !formData.acceptTerms) {
      newErrors.acceptTerms = 'You must accept the terms and conditions';
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
      await register({
        email: formData.email,
        password: formData.password,
        firstName: formData.firstName,
        lastName: formData.lastName,
        phoneNumber: formData.phoneNumber || undefined,
        acceptTerms: formData.acceptTerms
      });
      
      onSuccess?.();
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Registration failed');
      onError?.(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={className}>
      {fields.includes('firstName') && (
        <div className="auth-kit-form-group">
          <label htmlFor="firstName" className="auth-kit-label">
            First Name
          </label>
          <input
            id="firstName"
            type="text"
            value={formData.firstName}
            onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
            className="auth-kit-input"
            autoComplete="given-name"
            disabled={isLoading}
          />
          {errors.firstName && (
            <p className="auth-kit-error">{errors.firstName}</p>
          )}
        </div>
      )}

      {fields.includes('lastName') && (
        <div className="auth-kit-form-group">
          <label htmlFor="lastName" className="auth-kit-label">
            Last Name
          </label>
          <input
            id="lastName"
            type="text"
            value={formData.lastName}
            onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
            className="auth-kit-input"
            autoComplete="family-name"
            disabled={isLoading}
          />
          {errors.lastName && (
            <p className="auth-kit-error">{errors.lastName}</p>
          )}
        </div>
      )}

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

      {fields.includes('phoneNumber') && (
        <div className="auth-kit-form-group">
          <label htmlFor="phoneNumber" className="auth-kit-label">
            Phone Number
          </label>
          <input
            id="phoneNumber"
            type="tel"
            value={formData.phoneNumber}
            onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
            className="auth-kit-input"
            autoComplete="tel"
            disabled={isLoading}
          />
          {errors.phoneNumber && (
            <p className="auth-kit-error">{errors.phoneNumber}</p>
          )}
        </div>
      )}

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
          autoComplete="new-password"
          disabled={isLoading}
        />
        {errors.password && (
          <p className="auth-kit-error">{errors.password}</p>
        )}
        {showPasswordStrength && formData.password && passwordStrength && (
          <div className="auth-kit-password-strength">
            <div className="auth-kit-password-strength-bar">
              <div
                className="auth-kit-password-strength-fill"
                style={{
                  width: `${(passwordStrength.score / 4) * 100}%`,
                  backgroundColor: passwordStrength.color
                }}
              />
            </div>
            <p className="auth-kit-password-strength-label" style={{ color: passwordStrength.color }}>
              {passwordStrength.label}
            </p>
          </div>
        )}
      </div>

      <div className="auth-kit-form-group">
        <label htmlFor="confirmPassword" className="auth-kit-label">
          Confirm Password
        </label>
        <input
          id="confirmPassword"
          type="password"
          value={formData.confirmPassword}
          onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
          className="auth-kit-input"
          placeholder="••••••••"
          autoComplete="new-password"
          disabled={isLoading}
        />
        {errors.confirmPassword && (
          <p className="auth-kit-error">{errors.confirmPassword}</p>
        )}
      </div>

      {showTermsCheckbox && (
        <div className="auth-kit-form-group">
          <label className="auth-kit-checkbox-label">
            <input
              type="checkbox"
              checked={formData.acceptTerms}
              onChange={(e) => setFormData({ ...formData, acceptTerms: e.target.checked })}
              className="auth-kit-checkbox"
              disabled={isLoading}
            />
            <span>
              I agree to the{' '}
              <a href={termsUrl} className="auth-kit-link" target="_blank" rel="noopener noreferrer">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href={privacyUrl} className="auth-kit-link" target="_blank" rel="noopener noreferrer">
                Privacy Policy
              </a>
            </span>
          </label>
          {errors.acceptTerms && (
            <p className="auth-kit-error">{errors.acceptTerms}</p>
          )}
        </div>
      )}

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
        {isLoading ? 'Creating account...' : submitButtonText}
      </button>

      {showLoginLink && (
        <div className="auth-kit-form-footer">
          <span>
            Already have an account?{' '}
            <a href={loginUrl} className="auth-kit-link">
              Sign in
            </a>
          </span>
        </div>
      )}

      {children}
    </form>
  );
}