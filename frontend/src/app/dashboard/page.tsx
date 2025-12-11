'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { CloneCard } from '@/components/clone/CloneCard';
import { CloneForm } from '@/components/forms/CloneForm';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { CloneWithStats, ToneConfig } from '@/types';
import { Plus, Loader2 } from 'lucide-react';

export default function DashboardPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();
  const [clones, setClones] = useState<CloneWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    logger.info('DashboardPage loaded');

    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadClones();
    }
  }, [isAuthenticated]);

  const loadClones = async () => {
    try {
      logger.info('Loading clones');
      const data = await apiClient.get<CloneWithStats[]>('/api/clones', true);
      setClones(data);
      logger.info('Clones loaded', { count: data.length });
    } catch (error) {
      logger.error('Failed to load clones', {
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClone = async (data: {
    name: string;
    description: string;
    tone_config: ToneConfig;
  }) => {
    logger.info('Creating clone', { name: data.name });

    await apiClient.post('/api/clones', data, true);

    logger.info('Clone created successfully');
    setShowCreateForm(false);
    await loadClones();
  };

  if (authLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
      </div>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex justify-end space-x-4">
          <button
            onClick={() => router.push('/account')}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Account & Privacy
          </button>
          <button
            onClick={() => router.push('/billing')}
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Billing & Usage
          </button>
        </div>

        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-display text-gray-900 mb-2">
              Your Clones
            </h1>
            <p className="text-gray-600">
              Create and manage AI clones of your loved ones
            </p>
          </div>

          {!showCreateForm && (
            <button
              onClick={() => setShowCreateForm(true)}
              className="btn-primary flex items-center space-x-2"
            >
              <Plus className="w-5 h-5" />
              <span>New Clone</span>
            </button>
          )}
        </div>

        {showCreateForm && (
          <div className="card mb-8">
            <h2 className="text-2xl font-display text-gray-900 mb-6">
              Create New Clone
            </h2>
            <CloneForm
              onSubmit={handleCreateClone}
              onCancel={() => setShowCreateForm(false)}
              submitLabel="Create Clone"
            />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
          </div>
        ) : clones.length === 0 ? (
          <div className="text-center py-12">
            <div className="card max-w-md mx-auto">
              <h3 className="text-xl font-display text-gray-900 mb-2">
                No clones yet
              </h3>
              <p className="text-gray-600 mb-6">
                Create your first AI clone to start preserving memories and
                conversations.
              </p>
              {!showCreateForm && (
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="btn-primary"
                >
                  Create Your First Clone
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {clones.map((clone) => (
              <CloneCard key={clone.id} clone={clone} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
