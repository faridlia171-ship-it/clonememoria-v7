'use client';

import { useState } from 'react';
import { Message } from '@/types';
import { User, Bot, Volume2, Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';

interface MessageBubbleProps {
  message: Message;
  cloneName: string;
  cloneId?: string;
}

export function MessageBubble({ message, cloneName, cloneId }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [playingAudio, setPlayingAudio] = useState(false);
  const [loadingAudio, setLoadingAudio] = useState(false);

  const handlePlayTTS = async () => {
    if (!cloneId || isUser) return;

    setLoadingAudio(true);
    try {
      logger.info('Generating TTS', { cloneId, messageId: message.id });
      const response = await apiClient.generateTTS(cloneId, message.content);

      const audioData = atob(response.audio_base64);
      const audioArray = new Uint8Array(audioData.length);
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i);
      }

      const blob = new Blob([audioArray], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);

      setPlayingAudio(true);
      audio.onended = () => {
        setPlayingAudio(false);
        URL.revokeObjectURL(url);
      };

      await audio.play();
      logger.info('TTS playback started');
    } catch (error) {
      logger.error('Failed to play TTS', { error });
      alert(error instanceof Error ? error.message : 'Failed to play audio');
    } finally {
      setLoadingAudio(false);
    }
  };

  return (
    <div
      className={`flex items-start space-x-3 ${
        isUser ? 'flex-row-reverse space-x-reverse' : ''
      }`}
    >
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-gradient-to-br from-rose-300 to-rose-400'
            : 'bg-gradient-to-br from-sage-200 to-sage-300'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-rose-700" />
        ) : (
          <Bot className="w-4 h-4 text-sage-700" />
        )}
      </div>

      <div className={`flex-1 max-w-[70%] ${isUser ? 'items-end' : ''}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-rose-100 text-gray-900 rounded-tr-sm'
              : 'bg-white text-gray-900 rounded-tl-sm shadow-soft'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        <div
          className={`mt-1 flex items-center space-x-2 ${
            isUser ? 'justify-end' : 'justify-start'
          }`}
        >
          <span className="text-xs text-gray-400">
            {new Date(message.created_at).toLocaleTimeString('en-US', {
              hour: 'numeric',
              minute: '2-digit',
            })}
          </span>

          {!isUser && cloneId && (
            <button
              onClick={handlePlayTTS}
              disabled={loadingAudio || playingAudio}
              className="text-gray-400 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Play as audio"
            >
              {loadingAudio ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Volume2 className={`w-4 h-4 ${playingAudio ? 'text-blue-600' : ''}`} />
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
