'use client';

import { logger } from '@/utils/logger';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, '') ??
  'https://clonememoria-backend.onrender.com/api';

const DEFAULT_TIMEOUT = 15000;

/** Empêche l’appel d’URL externes ou forgées */
function sanitizePath(path: string): string {
  if (!path) throw new Error('apiClient: chemin vide');
  if (path.startsWith('http://') || path.startsWith('https://')) {
    throw new Error(
      'apiClient: usage direct URL interdit (sécurité). Utiliser des chemins relatifs.'
    );
  }
  return path.replace(/^\/+/, '');
}

/** Timeout sécurisé */
function withTimeout<T>(promise: Promise<T>, ms = DEFAULT_TIMEOUT): Promise<T> {
  let timer: NodeJS.Timeout;

  const timeoutPromise = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      reject(new Error(`Requête expirée après ${ms}ms`));
    }, ms);
  });

  return Promise.race([promise, timeoutPromise]).finally(() =>
    clearTimeout(timer)
  );
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    try {
      return localStorage.getItem('access_token');
    } catch {
      return null;
    }
  }

  private buildHeaders(auth: boolean): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-Client': 'CloneMemoria-Frontend',
      'cm-request-id': crypto.randomUUID(),
    };

    if (auth) {
      const token = this.getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  private async request<T>(
    path: string,
    options: RequestInit,
    auth = false
  ): Promise<T> {
    const safe = sanitizePath(path);
    const url = `${this.baseUrl}/${safe}`;

    const finalOptions: RequestInit = {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...this.buildHeaders(auth),
      },
    };

    logger.debug('API Request', { url, method: options.method });

    const response = await withTimeout(fetch(url, finalOptions));

    let data: any = null;
    try {
      data = await response.json();
    } catch {
      logger.warn('Réponse non JSON', { url });
    }

    if (!response.ok) {
      const errMessage =
        data?.message ||
        data?.error ||
        `Erreur API (${response.status}) sur ${url}`;

      if (response.status === 401) {
        try {
          localStorage.removeItem('access_token');
        } catch {}
      }

      logger.error('API Error', {
        status: response.status,
        url,
        message: errMessage,
      });

      throw new Error(errMessage);
    }

    return data as T;
  }

  public get<T>(path: string, auth = false): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'GET',
      },
      auth
    );
  }

  public post<T>(path: string, body?: any, auth = false): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'POST',
        body: body ? JSON.stringify(body) : undefined,
      },
      auth
    );
  }

  public put<T>(path: string, body?: any, auth = false): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'PUT',
        body: body ? JSON.stringify(body) : undefined,
      },
      auth
    );
  }

  public delete<T>(path: string, auth = false): Promise<T> {
    return this.request<T>(
      path,
      {
        method: 'DELETE',
      },
      auth
    );
  }
}

export const apiClient = new APIClient(API_BASE);
