'use client';

import Link from 'next/link';
import { CloneWithStats } from '@/types';
import { MessageCircle, BookOpen, User } from 'lucide-react';
import { useMemo } from 'react';

interface CloneCardProps {
  clone: CloneWithStats;
}

export function CloneCard({ clone }: CloneCardProps) {
  // Sécurisation totale des données
  const safe = useMemo(() => ({
    id: clone?.id ?? '',
    name: clone?.name?.toString().trim() || 'Unnamed Clone',
    description: clone?.description?.toString().trim() || 'No description provided',
    avatar: clone?.avatar_url || null,
    memoryCount: Number.isFinite(clone?.memory_count) ? clone.memory_count : 0,
    conversationCount: Number.isFinite(clone?.conversation_count) ? clone.conversation_count : 0,
    warmth: Number.isFinite(clone?.tone_config?.warmth)
      ? Math.round(clone.tone_config.warmth * 100)
      : 0,
    humor: Number.isFinite(clone?.tone_config?.humor)
      ? Math.round(clone.tone_config.humor * 100)
      : 0,
  }), [clone]);

  return (
    <Link href={`/clones/${safe.id}`}>
      <div className="card hover:shadow-soft-lg transition-shadow duration-200 cursor-pointer h-full">
        <div className="flex items-start space-x-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-rose-200 to-rose-300 flex items-center justify-center flex-shrink-0 overflow-hidden">

            {safe.avatar ? (
              <img
                src={safe.avatar}
                alt={safe.name}
                className="w-full h-full rounded-2xl object-cover"
                onError={(e) => {
                  // Fallback robuste en cas d’URL cassée
                  e.currentTarget.style.display = "none";
                  (e.currentTarget.parentNode as HTMLElement).innerHTML =
                    '<svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-3A2.25 2.25 0 008.25 5.25V9m0 0H5.25A2.25 2.25 0 003 11.25v9A2.25 2.25 0 005.25 22.5h13.5A2.25 2.25 0 0021 20.25v-9A2.25 2.25 0 0018.75 9h-3m-7.5 0h7.5" /></svg>';
                }}
              />
            ) : (
              <User className="w-8 h-8 text-rose-600" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-xl font-display text-gray-900 mb-1 truncate">
              {safe.name}
            </h3>
            <p className="text-gray-600 text-sm line-clamp-2 mb-3">
              {safe.description}
            </p>

            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <div className="flex items-center space-x-1">
                <BookOpen className="w-4 h-4" />
                <span>
                  {safe.memoryCount} {safe.memoryCount === 1 ? 'memory' : 'memories'}
                </span>
              </div>
              <div className="flex items-center space-x-1">
                <MessageCircle className="w-4 h-4" />
                <span>
                  {safe.conversationCount}{' '}
                  {safe.conversationCount === 1 ? 'conversation' : 'conversations'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center space-x-2 text-xs text-gray-400">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 rounded-full bg-rose-300"></div>
            <span>Warmth {safe.warmth}%</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 rounded-full bg-sage-300"></div>
            <span>Humor {safe.humor}%</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

