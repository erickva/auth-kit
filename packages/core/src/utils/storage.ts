/**
 * Storage utilities for tokens and user data
 */

export type StorageDriver = 'localStorage' | 'sessionStorage' | 'cookie' | 'memory';

export interface StorageOptions {
  driver?: StorageDriver;
  cookieOptions?: {
    domain?: string;
    path?: string;
    secure?: boolean;
    sameSite?: 'strict' | 'lax' | 'none';
    maxAge?: number;
  };
}

// In-memory storage for SSR or when localStorage is not available
const memoryStorage: Record<string, string> = {};

export class AuthStorage {
  private driver: StorageDriver;
  private cookieOptions: StorageOptions['cookieOptions'];

  constructor(options: StorageOptions = {}) {
    this.driver = options.driver || 'localStorage';
    this.cookieOptions = options.cookieOptions || {};
  }

  /**
   * Set item in storage
   */
  setItem(key: string, value: string): void {
    switch (this.driver) {
      case 'localStorage':
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem(key, value);
        } else {
          memoryStorage[key] = value;
        }
        break;
      
      case 'sessionStorage':
        if (typeof window !== 'undefined' && window.sessionStorage) {
          sessionStorage.setItem(key, value);
        } else {
          memoryStorage[key] = value;
        }
        break;
      
      case 'cookie':
        if (typeof document !== 'undefined') {
          const options = this.cookieOptions;
          let cookie = `${key}=${encodeURIComponent(value)}`;
          
          if (options.domain) cookie += `; domain=${options.domain}`;
          if (options.path) cookie += `; path=${options.path}`;
          if (options.maxAge) cookie += `; max-age=${options.maxAge}`;
          if (options.secure) cookie += '; secure';
          if (options.sameSite) cookie += `; samesite=${options.sameSite}`;
          
          document.cookie = cookie;
        } else {
          memoryStorage[key] = value;
        }
        break;
      
      case 'memory':
        memoryStorage[key] = value;
        break;
    }
  }

  /**
   * Get item from storage
   */
  getItem(key: string): string | null {
    switch (this.driver) {
      case 'localStorage':
        if (typeof window !== 'undefined' && window.localStorage) {
          return localStorage.getItem(key);
        }
        return memoryStorage[key] || null;
      
      case 'sessionStorage':
        if (typeof window !== 'undefined' && window.sessionStorage) {
          return sessionStorage.getItem(key);
        }
        return memoryStorage[key] || null;
      
      case 'cookie':
        if (typeof document !== 'undefined') {
          const match = document.cookie.match(new RegExp(`(^| )${key}=([^;]+)`));
          return match ? decodeURIComponent(match[2]) : null;
        }
        return memoryStorage[key] || null;
      
      case 'memory':
        return memoryStorage[key] || null;
      
      default:
        return null;
    }
  }

  /**
   * Remove item from storage
   */
  removeItem(key: string): void {
    switch (this.driver) {
      case 'localStorage':
        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.removeItem(key);
        }
        delete memoryStorage[key];
        break;
      
      case 'sessionStorage':
        if (typeof window !== 'undefined' && window.sessionStorage) {
          sessionStorage.removeItem(key);
        }
        delete memoryStorage[key];
        break;
      
      case 'cookie':
        if (typeof document !== 'undefined') {
          document.cookie = `${key}=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT`;
        }
        delete memoryStorage[key];
        break;
      
      case 'memory':
        delete memoryStorage[key];
        break;
    }
  }

  /**
   * Clear all auth-related items
   */
  clear(prefix: string = 'auth_'): void {
    const keysToRemove: string[] = [];

    // Find all keys with the prefix
    switch (this.driver) {
      case 'localStorage':
        if (typeof window !== 'undefined' && window.localStorage) {
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith(prefix)) {
              keysToRemove.push(key);
            }
          }
        }
        break;
      
      case 'sessionStorage':
        if (typeof window !== 'undefined' && window.sessionStorage) {
          for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key && key.startsWith(prefix)) {
              keysToRemove.push(key);
            }
          }
        }
        break;
      
      case 'memory':
        Object.keys(memoryStorage).forEach(key => {
          if (key.startsWith(prefix)) {
            keysToRemove.push(key);
          }
        });
        break;
    }

    // Remove all found keys
    keysToRemove.forEach(key => this.removeItem(key));
  }
}