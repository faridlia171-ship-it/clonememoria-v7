'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { MemoryForm } from '@/components/forms/MemoryForm';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { Memory } from '@/types';
import { ArrowLeft, Plus, BookOpen, Loader2, Calendar } from 'lucide-react';

export default function MemoriesPage() {
  const params = useParams();
  const cloneId = params.id as string;

  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);

  useEffect(() => {
    logger.info('MemoriesPage loaded', { cloneId });
    loadMemories();
  }, [cloneId]);

  const loadMemories = async () => {
    try {
      const data = await apiClient.get<Memory[]>(
        `/api/clones/${cloneId}/memories`,
        true
      );
      setMemories(data);
      logger.info('Memories loaded', { cloneId, count: data.length });
    } catch (error) {
      logger.error('Failed to load memories', {
        cloneId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateMemory = async (data: {
    title?: string;
    content: string;
  }) => {
    logger.info('Creating memory', { cloneId });

    await apiClient.post(
      `/api/clones/${cloneId}/memories`,
      {
        ...data,
        source_type: 'manual',
      },
      true
    );

    logger.info('Memory created successfully');
    setShowCreateForm(false);
    await loadMemories();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

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

        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-display text-gray-900 mb-2">
              Memories
            </h1>
            <p className="text-gray-600">
              Add memories to help the AI understand and emulate this person
            </p>
          </div>

          {!showCreateForm && (
            <button
              onClick={() => setShowCreateForm(true)}
              className="btn-primary flex items-center space-x-2"
            >
              <Plus className="w-5 h-5" />
              <span>Add Memory</span>
            </button>
          )}
        </div>

        {showCreateForm && (
          <div className="card mb-8">
            <h2 className="text-2xl font-display text-gray-900 mb-6">
              Add New Memory
            </h2>
            <MemoryForm
              onSubmit={handleCreateMemory}
              onCancel={() => setShowCreateForm(false)}
            />
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-12">
            <div className="card max-w-md mx-auto">
              <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-display text-gray-900 mb-2">
                No memories yet
              </h3>
              <p className="text-gray-600 mb-6">
                Start adding memories to help the AI better understand and
                represent this person.
              </p>
              {!showCreateForm && (
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="btn-primary"
                >
                  Add Your First Memory
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {memories.map((memory) => (
              <div key={memory.id} className="card">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="text-lg font-display text-gray-900">
                    {memory.title || 'Untitled Memory'}
                  </h3>
                  <div className="flex items-center space-x-2 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" />
                    <span>{formatDate(memory.created_at)}</span>
                  </div>
                </div>
                <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                  {memory.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
