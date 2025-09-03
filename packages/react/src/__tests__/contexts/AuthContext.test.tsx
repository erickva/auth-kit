import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../contexts/AuthContext';
import { StorageType } from '@erickva/auth-kit-core';

// Mock fetch
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider
      config={{
        apiUrl: 'http://localhost:3000',
        storageType: StorageType.LocalStorage,
        tokenKey: 'auth_token',
        refreshTokenKey: 'refresh_token',
      }}
    >
      {children}
    </AuthProvider>
  );

  describe('useAuth hook', () => {
    it('should initialize with loading state', () => {
      const { result } = renderHook(() => useAuth(), { wrapper });
      
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should load user from storage on mount', async () => {
      const mockUser = { id: '1', email: 'test@example.com' };
      const mockToken = 'mock-access-token';
      
      localStorage.setItem('auth_token', mockToken);
      localStorage.setItem('auth_user', JSON.stringify(mockUser));

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.isAuthenticated).toBe(true);
        expect(result.current.user).toEqual(mockUser);
        expect(result.current.accessToken).toBe(mockToken);
      });
    });
  });

  describe('login', () => {
    it('should login successfully with email and password', async () => {
      const mockResponse = {
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
        json: async () => mockResponse,
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/auth/login',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/x-www-form-urlencoded',
          }),
          body: expect.any(URLSearchParams),
        })
      );

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toEqual(mockResponse.user);
      expect(result.current.accessToken).toBe(mockResponse.tokens.access_token);
    });

    it('should handle login failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid credentials' }),
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await expect(
        act(async () => {
          await result.current.login({
            email: 'test@example.com',
            password: 'wrong-password',
          });
        })
      ).rejects.toThrow('Invalid credentials');

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });

    it('should handle 2FA required response', async () => {
      const mockResponse = {
        user: { id: '1', email: 'test@example.com', twoFactorEnabled: true },
        tokens: {
          access_token: 'temp-2fa-token',
          token_type: 'bearer',
          expires_in: 300,
        },
        requires_2fa: true,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      const response = await act(async () => {
        return await result.current.login({
          email: 'test@example.com',
          password: 'password123',
        });
      });

      expect(response).toEqual({
        requires2FA: true,
        tempToken: 'temp-2fa-token',
      });

      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  describe('logout', () => {
    it('should logout successfully', async () => {
      // Setup authenticated state
      const mockUser = { id: '1', email: 'test@example.com' };
      localStorage.setItem('auth_token', 'mock-access-token');
      localStorage.setItem('refresh_token', 'mock-refresh-token');
      localStorage.setItem('auth_user', JSON.stringify(mockUser));

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'Logged out successfully' }),
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.isAuthenticated).toBe(true);
      });

      await act(async () => {
        await result.current.logout();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/auth/logout',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
        })
      );

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.accessToken).toBeNull();
      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });
  });

  describe('register', () => {
    it('should register successfully', async () => {
      const mockResponse = {
        id: '1',
        email: 'newuser@example.com',
        firstName: 'New',
        lastName: 'User',
        isVerified: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockResponse,
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      const user = await act(async () => {
        return await result.current.register({
          email: 'newuser@example.com',
          password: 'password123',
          firstName: 'New',
          lastName: 'User',
        });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/auth/register',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify({
            email: 'newuser@example.com',
            password: 'password123',
            firstName: 'New',
            lastName: 'User',
          }),
        })
      );

      expect(user).toEqual(mockResponse);
    });
  });

  describe('refreshToken', () => {
    it('should refresh token successfully', async () => {
      localStorage.setItem('refresh_token', 'mock-refresh-token');

      const mockResponse = {
        access_token: 'new-access-token',
        token_type: 'bearer',
        expires_in: 3600,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.refreshToken();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/auth/refresh',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ refresh_token: 'mock-refresh-token' }),
        })
      );

      expect(result.current.accessToken).toBe('new-access-token');
    });

    it('should handle refresh token failure', async () => {
      localStorage.setItem('refresh_token', 'invalid-refresh-token');

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Invalid refresh token' }),
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await act(async () => {
        await result.current.refreshToken();
      });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
    });
  });

  describe('updateProfile', () => {
    it('should update profile successfully', async () => {
      // Setup authenticated state
      const mockUser = { id: '1', email: 'test@example.com', firstName: 'Test' };
      localStorage.setItem('auth_token', 'mock-access-token');
      localStorage.setItem('auth_user', JSON.stringify(mockUser));

      const updatedUser = { ...mockUser, firstName: 'Updated' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updatedUser,
      } as Response);

      const { result } = renderHook(() => useAuth(), { wrapper });

      await waitFor(() => {
        expect(result.current.user).toEqual(mockUser);
      });

      await act(async () => {
        await result.current.updateProfile({ firstName: 'Updated' });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/auth/me',
        expect.objectContaining({
          method: 'PUT',
          headers: expect.objectContaining({
            'Authorization': 'Bearer mock-access-token',
          }),
          body: JSON.stringify({ firstName: 'Updated' }),
        })
      );

      expect(result.current.user).toEqual(updatedUser);
    });
  });
});