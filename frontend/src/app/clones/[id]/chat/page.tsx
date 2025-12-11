'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { Clone, Conversation, Message, ChatResponse } from '@/types';
import { ArrowLeft, Loader2 } from 'lucide-react';

export default function ChatPage() {
  const params = useParams();
  const cloneId = params.id as string;

  const [clone, setClone] = useState<Clone | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    logger.info('ChatPage loaded', { cloneId });
    initializeChat();
  }, [cloneId]);

  const initializeChat = async () => {
    try {
      const cloneData = await apiClient.get<Clone>(
        `/api/clones/${cloneId}`,
        true
      );
      setClone(cloneData);

      const conversations = await apiClient.get<Conversation[]>(
        `/api/clones/${cloneId}/conversations`,
        true
      );

      let currentConversation: Conversation;

      if (conversations.length > 0) {
        currentConversation = conversations[0];
        logger.info('Using existing conversation', {
          conversationId: currentConversation.id,
        });
      } else {
        currentConversation = await apiClient.post<Conversation>(
          `/api/clones/${cloneId}/conversations`,
          { title: `Chat with ${cloneData.name}` },
          true
        );
        logger.info('Created new conversation', {
          conversationId: currentConversation.id,
        });
      }

      setConversation(currentConversation);

      const messagesData = await apiClient.get<Message[]>(
        `/api/clones/${cloneId}/conversations/${currentConversation.id}/messages`,
        true
      );
      setMessages(messagesData);

      logger.info('Chat initialized', {
        cloneId,
        conversationId: currentConversation.id,
        messageCount: messagesData.length,
      });
    } catch (error) {
      logger.error('Failed to initialize chat', {
        cloneId,
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (content: string): Promise<ChatResponse> => {
    if (!conversation) throw new Error('No conversation active');

    const response = await apiClient.post<ChatResponse>(
      `/api/clones/${cloneId}/conversations/${conversation.id}/messages`,
      { content },
      true
    );

    return response;
  };

  if (loading || !clone || !conversation) {
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
      <div className="max-w-5xl mx-auto">
        <Link
          href={`/clones/${cloneId}`}
          className="inline-flex items-center space-x-2 text-gray-600 hover:text-rose-500 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Clone</span>
        </Link>

        <div className="card p-0 overflow-hidden" style={{ height: '70vh' }}>
          <div className="bg-gradient-to-r from-cream-100 to-rose-50 px-6 py-4 border-b border-cream-200">
            <h1 className="text-2xl font-display text-gray-900">
              Chat with {clone.name}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              {clone.description || 'No description'}
            </p>
          </div>

          <ChatWindow
            conversationId={conversation.id}
            cloneName={clone.name}
            messages={messages}
            onSendMessage={handleSendMessage}
          />
        </div>
      </div>
    </AppLayout>
  );
}
