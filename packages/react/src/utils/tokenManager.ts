import {
  AuthStorage,
  AuthConfig,
  authEvents,
  parseToken,
  calculateTokenRefreshTime,
  DEFAULT_STORAGE_KEYS,
  TOKEN_SETTINGS
} from '@auth-kit/core';
import { authAPI } from '../api/auth';

class TokenManager {
  private static instance: TokenManager;
  private refreshTimer: NodeJS.Timeout | null = null;
  private isRefreshing = false;
  private storage: AuthStorage | null = null;
  private config: AuthConfig | null = null;

  private constructor() {}

  static getInstance(): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager();
    }
    return TokenManager.instance;
  }

  initialize(token: string, storage: AuthStorage, config: AuthConfig): void {
    this.storage = storage;
    this.config = config;
    this.startTokenRefreshTimer(token);

    // Listen for visibility change
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', this.handleVisibilityChange);
    }

    // Listen for storage changes (multi-tab support)
    if (typeof window !== 'undefined') {
      window.addEventListener('storage', this.handleStorageChange);
    }
  }

  cleanup(): void {
    this.stopTokenRefreshTimer();
    
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    }
    
    if (typeof window !== 'undefined') {
      window.removeEventListener('storage', this.handleStorageChange);
    }
  }

  private startTokenRefreshTimer(token: string): void {
    this.stopTokenRefreshTimer();

    const refreshTime = calculateTokenRefreshTime(
      token,
      TOKEN_SETTINGS.ACCESS_TOKEN_BUFFER_SECONDS
    );

    if (refreshTime > 0) {
      console.log(`Token refresh scheduled in ${Math.round(refreshTime / 1000 / 60)} minutes`);
      this.refreshTimer = setTimeout(() => {
        this.silentRefresh();
      }, refreshTime);
    } else {
      // Token expires soon or already expired, refresh immediately
      console.log('Token expiring soon, refreshing immediately');
      this.silentRefresh();
    }
  }

  private stopTokenRefreshTimer(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }

  private async silentRefresh(): Promise<boolean> {
    if (this.isRefreshing || !this.storage || !this.config) {
      return false;
    }

    const refreshTokenKey = this.config.storage?.refreshTokenKey || DEFAULT_STORAGE_KEYS.REFRESH_TOKEN;
    const refreshToken = this.storage.getItem(refreshTokenKey);
    
    if (!refreshToken) {
      console.error('No refresh token available');
      authEvents.emit('tokenRefreshFailed', { error: 'No refresh token' });
      return false;
    }

    this.isRefreshing = true;

    try {
      const tokens = await authAPI.refreshToken(refreshToken);
      
      // Save new tokens
      const tokenKey = this.config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
      this.storage.setItem(tokenKey, tokens.accessToken);
      
      if (tokens.refreshToken) {
        this.storage.setItem(refreshTokenKey, tokens.refreshToken);
      }

      console.log('Token refreshed successfully');
      
      // Restart timer for next refresh
      this.startTokenRefreshTimer(tokens.accessToken);
      
      // Emit success event
      authEvents.emit('tokenRefresh', { accessToken: tokens.accessToken });
      this.config.events?.onTokenRefresh?.(tokens);

      return true;
    } catch (error) {
      console.error('Token refresh failed:', error);
      authEvents.emit('tokenRefreshFailed', { error });
      this.config.events?.onAuthError?.({
        code: 'TOKEN_REFRESH_FAILED',
        message: 'Failed to refresh token'
      });
      return false;
    } finally {
      this.isRefreshing = false;
    }
  }

  private handleVisibilityChange = (): void => {
    if (document.visibilityState === 'visible' && this.storage && this.config) {
      // Page became visible, check if we need to refresh
      const tokenKey = this.config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
      const token = this.storage.getItem(tokenKey);
      
      if (token) {
        // Cancel existing timer and reschedule
        this.startTokenRefreshTimer(token);
      }
    }
  };

  private handleStorageChange = (event: StorageEvent): void => {
    if (!this.config || !this.storage) return;

    const tokenKey = this.config.storage?.tokenKey || DEFAULT_STORAGE_KEYS.ACCESS_TOKEN;
    
    if (event.key === tokenKey) {
      if (event.newValue) {
        // New token set, restart timer
        this.startTokenRefreshTimer(event.newValue);
      } else {
        // Token removed, stop timer
        this.stopTokenRefreshTimer();
      }
    }
  };
}

export const tokenManager = TokenManager.getInstance();