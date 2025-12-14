'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { AppLayout } from '@/components/layout/AppLayout';
import { ChatWindow } from '@/components/chat/ChatWindow';
import apiClient from '@/lib/apiClient';
import { logger } from '@/utils/logger';
import { Clone, Conversation, Message, ChatResponse } from '@/types';
import { ArrowLeft, Loader2 } from 'lucide-react';

export default function ChatPage() {
  const params = useParams();
  const cloneId = params?.id as string | undefined;

  const [clone, setClone] = useState<Clone | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!cloneId) {
      logger.error('ChatPage: missing cloneId in route params');
      setLoading(false);
      return;
    }

    logger.info('ChatPage mounted', { cloneId });
    void initializeChat();
  }, [cloneId]);

  const initializeChat = async () => {
    if (!cloneId) return;

    try {
      logger.info('ChatPage initialization started', { cloneId });

      // 1️⃣ Clone
      const cloneData = await apiClient.getCloneById(cloneId);
      setClone(cloneData);

      // 2️⃣ Conversations
      const conversations = await apiClient.getCloneConversations(cloneId);

      let activeConv: Conversation;

      if (conversations.length > 0) {
        activeConv = conversations[0];
      } else {
        activeConv = await apiClient.createConversation(
          cloneId,
          `Chat with ${cloneData.name}`
        );
      }

      setConversation(activeConv);

      // 3️⃣ Messages
      const msgs = await apiClient.getConversationMessages(activeConv.id);
      setMessages(msgs);

      logger.info('Chat initialized successfully', {
        cloneId,
        conversationId: activeConv.id,
        messageCount: msgs.length,
      });
    } catch (error: any) {
      logger.error('Chat initialization failed', {
        cloneId,
        error: error?.message ?? 'Unknown error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = useCallback(
    async (content: string): Promise<ChatResponse> => {
      if (!conversation) {
        throw new Error('No active conversation');
      }

      return apiClient.sendMessage(
        cloneId!,
        conversation.id,
        content
      );
    },
    [cloneId, conversation]
  );

  if (loading) {
    return (
      <AppLayout>
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-rose-400 animate-spin" />
        </div>
      </AppLayout>
    );
  }

  if (!clone || !conversation) {
    return (
      <AppLayout>
        <div className="max-w-xl mx-auto text-center py-12">
          <h2 className="text-xl font-display mb-4">Chat unavailable</h2>
          <p className="text-gray-600 mb-6">
            Impossible d'initialiser ce chat.
          </p>

          <Link
            href="/clones"
            className="px-4 py-2 rounded-md bg-rose-500 text-white hover:bg-rose-600 transition"
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
