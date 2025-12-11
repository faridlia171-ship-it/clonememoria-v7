import { logger } from '@/utils/logger';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    logger.info('APIClient initialized', { baseUrl });
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { requiresAuth = false, ...fetchOptions } = options;
    const url = `${this.baseUrl}${endpoint}`;
    const startTime = Date.now();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (fetchOptions.headers) {
      Object.assign(headers, fetchOptions.headers);
    }

    if (requiresAuth) {
      const token = this.getAuthToken();
      if (!token) {
        logger.error('API request requires auth but no token found', {
          endpoint,
        });
        throw new Error('Authentication required');
      }
      headers['Authorization'] = `Bearer ${token}`;
    }

    logger.debug('API request started', {
      method: fetchOptions.method || 'GET',
      url,
      requiresAuth,
    });

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers,
      });

      const elapsedTime = Date.now() - startTime;

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch {
          errorMessage = response.statusText || errorMessage;
        }

        logger.error('API request failed', {
          url,
          status: response.status,
          statusText: response.statusText,
          errorMessage,
          elapsedTime,
        });

        throw new Error(errorMessage);
      }

      const data = await response.json();

      logger.info('API request completed', {
        url,
        status: response.status,
        elapsedTime: `${elapsedTime}ms`,
      });

      return data as T;
    } catch (error) {
      const elapsedTime = Date.now() - startTime;

      logger.error('API request error', {
        url,
        error: error instanceof Error ? error.message : 'Unknown error',
        elapsedTime,
      });

      throw error;
    }
  }

  async get<T>(endpoint: string, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'GET',
      requiresAuth,
    });
  }

  async post<T>(
    endpoint: string,
    data: any,
    requiresAuth = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      requiresAuth,
    });
  }

  async put<T>(
    endpoint: string,
    data: any,
    requiresAuth = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
      requiresAuth,
    });
  }

  async patch<T>(
    endpoint: string,
    data: any,
    requiresAuth = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
      requiresAuth,
    });
  }

  async delete<T>(endpoint: string, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
      requiresAuth,
    });
  }

  async updateConsent(consents: any): Promise<any> {
    return this.patch('/api/v1/auth/me/consent', consents, true);
  }

  async exportUserData(): Promise<any> {
    return this.get('/api/v1/auth/me/export', true);
  }

  async deleteUserData(): Promise<any> {
    return this.delete('/api/v1/auth/me/data', true);
  }

  async getBillingPlan(): Promise<any> {
    return this.get('/api/v1/billing/plan', true);
  }

  async getBillingUsage(): Promise<any> {
    return this.get('/api/v1/billing/usage', true);
  }

  async createCheckout(plan: string): Promise<any> {
    return this.post(`/api/v1/billing/checkout?plan=${plan}`, {}, true);
  }

  async generateTTS(cloneId: string, text: string, voiceId?: string): Promise<any> {
    return this.post(`/api/v1/audio/tts/${cloneId}`, { text, voice_id: voiceId }, true);
  }

  async generateAvatar(cloneId: string, text: string, voice?: string, style?: string): Promise<any> {
    return this.post(`/api/v1/avatar/generate/${cloneId}`, { text, voice, style }, true);
  }
}

export const apiClient = new APIClient(API_BASE_URL);
