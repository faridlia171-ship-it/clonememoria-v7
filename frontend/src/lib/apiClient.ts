import { logger } from '@/utils/logger';
import type {
  UsageStats,
  BillingQuota,
  TTSResponse,
  Clone,
  Conversation,
  Message,
  ChatResponse,
  CloneWithStats,
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

  /* =======================
     CORE
  ======================= */

  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { requiresAuth = false, ...fetchOptions } = options;
    const url = `${this.baseUrl}${
      endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    }`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(fetchOptions.headers as Record<string, string>),
    };

    if (requiresAuth) {
      const token = this.getAuthToken();
      if (!token) throw new Error('Authentication required');
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, { ...fetchOptions, headers });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || response.statusText);
    }

    if (response.status === 204) {
      return undefined as unknown as T;
    }

    return (await response.json()) as T;
  }

  get<T>(endpoint: string, auth = false): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', requiresAuth: auth });
  }

  post<T>(endpoint: string, data: unknown, auth = false): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      requiresAuth: auth,
    });
  }

  /* =======================
     CLONES
  ======================= */

  listClones(): Promise<Clone[]> {
    return this.get<Clone[]>(`${API_PREFIX}/clones`, true);
  }

  clones = {
    list: async (): Promise<CloneWithStats[]> => {
      logger.info('apiClient.clones.list called');

      const clones = await this.listClones();

      return clones.map((clone) => ({
        ...clone,
        memory_count: 0,
        conversation_count: 0,
      }));
    },
  };

  /* =======================
     CONVERSATIONS / MESSAGES
  ======================= */

  getCloneConversations(cloneId: string): Promise<Conversation[]> {
    return this.get<Conversation[]>(
      `${API_PREFIX}/clones/${cloneId}/conversations`,
      true
    );
  }

  getMessages(cloneId: string, conversationId: string): Promise<Message[]> {
    return this.get<Message[]>(
      `${API_PREFIX}/clones/${cloneId}/conversations/${conversationId}/messages`,
      true
    );
  }

  getConversationMessages(_conversationId: string): Promise<Message[]> {
    return Promise.resolve([]);
  }

  sendMessage(
    cloneId: string,
    conversationId: string,
    content: string
  ): Promise<ChatResponse> {
    return this.post<ChatResponse>(
      `${API_PREFIX}/clones/${cloneId}/conversations/${conversationId}/messages`,
      { content },
      true
    );
  }

  /* =======================
     BILLING / AUDIO
  ======================= */

  getBillingPlan(): Promise<BillingQuota> {
    return this.get<BillingQuota>(`${API_PREFIX}/billing/plan`, true);
  }

  getBillingUsage(): Promise<UsageStats> {
    return this.get<UsageStats>(`${API_PREFIX}/billing/usage`, true);
  }

  generateTTS(
    cloneId: string,
    text: string,
    voiceId?: string
  ): Promise<TTSResponse> {
    return this.post<TTSResponse>(
      `${API_PREFIX}/audio/tts/${cloneId}`,
      { text, voice_id: voiceId },
      true
    );
  }

  /* =======================
     ACCOUNT (STUBS ALIGNÉS)
  ======================= */

  updateConsent(_consents: unknown): Promise<void> {
    logger.info('updateConsent called (stub)', _consents);
    return Promise.resolve();
  }

  exportUserData(): Promise<Record<string, unknown>> {
    return Promise.resolve({});
  }

  deleteUserData(): Promise<void> {
    return Promise.resolve();
  }
}

export const apiClient = new APIClient(API_BASE_URL);
export default apiClient;
