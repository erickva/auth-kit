import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider } from '../../contexts/AuthContext';
import { use2FA } from '../../hooks/use2FA';
import { StorageType } from '@erickva/auth-kit-core';

// Mock fetch
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('use2FA', () => {
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

  describe('getStatus', () => {
    it('should get 2FA status when authenticated', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      const mockStatus = {
        enabled: true,
        method: 'totp',
        backup_codes_remaining: 5,
        created_at: new Date().toISOString(),
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus,
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      await waitFor(() => {
        expect(result.current.status).toEqual(mockStatus);
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/status',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
        })
      );
    });

    it('should not get status when not authenticated', async () => {
      const { result } = renderHook(() => use2FA(), { wrapper });

      await waitFor(() => {
        expect(result.current.status).toEqual({
          enabled: false,
          method: null,
          backup_codes_remaining: null,
          created_at: null,
        });
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('setup2FA', () => {
    it('should setup 2FA successfully', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      // Mock setup begin response
      const mockSetupResponse = {
        secret: 'mock-secret',
        qr_code: 'data:image/png;base64,mockqrcode',
        manual_entry_key: 'MOCKSECRET',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSetupResponse,
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      let setupData: any;
      await act(async () => {
        setupData = await result.current.setup2FA();
      });

      expect(setupData).toEqual(mockSetupResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/setup/begin',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
        })
      );
    });

    it('should handle setup errors', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: '2FA already enabled' }),
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      await expect(
        act(async () => {
          await result.current.setup2FA();
        })
      ).rejects.toThrow('2FA already enabled');
    });
  });

  describe('verify2FA', () => {
    it('should verify 2FA setup successfully', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      const mockVerifyResponse = {
        recovery_codes: [
          'AAAA-BBBB',
          'CCCC-DDDD',
          'EEEE-FFFF',
          'GGGG-HHHH',
          'IIII-JJJJ',
          'KKKK-LLLL',
          'MMMM-NNNN',
          'OOOO-PPPP',
        ],
        message: 'Two-factor authentication has been enabled',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockVerifyResponse,
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      let recoveryCodes: string[];
      await act(async () => {
        recoveryCodes = await result.current.verify2FA('123456');
      });

      expect(recoveryCodes!).toEqual(mockVerifyResponse.recovery_codes);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/setup/verify',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
          body: JSON.stringify({ code: '123456' }),
        })
      );
    });

    it('should handle invalid verification code', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid verification code' }),
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      await expect(
        act(async () => {
          await result.current.verify2FA('000000');
        })
      ).rejects.toThrow('Invalid verification code');
    });
  });

  describe('verifyLogin2FA', () => {
    it('should verify 2FA login successfully', async () => {
      const mockLoginResponse = {
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
        json: async () => mockLoginResponse,
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      const response = await act(async () => {
        return await result.current.verifyLogin2FA('123456', 'temp-2fa-token');
      });

      expect(response).toEqual(mockLoginResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/verify/login',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer temp-2fa-token',
          }),
          body: JSON.stringify({ code: '123456', is_recovery_code: false }),
        })
      );
    });

    it('should verify with recovery code', async () => {
      const mockLoginResponse = {
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
        json: async () => mockLoginResponse,
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      await act(async () => {
        await result.current.verifyLogin2FA('AAAA-BBBB', 'temp-2fa-token', true);
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/verify/login',
        expect.objectContaining({
          body: JSON.stringify({ code: 'AAAA-BBBB', is_recovery_code: true }),
        })
      );
    });
  });

  describe('disable2FA', () => {
    it('should disable 2FA successfully', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Two-factor authentication has been disabled' }),
      } as Response);

      // Mock status refetch
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          enabled: false,
          method: null,
          backup_codes_remaining: null,
          created_at: null,
        }),
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      await act(async () => {
        await result.current.disable2FA('password123');
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/disable',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
          body: JSON.stringify({ password: 'password123' }),
        })
      );

      await waitFor(() => {
        expect(result.current.status.enabled).toBe(false);
      });
    });

    it('should handle incorrect password', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Incorrect password' }),
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      await expect(
        act(async () => {
          await result.current.disable2FA('wrong-password');
        })
      ).rejects.toThrow('Incorrect password');
    });
  });

  describe('regenerateRecoveryCodes', () => {
    it('should regenerate recovery codes successfully', async () => {
      localStorage.setItem('auth_token', 'mock-access-token');

      const mockNewCodes = [
        'ZZZZ-YYYY',
        'XXXX-WWWW',
        'VVVV-UUUU',
        'TTTT-SSSS',
        'RRRR-QQQQ',
        'PPPP-OOOO',
        'NNNN-MMMM',
        'LLLL-KKKK',
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          recovery_codes: mockNewCodes,
          message: 'New recovery codes have been generated',
        }),
      } as Response);

      const { result } = renderHook(() => use2FA(), { wrapper });

      let newCodes: string[];
      await act(async () => {
        newCodes = await result.current.regenerateRecoveryCodes('password123');
      });

      expect(newCodes!).toEqual(mockNewCodes);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/2fa/recovery-codes',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
          body: JSON.stringify({ password: 'password123' }),
        })
      );
    });
  });
});