'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { Clone, Message } from '@/types';
import { ArrowLeft, Loader2 } from 'lucide-react';

export default function CloneMemoriesPage() {
  const params = useParams();
  const cloneId = params?.id as string | undefined;

  const [clone, setClone] = useState<Clone | null>(null);
  const [memories, setMemories] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!cloneId) {
      logger.error('CloneMemoriesPage: missing cloneId');
      setLoading(false);
      return;
    }

    void loadData();
  }, [cloneId]);

  const loadData = async () => {
    if (!cloneId) return;

    try {
      logger.info('Loading clone memories', { cloneId });

      const cloneData = await apiClient.getCloneById(cloneId);
      const memoriesData = await apiClient.getCloneMemories(cloneId);

      setClone(cloneData);
      setMemories(Array.isArray(memoriesData) ? memoriesData : []);
    } catch (error: any) {
      logger.error('Failed to load clone memories', {
        cloneId,
        error: error?.message ?? 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  if (!clone) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-gray-600">Clone introuvable</p>
          <Link
            href="/clones"
            className="mt-4 inline-block text-rose-500 underline"
          >
            Back to clones
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto">
        <Link
          href={`/clones/${cloneId}`}
          className="inline-flex items-center space-x-2 text-gray-600 hover:text-rose-500 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Clone</span>
        </Link>

        <h1 className="text-2xl font-display mb-6">
          Memories of {clone.name}
        </h1>

        {memories.length === 0 ? (
          <p className="text-gray-500">No memories available.</p>
        ) : (
          <div className="space-y-4">
            {memories.map((m) => (
              <div
                key={m.id}
                className="p-4 rounded-md border border-gray-200 bg-white"
              >
                <div className="text-sm text-gray-500 mb-1">
                  {new Date(m.created_at).toLocaleString()}
                </div>
                <div className="text-gray-900">{m.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
