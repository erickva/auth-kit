import {
  Passkey,
  PasskeyRegistrationOptions,
  PasskeyAuthenticationOptions,
  DEFAULT_ENDPOINTS,
  AuthConfig
} from '@auth-kit/core';

interface PasskeyListResponse {
  passkeys: Passkey[];
  total: number;
}

class PasskeyAPI {
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

  private async fetchWithAuth(url: string, options: RequestInit = {}, accessToken?: string) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const headers: Record<string, string> = {
        ...this.headers,
        ...options.headers as Record<string, string>
      };

      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
      }

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers
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

  async beginRegistration(name: string, accessToken: string): Promise<{
    options: PasskeyRegistrationOptions;
    challenge: string;
  }> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.PASSKEY_REGISTER_BEGIN}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name }),
      },
      accessToken
    );

    const data = await response.json();
    return {
      options: data,
      challenge: data.challenge
    };
  }

  async completeRegistration(
    name: string,
    response: any,
    challenge: string,
    accessToken: string
  ): Promise<void> {
    await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.PASSKEY_REGISTER_COMPLETE}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          response,
          challenge,
        }),
      },
      accessToken
    );
  }

  async listPasskeys(accessToken: string): Promise<PasskeyListResponse> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.PASSKEY_LIST}`,
      {},
      accessToken
    );
    return response.json();
  }

  async deletePasskey(passkeyId: string, accessToken: string): Promise<void> {
    const url = `${this.baseUrl}${this.endpoints.PASSKEY_DELETE.replace(':id', passkeyId)}`;
    await this.fetchWithAuth(
      url,
      {
        method: 'DELETE',
      },
      accessToken
    );
  }

  async beginAuthentication(email?: string): Promise<{
    options: PasskeyAuthenticationOptions;
    challenge: string;
  }> {
    const response = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.PASSKEY_AUTH_BEGIN}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      }
    );

    const data = await response.json();
    return {
      options: data,
      challenge: data.challenge
    };
  }

  async completeAuthentication(
    response: any,
    challenge: string
  ): Promise<any> {
    const apiResponse = await this.fetchWithAuth(
      `${this.baseUrl}${this.endpoints.PASSKEY_AUTH_COMPLETE}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          response,
          challenge,
        }),
      }
    );
    return apiResponse.json();
  }
}

export const passkeyAPI = new PasskeyAPI();