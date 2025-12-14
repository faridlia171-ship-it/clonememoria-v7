'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { CloneCard } from '@/components/clone/CloneCard';
import { CloneForm } from '@/components/forms/CloneForm';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { CloneWithStats, ToneConfig } from '@/types';
import { Plus, Loader2 } from 'lucide-react';

export default function DashboardPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const router = useRouter();

  const [clones, setClones] = useState<CloneWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchClones = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.clones.list();
      setClones(res || []);
    } catch (err) {
      logger.error('FETCH_CLONES_FAILED', { error: err });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (isAuthenticated) fetchClones();
  }, [authLoading, isAuthenticated, fetchClones, router]);

  const handleCloneCreated = (newClone: CloneWithStats) => {
    setClones((prev) => [...prev, newClone]);
    setShowCreateForm(false);
  };

  return (
    <AppLayout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Mes clones</h1>

        {!creating && (
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 transition"
          >
            <Plus size={18} />
            Nouveau clone
          </button>
        )}
      </div>

      {showCreateForm && (
        <div className="mb-6">
          <CloneForm
            onCreated={handleCloneCreated}
            onCancel={() => setShowCreateForm(false)}
          />
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-10">
          <Loader2 size={32} className="animate-spin text-gray-500" />
        </div>
      ) : clones.length === 0 ? (
        <p className="text-gray-500">Aucun clone enregistré pour le moment.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {clones.map((clone) => (
            <CloneCard key={clone.id} clone={clone} />
          ))}
        </div>
      )}
    </AppLayout>
  );
}

