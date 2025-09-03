import { useState, useCallback, useEffect } from 'react';
import { browserSupportsWebAuthn, startRegistration, startAuthentication } from '@simplewebauthn/browser';
import { useAuth } from '../contexts/AuthContext';
import { passkeyAPI } from '../api/passkey';
import { Passkey, authEvents } from '@erickva/auth-kit-core';

export interface UsePasskeyReturn {
  passkeys: Passkey[];
  isSupported: boolean;
  isLoading: boolean;
  error: string | null;
  registerPasskey: (name: string) => Promise<void>;
  authenticateWithPasskey: (email?: string) => Promise<void>;
  deletePasskey: (passkeyId: string) => Promise<void>;
  refreshPasskeys: () => Promise<void>;
}

export function usePasskey(): UsePasskeyReturn {
  const { accessToken, loginWithPasskey, config } = useAuth();
  const [passkeys, setPasskeys] = useState<Passkey[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);

  // Configure API with auth config
  useEffect(() => {
    passkeyAPI.configure(config.api);
  }, [config.api]);

  // Check if WebAuthn is supported
  useEffect(() => {
    setIsSupported(browserSupportsWebAuthn());
  }, []);

  // Fetch user's passkeys
  const refreshPasskeys = useCallback(async () => {
    if (!accessToken || !config.features?.passkeys) return;

    try {
      const response = await passkeyAPI.listPasskeys(accessToken);
      setPasskeys(response.passkeys);
    } catch (err) {
      console.error('Failed to fetch passkeys:', err);
    }
  }, [accessToken, config.features?.passkeys]);

  // Load passkeys on mount and when access token changes
  useEffect(() => {
    refreshPasskeys();
  }, [refreshPasskeys]);

  const registerPasskey = useCallback(async (name: string) => {
    if (!accessToken || !isSupported) {
      setError('Passkeys are not supported or user is not authenticated');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Get registration options from server
      const { options, challenge } = await passkeyAPI.beginRegistration(name, accessToken);
      
      // Start WebAuthn registration
      const registrationResponse = await startRegistration(options);
      
      // Complete registration with server
      await passkeyAPI.completeRegistration(
        name,
        registrationResponse,
        challenge,
        accessToken
      );
      
      // Refresh passkeys list
      await refreshPasskeys();
      
      // Emit event
      authEvents.emit('passkeyAdded', { name });
    } catch (err: any) {
      console.error('Passkey registration failed:', err);
      
      if (err.name === 'NotAllowedError') {
        setError('Registration was cancelled');
      } else {
        setError(err.message || 'Failed to register passkey');
      }
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, isSupported, refreshPasskeys]);

  const authenticateWithPasskey = useCallback(async (email?: string) => {
    if (!isSupported) {
      setError('Passkeys are not supported on this device');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Get authentication options from server
      const { options, challenge } = await passkeyAPI.beginAuthentication(email);
      
      // Start WebAuthn authentication
      const authResponse = await startAuthentication(options);
      
      // Complete authentication with server
      const loginResponse = await passkeyAPI.completeAuthentication(
        authResponse,
        challenge
      );
      
      // Use the loginWithPasskey method from AuthContext
      await loginWithPasskey(loginResponse);
      
      // Emit event
      authEvents.emit('login', loginResponse.user);
    } catch (err: any) {
      console.error('Passkey authentication failed:', err);
      
      if (err.name === 'NotAllowedError') {
        setError('Authentication was cancelled');
      } else if (err.message?.includes('No passkeys')) {
        setError('No passkeys found for this device');
      } else {
        setError(err.message || 'Passkey authentication failed');
      }
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [isSupported, loginWithPasskey]);

  const deletePasskey = useCallback(async (passkeyId: string) => {
    if (!accessToken) return;

    setIsLoading(true);
    setError(null);

    try {
      await passkeyAPI.deletePasskey(passkeyId, accessToken);
      
      // Refresh passkeys list
      await refreshPasskeys();
      
      // Emit event
      authEvents.emit('passkeyRemoved', { id: passkeyId });
    } catch (err: any) {
      console.error('Failed to delete passkey:', err);
      setError(err.message || 'Failed to delete passkey');
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, refreshPasskeys]);

  return {
    passkeys,
    isSupported,
    isLoading,
    error,
    registerPasskey,
    authenticateWithPasskey,
    deletePasskey,
    refreshPasskeys
  };
}