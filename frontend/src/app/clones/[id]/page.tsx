'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { Clone } from '@/types';
import { MessageCircle, BookOpen, Settings, Loader2, ArrowLeft } from 'lucide-react';

export default function CloneDetailPage() {
  const params = useParams();
  const router = useRouter();
  const cloneId = params.id as string;

  const [clone, setClone] = useState<Clone | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    logger.info('CloneDetailPage loaded', { cloneId });
    loadClone();
  }, [cloneId]);

  const loadClone = async () => {
    try {
      const data = await apiClient.get<Clone>(`/api/clones/${cloneId}`, true);
      setClone(data);
      logger.info('Clone loaded', { cloneId, cloneName: data.name });
    } catch (error) {
      logger.error('Failed to load clone', {
        cloneId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading || !clone) {
    return (
      <AppLayout>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto">
        <Link
          href="/dashboard"
          className="inline-flex items-center space-x-2 text-gray-600 hover:text-rose-500 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>

        <div className="card mb-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-4xl font-display text-gray-900 mb-2">
                {clone.name}
              </h1>
              <p className="text-gray-600">{clone.description}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 text-sm">
            <div className="px-4 py-2 bg-rose-50 rounded-xl text-rose-700">
              Warmth: {Math.round(clone.tone_config.warmth * 100)}%
            </div>
            <div className="px-4 py-2 bg-sage-50 rounded-xl text-sage-700">
              Humor: {Math.round(clone.tone_config.humor * 100)}%
            </div>
            <div className="px-4 py-2 bg-cream-200 rounded-xl text-gray-700">
              Formality: {Math.round(clone.tone_config.formality * 100)}%
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link href={`/clones/${cloneId}/chat`}>
            <div className="card hover:shadow-soft-lg transition-shadow duration-200 cursor-pointer h-full">
              <div className="flex items-center space-x-4 mb-4">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-rose-200 to-rose-300 flex items-center justify-center">
                  <MessageCircle className="w-6 h-6 text-rose-600" />
                </div>
                <h2 className="text-2xl font-display text-gray-900">
                  Chat
                </h2>
              </div>
              <p className="text-gray-600">
                Start a conversation with {clone.name}
              </p>
            </div>
          </Link>

          <Link href={`/clones/${cloneId}/memories`}>
            <div className="card hover:shadow-soft-lg transition-shadow duration-200 cursor-pointer h-full">
              <div className="flex items-center space-x-4 mb-4">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-sage-200 to-sage-300 flex items-center justify-center">
                  <BookOpen className="w-6 h-6 text-sage-600" />
                </div>
                <h2 className="text-2xl font-display text-gray-900">
                  Memories
                </h2>
              </div>
              <p className="text-gray-600">
                View and add memories for {clone.name}
              </p>
            </div>
          </Link>
        </div>
      </div>
    </AppLayout>
  );
}
