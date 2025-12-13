'use client';

import React, { Component, ReactNode } from 'react';
import { logger } from '@/utils/logger';

/**
 * ErrorBoundary – Production-grade React boundary
 * Sécurisé, isolé, évite toute fuite de stack trace côté client.
 */

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    // Évite de diffuser l'erreur brute dans l’UI
    return { hasError: true, error: error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    /**
     * Logging strict côté backend seulement.
     * Aucun stack trace n’apparaît dans la console du navigateur.
     */
    logger.error('FRONTEND_ERROR_BOUNDARY', {
      message: error.message,
      componentStack: errorInfo.componentStack ?? 'no-component-stack',
    });
  }

  render() {
    if (this.state.hasError) {
      // Si un fallback custom est fourni (écran personnalisé), on l'utilise
      if (this.props.fallback) return this.props.fallback;

      // Sinon, fallback par défaut ultra simple + sûr
      return (
        <div className="min-h-screen flex items-center justify-center bg-cream-100 px-4">
          <div className="card max-w-md text-center">
            <h2 className="text-2xl font-display text-gray-900 mb-4">
              Oups, une erreur est survenue
            </h2>
            <p className="text-gray-600 mb-6">
              Un problème inattendu s’est produit. Merci de recharger la page.
            </p>

            <button
              onClick={() => window.location.reload()}
              className="btn-primary"
            >
              Recharger la page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
