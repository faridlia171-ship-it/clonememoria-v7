'use client';

import Link from 'next/link';
import { CloneWithStats } from '@/types';
import { MessageCircle, BookOpen, User } from 'lucide-react';

interface CloneCardProps {
  clone: CloneWithStats;
}

export function CloneCard({ clone }: CloneCardProps) {
  return (
    <Link href={`/clones/${clone.id}`}>
      <div className="card hover:shadow-soft-lg transition-shadow duration-200 cursor-pointer h-full">
        <div className="flex items-start space-x-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-rose-200 to-rose-300 flex items-center justify-center flex-shrink-0">
            {clone.avatar_url ? (
              <img
                src={clone.avatar_url}
                alt={clone.name}
                className="w-full h-full rounded-2xl object-cover"
              />
            ) : (
              <User className="w-8 h-8 text-rose-600" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-xl font-display text-gray-900 mb-1 truncate">
              {clone.name}
            </h3>
            <p className="text-gray-600 text-sm line-clamp-2 mb-3">
              {clone.description || 'No description provided'}
            </p>

            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <div className="flex items-center space-x-1">
                <BookOpen className="w-4 h-4" />
                <span>
                  {clone.memory_count}{' '}
                  {clone.memory_count === 1 ? 'memory' : 'memories'}
                </span>
              </div>
              <div className="flex items-center space-x-1">
                <MessageCircle className="w-4 h-4" />
                <span>
                  {clone.conversation_count}{' '}
                  {clone.conversation_count === 1
                    ? 'conversation'
                    : 'conversations'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center space-x-2 text-xs text-gray-400">
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 rounded-full bg-rose-300"></div>
            <span>Warmth {Math.round(clone.tone_config.warmth * 100)}%</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 rounded-full bg-sage-300"></div>
            <span>Humor {Math.round(clone.tone_config.humor * 100)}%</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
