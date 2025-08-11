/**
 * Validation utilities for authentication
 */

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

/**
 * Validate email address
 */
export function validateEmail(email: string): ValidationResult {
  const errors: string[] = [];
  
  if (!email) {
    errors.push('Email is required');
  } else {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      errors.push('Invalid email format');
    }
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate password strength
 */
export function validatePassword(
  password: string,
  options: {
    minLength?: number;
    requireUppercase?: boolean;
    requireLowercase?: boolean;
    requireNumbers?: boolean;
    requireSpecialChars?: boolean;
  } = {}
): ValidationResult {
  const {
    minLength = 8,
    requireUppercase = true,
    requireLowercase = true,
    requireNumbers = true,
    requireSpecialChars = true
  } = options;

  const errors: string[] = [];

  if (!password) {
    errors.push('Password is required');
    return { isValid: false, errors };
  }

  if (password.length < minLength) {
    errors.push(`Password must be at least ${minLength} characters long`);
  }

  if (requireUppercase && !/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (requireLowercase && !/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (requireNumbers && !/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  if (requireSpecialChars && !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate phone number
 */
export function validatePhoneNumber(phone: string): ValidationResult {
  const errors: string[] = [];
  
  if (!phone) {
    return { isValid: true, errors }; // Phone is optional
  }

  // Remove all non-digit characters for validation
  const digitsOnly = phone.replace(/\D/g, '');
  
  if (digitsOnly.length < 10 || digitsOnly.length > 15) {
    errors.push('Phone number must be between 10 and 15 digits');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate TOTP code
 */
export function validateTOTPCode(code: string): ValidationResult {
  const errors: string[] = [];
  
  if (!code) {
    errors.push('Verification code is required');
  } else if (!/^\d{6}$/.test(code)) {
    errors.push('Verification code must be 6 digits');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate recovery code
 */
export function validateRecoveryCode(code: string): ValidationResult {
  const errors: string[] = [];
  
  if (!code) {
    errors.push('Recovery code is required');
  } else if (!/^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(code.toUpperCase())) {
    errors.push('Invalid recovery code format');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Validate passkey name
 */
export function validatePasskeyName(name: string): ValidationResult {
  const errors: string[] = [];
  
  if (!name) {
    errors.push('Passkey name is required');
  } else if (name.length < 3) {
    errors.push('Passkey name must be at least 3 characters');
  } else if (name.length > 50) {
    errors.push('Passkey name must be less than 50 characters');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

/**
 * Password strength meter
 */
export function getPasswordStrength(password: string): {
  score: number; // 0-4
  label: 'Very Weak' | 'Weak' | 'Fair' | 'Good' | 'Strong';
  color: string;
} {
  let score = 0;
  
  if (!password) {
    return { score: 0, label: 'Very Weak', color: '#dc2626' };
  }

  // Length
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  
  // Complexity
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  // Penalize common patterns
  if (/(.)\1{2,}/.test(password)) score--; // Repeated characters
  if (/^(password|123456|qwerty)/i.test(password)) score = 0; // Common passwords

  score = Math.max(0, Math.min(4, score));

  const strengthMap = [
    { label: 'Very Weak' as const, color: '#dc2626' },
    { label: 'Weak' as const, color: '#f59e0b' },
    { label: 'Fair' as const, color: '#eab308' },
    { label: 'Good' as const, color: '#22c55e' },
    { label: 'Strong' as const, color: '#16a34a' }
  ];

  return {
    score,
    ...strengthMap[score]
  };
}