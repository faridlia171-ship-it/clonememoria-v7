'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { LogOut, User as UserIcon, Heart } from 'lucide-react';
import { logger } from '@/utils/logger';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    try {
      logger.info('USER_LOGOUT_CLICKED', { email: user?.email ?? 'unknown' });
      logout();
    } catch (err) {
      logger.error('LOGOUT_FAILED', { error: String(err) });
    }
  };

  const safeEmail = typeof user?.email === 'string' ? user.email : 'Utilisateur';

  return (
    <div className="min-h-screen bg-cream-100">
      <header className="bg-white border-b border-cream-200 shadow-soft">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">

            {/* Logo + retour dashboard */}
            <Link href="/dashboard" className="flex items-center space-x-2">
              <Heart className="w-6 h-6 text-rose-400" />
              <span className="text-xl font-display text-gray-900">
                CloneMemoria
              </span>
            </Link>

            {/* Zone utilisateur */}
            <div className="flex items-center space-x-4">

              {/* Email affiché en sécurité */}
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <UserIcon className="w-4 h-4" />
                <span>{safeEmail}</span>
              </div>

              {/* Bouton Logout sécurisé */}
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2 text-gray-700 hover:text-rose-500 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Logout</span>
              </button>

            </div>
          </div>
        </div>
      </header>

      {/* Contenu */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
