import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider } from '../../contexts/AuthContext';
import { usePasskey } from '../../hooks/usePasskey';
import { StorageType } from '@auth-kit/core';

// Mock WebAuthn API
const mockNavigatorCredentials = {
  create: jest.fn(),
  get: jest.fn(),
};

Object.defineProperty(window.navigator, 'credentials', {
  value: mockNavigatorCredentials,
  writable: true,
});

// Mock fetch
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('usePasskey', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider
      config={{
        apiUrl: 'http://localhost:3000',
        storageType: StorageType.LocalStorage,
      }}
    >
      {children}
    </AuthProvider>
  );

  describe('isSupported', () => {
    it('should detect WebAuthn support', () => {
      const { result } = renderHook(() => usePasskey(), { wrapper });
      expect(result.current.isSupported).toBe(true);
    });

    it('should handle missing WebAuthn support', () => {
      // Temporarily remove credentials
      const originalCredentials = window.navigator.credentials;
      Object.defineProperty(window.navigator, 'credentials', {
        value: undefined,
        writable: true,
      });

      const { result } = renderHook(() => usePasskey(), { wrapper });
      expect(result.current.isSupported).toBe(false);

      // Restore
      Object.defineProperty(window.navigator, 'credentials', {
        value: originalCredentials,
        writable: true,
      });
    });
  });

  describe('registerPasskey', () => {
    it('should register a passkey successfully', async () => {
      // Mock API responses
      const mockOptions = {
        challenge: 'mock-challenge',
        rp: { id: 'localhost', name: 'Test App' },
        user: { id: 'user-id', name: 'test@example.com', displayName: 'Test User' },
        pubKeyCredParams: [{ alg: -7, type: 'public-key' }],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'preferred',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOptions,
      } as Response);

      // Mock credential creation
      const mockCredential = {
        id: 'credential-id',
        rawId: new ArrayBuffer(32),
        response: {
          attestationObject: new ArrayBuffer(128),
          clientDataJSON: new ArrayBuffer(128),
          getPublicKey: () => new ArrayBuffer(65),
          getPublicKeyAlgorithm: () => -7,
          getTransports: () => ['internal'],
        },
        type: 'public-key',
      };

      mockNavigatorCredentials.create.mockResolvedValueOnce(mockCredential);

      // Mock registration completion
      const mockPasskey = {
        id: '1',
        name: 'My Passkey',
        createdAt: new Date().toISOString(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockPasskey,
      } as Response);

      const { result } = renderHook(() => usePasskey(), { wrapper });

      await act(async () => {
        await result.current.registerPasskey('My Passkey');
      });

      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(mockFetch).toHaveBeenNthCalledWith(
        1,
        'http://localhost:3000/passkeys/register/begin',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'My Passkey' }),
        })
      );

      expect(mockNavigatorCredentials.create).toHaveBeenCalledWith({
        publicKey: expect.objectContaining({
          challenge: expect.any(ArrayBuffer),
          rp: mockOptions.rp,
          user: expect.objectContaining({
            id: expect.any(ArrayBuffer),
            name: mockOptions.user.name,
            displayName: mockOptions.user.displayName,
          }),
        }),
      });

      expect(result.current.passkeys).toContainEqual(
        expect.objectContaining({
          id: '1',
          name: 'My Passkey',
        })
      );
    });

    it('should handle registration errors', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Registration failed' }),
      } as Response);

      const { result } = renderHook(() => usePasskey(), { wrapper });

      await expect(
        act(async () => {
          await result.current.registerPasskey('My Passkey');
        })
      ).rejects.toThrow('Registration failed');
    });
  });

  describe('authenticateWithPasskey', () => {
    it('should authenticate with passkey successfully', async () => {
      // Mock authentication options
      const mockOptions = {
        challenge: 'mock-challenge',
        rpId: 'localhost',
        userVerification: 'preferred',
        allowCredentials: [{
          id: 'credential-id',
          type: 'public-key',
          transports: ['internal'],
        }],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOptions,
      } as Response);

      // Mock credential get
      const mockAssertion = {
        id: 'credential-id',
        rawId: new ArrayBuffer(32),
        response: {
          authenticatorData: new ArrayBuffer(37),
          clientDataJSON: new ArrayBuffer(128),
          signature: new ArrayBuffer(64),
          userHandle: new ArrayBuffer(16),
        },
        type: 'public-key',
      };

      mockNavigatorCredentials.get.mockResolvedValueOnce(mockAssertion);

      // Mock authentication completion
      const mockAuthResponse = {
        user: { id: '1', email: 'test@example.com' },
        tokens: {
          access_token: 'mock-access-token',
          refresh_token: 'mock-refresh-token',
          token_type: 'bearer',
          expires_in: 3600,
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockAuthResponse,
      } as Response);

      const { result } = renderHook(() => usePasskey(), { wrapper });

      const response = await act(async () => {
        return await result.current.authenticateWithPasskey();
      });

      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(mockFetch).toHaveBeenNthCalledWith(
        1,
        'http://localhost:3000/passkeys/authenticate/begin',
        expect.objectContaining({
          method: 'POST',
        })
      );

      expect(mockNavigatorCredentials.get).toHaveBeenCalledWith({
        publicKey: expect.objectContaining({
          challenge: expect.any(ArrayBuffer),
          rpId: mockOptions.rpId,
          userVerification: mockOptions.userVerification,
        }),
      });

      expect(response).toEqual(mockAuthResponse);
    });

    it('should handle user cancellation', async () => {
      const mockOptions = {
        challenge: 'mock-challenge',
        rpId: 'localhost',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockOptions,
      } as Response);

      // Mock user cancellation
      mockNavigatorCredentials.get.mockRejectedValueOnce(
        new DOMException('User cancelled', 'NotAllowedError')
      );

      const { result } = renderHook(() => usePasskey(), { wrapper });

      await expect(
        act(async () => {
          await result.current.authenticateWithPasskey();
        })
      ).rejects.toThrow('User cancelled');
    });
  });

  describe('deletePasskey', () => {
    it('should delete a passkey successfully', async () => {
      // Setup initial passkeys
      const initialPasskeys = [
        { id: '1', name: 'Passkey 1', createdAt: new Date().toISOString() },
        { id: '2', name: 'Passkey 2', createdAt: new Date().toISOString() },
      ];

      localStorage.setItem('auth_token', 'mock-access-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ passkeys: initialPasskeys }),
      } as Response);

      const { result } = renderHook(() => usePasskey(), { wrapper });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.passkeys).toHaveLength(2);
      });

      // Mock delete response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Passkey deleted' }),
      } as Response);

      await act(async () => {
        await result.current.deletePasskey('1');
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/passkeys/1',
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
        })
      );

      expect(result.current.passkeys).toHaveLength(1);
      expect(result.current.passkeys[0].id).toBe('2');
    });
  });

  describe('loadPasskeys', () => {
    it('should load passkeys when authenticated', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      const mockPasskeys = [
        { id: '1', name: 'Passkey 1', createdAt: new Date().toISOString() },
        { id: '2', name: 'Passkey 2', createdAt: new Date().toISOString() },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ passkeys: mockPasskeys }),
      } as Response);

      const { result } = renderHook(() => usePasskey(), { wrapper });

      await waitFor(() => {
        expect(result.current.passkeys).toEqual(mockPasskeys);
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('should not load passkeys when not authenticated', async () => {
      const { result } = renderHook(() => usePasskey(), { wrapper });

      await waitFor(() => {
        expect(result.current.passkeys).toEqual([]);
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});