'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/apiClient';
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    logger.info('AuthProvider mounted');
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');

    if (!token) {
      logger.debug('No auth token found');
      setLoading(false);
      return;
    }

    try {
      logger.info('Checking authentication');
      const userData = await apiClient.get<User>('/api/auth/me', true);
      setUser(userData);
      logger.info('User authenticated', { userId: userData.id });
    } catch (error) {
      logger.error('Auth check failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      localStorage.removeItem('access_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    logger.info('Login attempt', { email });

    try {
      const response = await apiClient.post<TokenResponse>('/api/auth/login', {
        email,
        password,
      });

      localStorage.setItem('access_token', response.access_token);
      setUser(response.user);

      logger.info('Login successful', { userId: response.user.id });

      router.push('/dashboard');
    } catch (error) {
      logger.error('Login failed', {
        email,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  };

  const register = async (
    email: string,
    password: string,
    fullName?: string
  ) => {
    logger.info('Registration attempt', { email });

    try {
      const response = await apiClient.post<TokenResponse>(
        '/api/auth/register',
        {
          email,
          password,
          full_name: fullName,
        }
      );

      localStorage.setItem('access_token', response.access_token);
      setUser(response.user);

      logger.info('Registration successful', { userId: response.user.id });

      router.push('/dashboard');
    } catch (error) {
      logger.error('Registration failed', {
        email,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      throw error;
    }
  };

  const logout = () => {
    logger.info('User logout', { userId: user?.id });

    localStorage.removeItem('access_token');
    setUser(null);
    router.push('/login');
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
