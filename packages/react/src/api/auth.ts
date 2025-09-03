import {
  LoginCredentials,
  RegisterData,
  User,
  AuthTokens,
  LoginResponse,
  PasswordChangeData,
  PasswordResetData,
  PasswordResetConfirmData,
  DEFAULT_ENDPOINTS,
  AuthConfig
} from '@erickva/auth-kit-core';

export interface ProfileUpdateData {
  firstName?: string;
  lastName?: string;
  phoneNumber?: string;
  metadata?: Record<string, any>;
}

class AuthAPI {
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

  private async handleResponse(response: Response) {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
      let errorMessage = 'An error occurred';
      
      if (typeof error === 'string') {
        errorMessage = error;
      } else if (error.detail) {
        errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
      } else if (error.message) {
        errorMessage = error.message;
      } else if (error.error) {
        errorMessage = error.error;
      } else {
        errorMessage = `HTTP error! status: ${response.status}`;
      }
      
      const authError = new Error(errorMessage);
      (authError as any).status = response.status;
      throw authError;
    }

    return response;
  }

  private async fetchWithTimeout(url: string, options: RequestInit = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          ...this.headers,
          ...options.headers
        }
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  async register(data: RegisterData): Promise<User> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.REGISTER}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    await this.handleResponse(response);
    return response.json();
  }

  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    // OAuth2 password flow requires form data
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.LOGIN}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    await this.handleResponse(response);
    return response.json();
  }

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.REFRESH}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    await this.handleResponse(response);
    return response.json();
  }

  async logout(refreshToken: string, accessToken: string): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.LOGOUT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    await this.handleResponse(response);
  }

  async getProfile(accessToken: string): Promise<User> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.PROFILE}`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    await this.handleResponse(response);
    return response.json();
  }

  async validateToken(accessToken: string): Promise<User | null> {
    try {
      const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.PROFILE}`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });
      
      if (response.ok) {
        return response.json();
      }
      
      return null;
    } catch {
      return null;
    }
  }

  async changePassword(data: PasswordChangeData, accessToken: string): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.PASSWORD_CHANGE}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify(data),
    });
    await this.handleResponse(response);
  }

  async requestPasswordReset(data: PasswordResetData): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.PASSWORD_RESET}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    await this.handleResponse(response);
  }

  async confirmPasswordReset(data: PasswordResetConfirmData): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.PASSWORD_RESET_CONFIRM}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    await this.handleResponse(response);
  }

  async verifyEmail(token: string): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.EMAIL_VERIFY}/${token}`);
    await this.handleResponse(response);
  }

  async resendVerification(accessToken: string): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.EMAIL_RESEND}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    await this.handleResponse(response);
  }

  async updateProfile(data: ProfileUpdateData, accessToken: string): Promise<User> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.PROFILE}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify(data),
    });
    await this.handleResponse(response);
    return response.json();
  }

  async verifyTwoFactor(code: string, tempToken: string): Promise<LoginResponse> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${this.endpoints.TWO_FACTOR_VERIFY_LOGIN}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${tempToken}`,
      },
      body: JSON.stringify({ code }),
    });

    await this.handleResponse(response);
    return response.json();
  }
}

export const authAPI = new AuthAPI();