import { logger } from '@/utils/logger';
import type {
  UsageStats,
  BillingQuota,
  User,
  TTSResponse,
  Clone,
  Conversation,
  Message,
  ChatResponse,
} from '@/types';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
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

  // --------------------
  // Core helpers
  // --------------------

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { requiresAuth = false, ...fetchOptions } = options;

    const normalizedEndpoint = endpoint.startsWith('/')
      ? endpoint
      : `/${endpoint}`;
    const url = `${this.baseUrl}${normalizedEndpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (fetchOptions.headers) {
      Object.assign(headers, fetchOptions.headers as Record<string, string>);
    }

    if (requiresAuth) {
      const token = this.getAuthToken();
      if (!token) {
        throw new Error('Authentication required');
      }
      headers.Authorization = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, {
        ...fetchOptions,
        headers,
      });

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage =
            errorData?.detail ||
            errorData?.message ||
            errorMessage;
        } catch {
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      if (response.status === 204) {
        return undefined as unknown as T;
      }

      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        const txt = await response.text();
        return txt as unknown as T;
      }

      return (await response.json()) as T;
    } catch (error) {
      logger.error('API request error', { error });
      throw error;
    }
  }

  private get<T>(endpoint: string, requiresAuth = false): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', requiresAuth });
  }

  private post<T>(
    endpoint: string,
    data: unknown,
    requiresAuth = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data ?? {}),
      requiresAuth,
    });
  }

  private patch<T>(
    endpoint: string,
    data: unknown,
    requiresAuth = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data ?? {}),
      requiresAuth,
    });
  }

  private delete<T>(
    endpoint: string,
    requiresAuth = false
  ): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
      requiresAuth,
    });
  }

  // --------------------
  // Account / RGPD
  // --------------------

  updateConsent(consents: Partial<User>): Promise<User> {
    return this.patch<User>(
      `${API_PREFIX}/auth/me/consent`,
      consents,
      true
    );
  }

  exportUserData(): Promise<{ exported_at: string; data: unknown }> {
    return this.get(
      `${API_PREFIX}/auth/me/export`,
      true
    );
  }

  deleteUserData(): Promise<{ status: 'ok' }> {
    return this.delete(
      `${API_PREFIX}/auth/me/data`,
      true
    );
  }

  // --------------------
  // Billing
  // --------------------

  getBillingPlan(): Promise<BillingQuota> {
    return this.get(
      `${API_PREFIX}/billing/plan`,
      true
    );
  }

  getBillingUsage(): Promise<UsageStats> {
    return this.get(
      `${API_PREFIX}/billing/usage`,
      true
    );
  }

  createCheckout(plan: string): Promise<{ checkout_url: string }> {
    return this.post(
      `${API_PREFIX}/billing/checkout?plan=${encodeURIComponent(plan)}`,
      {},
      true
    );
  }

  // --------------------
  // Clones / Chat (API MÉTIER)
  // --------------------

  getCloneById(cloneId: string): Promise<Clone> {
    return this.get(
      `${API_PREFIX}/clones/${encodeURIComponent(cloneId)}`,
      true
    );
  }

  getCloneConversations(cloneId: string): Promise<Conversation[]> {
    return this.get(
      `${API_PREFIX}/clones/${encodeURIComponent(cloneId)}/conversations`,
      true
    );
  }

  createConversation(
    cloneId: string,
    title: string
  ): Promise<Conversation> {
    return this.post(
      `${API_PREFIX}/clones/${encodeURIComponent(cloneId)}/conversations`,
      { title },
      true
    );
  }

  getConversationMessages(
    conversationId: string
  ): Promise<Message[]> {
    return this.get(
      `${API_PREFIX}/conversations/${encodeURIComponent(conversationId)}/messages`,
      true
    );
  }

  sendMessage(
    cloneId: string,
    conversationId: string,
    content: string
  ): Promise<ChatResponse> {
    return this.post(
      `${API_PREFIX}/clones/${encodeURIComponent(
        cloneId
      )}/conversations/${encodeURIComponent(
        conversationId
      )}/messages`,
      { content },
      true
    );
  }

  // --------------------
  // Audio / Avatar
  // --------------------

  generateTTS(
    cloneId: string,
    text: string,
    voiceId?: string
  ): Promise<TTSResponse> {
    return this.post(
      `${API_PREFIX}/audio/tts/${encodeURIComponent(cloneId)}`,
      { text, voice_id: voiceId },
      true
    );
  }

  generateAvatar(
    cloneId: string,
    text: string,
    voice?: string,
    style?: string
  ): Promise<{ avatar_image_url: string; message: string }> {
    return this.post(
      `${API_PREFIX}/avatar/generate/${encodeURIComponent(cloneId)}`,
      { text, voice, style },
      true
    );
  }
}

export const apiClient = new APIClient(API_BASE_URL);
export default apiClient;
