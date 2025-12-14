'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { Memory, Clone } from '@/types';
import { 
  ArrowLeft, 
  Loader2, 
  PlusCircle 
} from 'lucide-react';

export default function CloneMemoriesPage() {
  const params = useParams();
  const router = useRouter();

  // Sécurisation ID
  const cloneId = typeof params?.id === 'string' ? params.id : null;

  const [clone, setClone] = useState<Clone | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!cloneId) {
      logger.error('Invalid cloneId provided to memories page');
      router.push('/dashboard');
      return;
    }

    logger.info('CloneMemoriesPage loaded', { cloneId });
    loadData();
  }, [cloneId]);

  // Chargement clone + memories
  const loadData = async () => {
    try {
      const cloneData = await apiClient.get<Clone>(`/api/clones/${cloneId}`, true);
      if (!cloneData || typeof cloneData !== 'object') {
        throw new Error('Invalid clone data structure');
      }

      const memoriesData = await apiClient.get<Memory[]>(`/api/clones/${cloneId}/memories`, true);
      if (!Array.isArray(memoriesData)) {
        throw new Error('Invalid memories structure');
      }

      setClone(cloneData);
      setMemories(memoriesData);

      logger.info('Clone & memories loaded', {
        cloneId,
        memoryCount: memoriesData.length
      });

    } catch (error) {
      logger.error('Failed to load clone memories page', {
        cloneId,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  // Chargement
  if (loading || !clone) {
    return (
      <AppLayout>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  const name = clone.name ?? 'Unnamed';

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto">

        <Link
          href={`/clones/${cloneId}`}
          className="inline-flex items-center space-x-2 text-gray-600 hover:text-rose-500 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Clone</span>
        </Link>

        <div className="flex items-center justify-between mb-6">
          <h1 className="text-4xl font-display text-gray-900">
            Memories of {name}
          </h1>

          <Link
            href={`/clones/${cloneId}/memories/new`}
            className="btn-primary inline-flex items-center space-x-2"
          >
            <PlusCircle className="w-5 h-5" />
            <span>Add Memory</span>
          </Link>
        </div>

        {/* liste des memories sécurisée */}
        {memories.length === 0 ? (
          <p className="text-gray-500">No memories recorded yet.</p>
        ) : (
          <div className="space-y-4">
            {memories.map((mem) => (
              <div
                key={mem.id}
                className="card hover:shadow-soft-lg transition-shadow duration-200"
              >
                <h2 className="text-xl font-display text-gray-900 mb-2">
                  {mem.title ?? 'Untitled'}
                </h2>
                <p className="text-gray-700 whitespace-pre-line">
                  {mem.content ?? ''}
                </p>
                <p className="text-xs text-gray-500 mt-3">
                  {mem.created_at ? new Date(mem.created_at).toLocaleString() : ''}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
