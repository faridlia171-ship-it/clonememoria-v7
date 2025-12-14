'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
} from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { User, TokenResponse } from '@/types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/** Décodage JWT sécurisé */
function parseJwt(token: string) {
  try {
    if (!token || typeof token !== 'string' || token.split('.').length !== 3)
      return null;

    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const decoded = atob(base64);

    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loginLock = useRef(false);
  const router = useRouter();

  useEffect(() => {
    logger.debug('AuthProvider mounted');
    safeCheckAuth();
  }, []);

  /** Vérification sécurisée du token */
  const safeCheckAuth = async () => {
    let token: string | null = null;

    try {
      token = localStorage.getItem('access_token');
    } catch {
      logger.error('localStorage inaccessible');
      setLoading(false);
      return;
    }

    if (!token) {
      setLoading(false);
      return;
    }

    const decoded = parseJwt(token);

    // Token local expiré → purge
    if (!decoded || !decoded.exp || decoded.exp * 1000 < Date.now()) {
      logger.warn('Token expiré localement, purge…');
      try {
        localStorage.removeItem('access_token');
      } catch {}
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await apiClient.get<User>('/api/auth/me', true);
      setUser(userData);
      logger.info('User authenticated', { userId: userData.id });
    } catch (err) {
      logger.warn('Auth backend check failed, purge token');
      try {
        localStorage.removeItem('access_token');
      } catch {}
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  /** Connexion sécurisée */
  const login = async (email: string, password: string) => {
    if (loginLock.current) return;
    loginLock.current = true;

    logger.info('Login attempt');

    try {
      const response = await apiClient.post<TokenResponse>('/api/auth/login', {
        email,
        password,
      });

      if (!response?.access_token || !response.user) {
        throw new Error('Réponse login invalide');
      }

      localStorage.setItem('access_token', response.access_token);
      setUser(response.user);

      logger.info('Login successful');
      router.push('/dashboard');
    } catch (err) {
      logger.error('Login failed', err);
      throw err;
    } finally {
      loginLock.current = false;
    }
  };

  /** Enregistrement sécurisé */
  const register = async (
    email: string,
    password: string,
    fullName?: string
  ) => {
    logger.info('Register attempt');

    try {
      const response = await apiClient.post<TokenResponse>(
        '/api/auth/register',
        {
          email,
          password,
          full_name: fullName,
        }
      );

      if (!response?.access_token || !response.user) {
        throw new Error('Réponse register invalide');
      }

      localStorage.setItem('access_token', response.access_token);
      setUser(response.user);

      logger.info('Registration successful');
      router.push('/dashboard');
    } catch (err) {
      logger.error('Registration failed', err);
      throw err;
    }
  };

  /** Déconnexion complète et propre */
  const logout = () => {
    logger.info('User logout');

    try {
      localStorage.removeItem('access_token');
    } catch {
      logger.warn('Impossible de nettoyer le token');
    }

    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

