import {
  TwoFactorSetupResponse,
  TwoFactorEnableResponse,
  RecoveryCodesResponse,
  DEFAULT_ENDPOINTS,
  AuthConfig
} from '@auth-kit/core';

class TwoFactorAPI {
  private baseUrl: string = '';
  private endpoints: typeof DEFAULT_ENDPOINTS;
  private headers: Record<string, string> = {};
  private timeout: number = 30000;

  constructor() {
    this.endpoints = { ...DEFAULT_ENDPOINTS };
  }

  configure(apiConfig: AuthConfig['api']) {
    this.baseUrl = apiConfig.baseUrl;
    this.endpoints = { ...DEFAULT_ENDPOINTS, ...apiConfig.endpoints };
    this.headers = apiConfig.headers || {};
    this.timeout = apiConfig.timeout || 30000;
  }

  private async fetchWithAuth(url: string, options: RequestInit = {}, accessToken: string) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          ...this.headers,
          'Authorization': `Bearer ${accessToken}`,
          ...options.headers
        }
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
      }
      
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  async beginSetup(accessToken: string): Promise<TwoFactorSetupResponse> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.TWO_FACTOR_SETUP_BEGIN}`,
      {
        method: 'POST',
      },
      accessToken
    );
    return response.json();
  }

  async verifySetup(code: string, accessToken: string): Promise<TwoFactorEnableResponse> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.TWO_FACTOR_SETUP_VERIFY}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code }),
      },
      accessToken
    );
    return response.json();
  }

  async disable(password: string, accessToken: string): Promise<void> {
    await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.TWO_FACTOR_DISABLE}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      },
      accessToken
    );
  }

  async regenerateRecoveryCodes(password: string, accessToken: string): Promise<RecoveryCodesResponse> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.TWO_FACTOR_RECOVERY_CODES}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      },
      accessToken
    );
    return response.json();
  }

  async verifyLogin(code: string, tempToken: string): Promise<any> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(
        `${this.baseUrl}${this.endpoints.TWO_FACTOR_VERIFY_LOGIN}`,
        {
          method: 'POST',
          signal: controller.signal,
          headers: {
            ...this.headers,
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${tempToken}`,
          },
          body: JSON.stringify({ code }),
        }
      );
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Verification failed' }));
        throw new Error(error.detail || 'Invalid verification code');
      }
      
      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }
}

export const twoFactorAPI = new TwoFactorAPI();