import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import {
  User,
  LoginCredentials,
  RegisterData,
  LoginResponse,
  AuthConfig,
  AuthState,
  AuthError,
  authEvents,
  AuthStorage,
  DEFAULT_STORAGE_KEYS,
  calculateTokenRefreshTime,
  isTokenExpired
} from '@erickva/auth-kit-core';
import { authAPI } from '../api/auth';
import { tokenManager } from '../utils/tokenManager';

interface AuthContextType extends AuthState {
  config: AuthConfig;
  login: (credentials: LoginCredentials) => Promise<LoginResponse>;
  loginWithPasskey: (response: any) => Promise<void>;
  verifyTwoFactor: (code: string, tempToken: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export interface AuthProviderProps {
  children: React.ReactNode;
  config: AuthConfig;
  onAuthStateChange?: (user: User | null) => void;
}

export function AuthProvider({ children, config, onAuthStateChange }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
    accessToken: null,
    error: null
  });

  // Initialize storage and API
  const storage = useMemo(
    () => new AuthStorage(config.storage),
    [config.storage]
  );

  // Initialize API client with config
  useEffect(() => {
    authAPI.configure(config.api);
  }, [config.api]);

  // Clear error
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Load user from storage on mount
  useEffect(() => {
    const loadUser = async () => {
      try {
        const tokenKey = config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
        const userKey = config.storage?.userKey || DEFAULT_STORAGE_KEYS.USER;
        
        const token = storage.getItem(tokenKey);
        const savedUser = storage.getItem(userKey);

        if (token && savedUser && !isTokenExpired(token)) {
          // Validate token with backend
          try {
            const currentUser = await authAPI.validateToken(token);
            if (currentUser) {
              setState({
                user: currentUser,
                isLoading: false,
                isAuthenticated: true,
                accessToken: token,
                error: null
              });
              
              // Initialize token manager
              tokenManager.initialize(token, storage, config);
              
              // Emit login event
              authEvents.emit('login', currentUser);
              config.events?.onLogin?.(currentUser);
              onAuthStateChange?.(currentUser);
              
              return;
            }
          } catch (error) {
            // Token invalid, clear storage
            clearAuthData();
          }
        }
        
        setState(prev => ({ ...prev, isLoading: false }));
      } catch (error) {
        console.error('Error loading user:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    loadUser();
  }, []);

  // Listen for auth events
  useEffect(() => {
    const unsubscribeRefreshed = authEvents.on('tokenRefresh', (event) => {
      const newToken = event.data?.accessToken;
      if (newToken) {
        setState(prev => ({ ...prev, accessToken: newToken }));
      }
    });

    const unsubscribeRefreshFailed = authEvents.on('tokenRefreshFailed', () => {
      clearAuthData();
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
        accessToken: null,
        error: { code: 'TOKEN_REFRESH_FAILED', message: 'Session expired' }
      });
    });

    return () => {
      unsubscribeRefreshed();
      unsubscribeRefreshFailed();
    };
  }, []);

  const clearAuthData = useCallback(() => {
    const tokenKey = config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
    const refreshTokenKey = config.storage?.refreshTokenKey || DEFAULT_STORAGE_KEYS.REFRESH_TOKEN;
    const userKey = config.storage?.userKey || DEFAULT_STORAGE_KEYS.USER;
    
    storage.removeItem(tokenKey);
    storage.removeItem(refreshTokenKey);
    storage.removeItem(userKey);
    
    tokenManager.cleanup();
  }, [config.storage, storage]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const response = await authAPI.login(credentials);
      
      // Check if 2FA is required
      if (response.requires2FA) {
        setState(prev => ({ ...prev, isLoading: false }));
        return response;
      }
      
      // Save tokens and user
      const tokenKey = config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
      const refreshTokenKey = config.storage?.refreshTokenKey || DEFAULT_STORAGE_KEYS.REFRESH_TOKEN;
      const userKey = config.storage?.userKey || DEFAULT_STORAGE_KEYS.USER;
      
      storage.setItem(tokenKey, response.tokens.accessToken);
      if (response.tokens.refreshToken) {
        storage.setItem(refreshTokenKey, response.tokens.refreshToken);
      }
      storage.setItem(userKey, JSON.stringify(response.user));
      
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
        accessToken: response.tokens.accessToken,
        error: null
      });
      
      // Initialize token manager
      tokenManager.initialize(response.tokens.accessToken, storage, config);
      
      // Emit events
      authEvents.emit('login', response.user);
      config.events?.onLogin?.(response.user);
      onAuthStateChange?.(response.user);
      
      return response;
    } catch (error) {
      const authError: AuthError = {
        code: 'LOGIN_FAILED',
        message: error instanceof Error ? error.message : 'Login failed'
      };
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: authError
      }));
      
      clearAuthData();
      throw error;
    }
  }, [config, storage, clearAuthData, onAuthStateChange]);

  const loginWithPasskey = useCallback(async (response: any) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      // Save tokens and user
      const tokenKey = config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
      const refreshTokenKey = config.storage?.refreshTokenKey || DEFAULT_STORAGE_KEYS.REFRESH_TOKEN;
      const userKey = config.storage?.userKey || DEFAULT_STORAGE_KEYS.USER;
      
      storage.setItem(tokenKey, response.tokens.accessToken);
      if (response.tokens.refreshToken) {
        storage.setItem(refreshTokenKey, response.tokens.refreshToken);
      }
      storage.setItem(userKey, JSON.stringify(response.user));
      
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
        accessToken: response.tokens.accessToken,
        error: null
      });
      
      // Initialize token manager
      tokenManager.initialize(response.tokens.accessToken, storage, config);
      
      // Emit events
      authEvents.emit('login', response.user);
      config.events?.onLogin?.(response.user);
      onAuthStateChange?.(response.user);
    } catch (error) {
      const authError: AuthError = {
        code: 'PASSKEY_LOGIN_FAILED',
        message: error instanceof Error ? error.message : 'Passkey login failed'
      };
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: authError
      }));
      
      clearAuthData();
      throw error;
    }
  }, [config, storage, clearAuthData, onAuthStateChange]);

  const verifyTwoFactor = useCallback(async (code: string, tempToken: string) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const response = await authAPI.verifyTwoFactor(code, tempToken);
      
      // Save tokens and user
      const tokenKey = config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
      const refreshTokenKey = config.storage?.refreshTokenKey || DEFAULT_STORAGE_KEYS.REFRESH_TOKEN;
      const userKey = config.storage?.userKey || DEFAULT_STORAGE_KEYS.USER;
      
      storage.setItem(tokenKey, response.tokens.accessToken);
      if (response.tokens.refreshToken) {
        storage.setItem(refreshTokenKey, response.tokens.refreshToken);
      }
      storage.setItem(userKey, JSON.stringify(response.user));
      
      setState({
        user: response.user,
        isLoading: false,
        isAuthenticated: true,
        accessToken: response.tokens.accessToken,
        error: null
      });
      
      // Initialize token manager
      tokenManager.initialize(response.tokens.accessToken, storage, config);
      
      // Emit events
      authEvents.emit('login', response.user);
      config.events?.onLogin?.(response.user);
      onAuthStateChange?.(response.user);
    } catch (error) {
      const authError: AuthError = {
        code: 'INVALID_2FA_CODE',
        message: error instanceof Error ? error.message : 'Invalid verification code'
      };
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: authError
      }));
      
      throw error;
    }
  }, [config, storage, onAuthStateChange]);

  const register = useCallback(async (data: RegisterData) => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const newUser = await authAPI.register(data);
      
      // Auto-login after registration if configured
      if (config.features?.emailVerification) {
        setState(prev => ({ ...prev, isLoading: false }));
        authEvents.emit('register', newUser);
      } else {
        // Auto-login
        await login({
          email: data.email,
          password: data.password
        });
      }
    } catch (error) {
      const authError: AuthError = {
        code: 'REGISTRATION_FAILED',
        message: error instanceof Error ? error.message : 'Registration failed'
      };
      
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: authError
      }));
      
      throw error;
    }
  }, [config.features?.emailVerification, login]);

  const logout = useCallback(async () => {
    try {
      const tokenKey = config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
      const refreshTokenKey = config.storage?.refreshTokenKey || DEFAULT_STORAGE_KEYS.REFRESH_TOKEN;
      
      const token = storage.getItem(tokenKey);
      const refreshToken = storage.getItem(refreshTokenKey);
      
      if (token && refreshToken) {
        await authAPI.logout(refreshToken, token);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuthData();
      
      setState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
        accessToken: null,
        error: null
      });
      
      // Emit events
      authEvents.emit('logout');
      config.events?.onLogout?.();
      onAuthStateChange?.(null);
    }
  }, [config, storage, clearAuthData, onAuthStateChange]);

  const updateUser = useCallback((updatedUser: User) => {
    const userKey = config.storage?.userKey || DEFAULT_STORAGE_KEYS.USER;
    storage.setItem(userKey, JSON.stringify(updatedUser));
    
    setState(prev => ({ ...prev, user: updatedUser }));
    onAuthStateChange?.(updatedUser);
  }, [config.storage?.userKey, storage, onAuthStateChange]);

  const refreshUser = useCallback(async () => {
    if (!state.accessToken) return;
    
    try {
      const currentUser = await authAPI.getProfile(state.accessToken);
      updateUser(currentUser);
    } catch (error) {
      console.error('Error refreshing user:', error);
    }
  }, [state.accessToken, updateUser]);

  const value = useMemo(
    () => ({
      ...state,
      config,
      login,
      loginWithPasskey,
      verifyTwoFactor,
      register,
      logout,
      updateUser,
      refreshUser,
      clearError
    }),
    [state, config, login, loginWithPasskey, verifyTwoFactor, register, logout, updateUser, refreshUser, clearError]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}