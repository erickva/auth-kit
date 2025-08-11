import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { twoFactorAPI } from '../api/twoFactor';
import { TwoFactorSetupResponse, TwoFactorEnableResponse, authEvents } from '@auth-kit/core';

export interface Use2FAReturn {
  isEnabled: boolean;
  isLoading: boolean;
  error: string | null;
  setupData: TwoFactorSetupResponse | null;
  recoveryCodes: string[] | null;
  beginSetup: () => Promise<void>;
  verifySetup: (code: string) => Promise<void>;
  disable: (password: string) => Promise<void>;
  regenerateRecoveryCodes: (password: string) => Promise<void>;
}

export function use2FA(): Use2FAReturn {
  const { user, accessToken, updateUser, config } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);

  // Configure API with auth config
  useEffect(() => {
    twoFactorAPI.configure(config.api);
  }, [config.api]);

  const isEnabled = user?.twoFactorEnabled || false;

  const beginSetup = useCallback(async () => {
    if (!accessToken || !config.features?.twoFactor) {
      setError('Two-factor authentication is not available');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await twoFactorAPI.beginSetup(accessToken);
      setSetupData(response);
    } catch (err: any) {
      console.error('Failed to begin 2FA setup:', err);
      setError(err.message || 'Failed to begin 2FA setup');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, config.features?.twoFactor]);

  const verifySetup = useCallback(async (code: string) => {
    if (!accessToken || !setupData) {
      setError('Setup not initialized');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await twoFactorAPI.verifySetup(code, accessToken);
      setRecoveryCodes(response.recoveryCodes);
      setSetupData(null);
      
      // Update user state
      if (user) {
        updateUser({ ...user, twoFactorEnabled: true });
      }
      
      // Emit event
      authEvents.emit('2faEnabled');
    } catch (err: any) {
      console.error('Failed to verify 2FA setup:', err);
      setError(err.message || 'Invalid verification code');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, setupData, user, updateUser]);

  const disable = useCallback(async (password: string) => {
    if (!accessToken) {
      setError('Not authenticated');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await twoFactorAPI.disable(password, accessToken);
      
      // Update user state
      if (user) {
        updateUser({ ...user, twoFactorEnabled: false });
      }
      
      // Clear any stored data
      setSetupData(null);
      setRecoveryCodes(null);
      
      // Emit event
      authEvents.emit('2faDisabled');
    } catch (err: any) {
      console.error('Failed to disable 2FA:', err);
      setError(err.message || 'Failed to disable 2FA');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, user, updateUser]);

  const regenerateRecoveryCodes = useCallback(async (password: string) => {
    if (!accessToken) {
      setError('Not authenticated');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await twoFactorAPI.regenerateRecoveryCodes(password, accessToken);
      setRecoveryCodes(response.recoveryCodes);
    } catch (err: any) {
      console.error('Failed to regenerate recovery codes:', err);
      setError(err.message || 'Failed to regenerate recovery codes');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken]);

  return {
    isEnabled,
    isLoading,
    error,
    setupData,
    recoveryCodes,
    beginSetup,
    verifySetup,
    disable,
    regenerateRecoveryCodes
  };
}