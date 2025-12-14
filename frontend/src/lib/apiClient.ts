import { logger } from '@/utils/logger';
import type { UsageStats, BillingQuota, User, TTSResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Backend réel (FastAPI) utilise settings.API_V1_PREFIX = "/api" par défaut.
 * Donc les endpoints doivent être préfixés par "/api" (et non "/api/v1").
 *
 * Optionnel: NEXT_PUBLIC_API_PREFIX si tu veux override (ex: "/api").
 */
const API_PREFIX = process.env.NEXT_PUBLIC_API_PREFIX || '/api';

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    logger.info('APIClient initialized', { baseUrl: this.baseUrl });
  }

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { requiresAuth = false, ...fetchOptions } = options;

    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${this.baseUrl}${normalizedEndpoint}`;
    const startTime = Date.now();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (fetchOptions.headers) {
      Object.assign(headers, fetchOptions.headers as Record<string, string>);
    }

    if (requiresAuth) {
      const token = this.getAuthToken();
      if (!token) {
        logger.error('API request requires auth but no token found', { endpoint: normalizedEndpoint });
        throw new Error('Authentication required');
      }
      headers.Authorization = `Bearer ${token}`;
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
          errorMessage = errorData?.detail || errorData?.message || errorMessage;
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

      // 204 / empty body safety
      if (response.status === 204) {
        return undefined as unknown as T;
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        const txt = await response.text();
        return txt as unknown as T;
      }

      const data = (await response.json()) as T;

      logger.info('API request completed', {
        url,
        status: response.status,
        elapsedTime: `${elapsedTime}ms`,
      });

      return data;
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
    return this.request<T>(endpoint, { method: 'GET', requiresAuth });
  }

  async post<T>(endpoint: string, data: unknown, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data ?? {}),
      requiresAuth,
    });
  }

  async put<T>(endpoint: string, data: unknown, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data ?? {}),
      requiresAuth,
    });
  }

  async patch<T>(endpoint: string, data: unknown, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data ?? {}),
      requiresAuth,
    });
  }

  async delete<T>(endpoint: string, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', requiresAuth });
  }

  // ---------------------------
  // RGPD / Account (utilisé par app/account/page.tsx)
  // ---------------------------

  async updateConsent(consents: Partial<User>): Promise<User> {
    return this.patch<User>(`${API_PREFIX}/auth/me/consent`, consents, true);
  }

  async exportUserData(): Promise<{ exported_at: string; data: unknown }> {
    return this.get<{ exported_at: string; data: unknown }>(`${API_PREFIX}/auth/me/export`, true);
  }

  async deleteUserData(): Promise<{ status: 'ok' }> {
    return this.delete<{ status: 'ok' }>(`${API_PREFIX}/auth/me/data`, true);
  }

  // ---------------------------
  // Billing (utilisé par app/billing/page.tsx)
  // ---------------------------

  async getBillingPlan(): Promise<BillingQuota> {
    return this.get<BillingQuota>(`${API_PREFIX}/billing/plan`, true);
  }

  async getBillingUsage(): Promise<UsageStats> {
    return this.get<UsageStats>(`${API_PREFIX}/billing/usage`, true);
  }

  async createCheckout(plan: string): Promise<{ checkout_url: string }> {
    const qp = encodeURIComponent(plan);
    return this.post<{ checkout_url: string }>(`${API_PREFIX}/billing/checkout?plan=${qp}`, {}, true);
  }

  // ---------------------------
  // Audio / Avatar (utilisé par MessageBubble)
  // ---------------------------

  async generateTTS(cloneId: string, text: string, voiceId?: string): Promise<TTSResponse> {
    return this.post<TTSResponse>(
      `${API_PREFIX}/audio/tts/${encodeURIComponent(cloneId)}`,
      { text, voice_id: voiceId },
      true
    );
  }

  async generateAvatar(
    cloneId: string,
    text: string,
    voice?: string,
    style?: string
  ): Promise<{ avatar_image_url: string; message: string }> {
    return this.post<{ avatar_image_url: string; message: string }>(
      `${API_PREFIX}/avatar/generate/${encodeURIComponent(cloneId)}`,
      { text, voice, style },
      true
    );
  }
}

export const apiClient = new APIClient(API_BASE_URL);
