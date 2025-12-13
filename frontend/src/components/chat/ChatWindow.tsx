'use client';

import { useState, useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { Message, ChatResponse } from '@/types';
import { Send, Loader2 } from 'lucide-react';
import { logger } from '@/utils/logger';

interface ChatWindowProps {
  conversationId: string;
  cloneId?: string;
  cloneName: string;
  messages: Message[];
  onSendMessage: (content: string) => Promise<ChatResponse>;
}

export function ChatWindow({
  conversationId,
  cloneId,
  cloneName,
  messages: initialMessages,
  onSendMessage,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync external messages → internal state
  useEffect(() => {
    setMessages(initialMessages);
  }, [initialMessages]);

  // Auto-scroll on update
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    });
  };

  const sanitize = (str: string) =>
    str.replace(/[\u0000-\u001f\u007f]/g, '').trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    const cleaned = sanitize(inputValue);
    if (!cleaned) return;

    setLoading(true);
    setInputValue('');

    logger.info('chat.message.send', {
      conversationId,
      length: cleaned.length,
    });

    try {
      const response = await onSendMessage(cleaned);

      // Sécurisation : empêcher des injections malformées
      if (!response?.user_message || !response?.clone_message) {
        throw new Error('Invalid response structure');
      }

      setMessages((prev) => [
        ...prev,
        response.user_message,
        response.clone_message,
      ]);

      logger.info('chat.message.received', {
        conversationId,
        userMessageId: response.user_message.id,
        cloneMessageId: response.clone_message.id,
      });
    } catch (err) {
      logger.error('chat.message.error', {
        conversationId,
        error:
          err instanceof Error
            ? err.message.slice(0, 200)
            : 'Unknown error',
      });

      const fallback: Message = {
        id: 'error-' + Date.now(),
        conversation_id: conversationId,
        role: 'system',
        content:
          'An error occurred while sending your message. Please try again.',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, fallback]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* CHAT BODY */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500">
              Start a conversation with {cloneName}
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              cloneName={cloneName}
              cloneId={cloneId}
            />
          ))
        )}

        {loading && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sage-200 to-sage-300 flex items-center justify-center">
              <Loader2 className="w-4 h-4 text-sage-700 animate-spin" />
            </div>
            <div className="bg-white rounded-2xl rounded-tl-sm shadow-soft px-4 py-3">
              <p className="text-sm text-gray-500 italic">
                {cloneName} is thinking...
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* INPUT BAR */}
      <div className="border-t border-cream-200 p-6 bg-white">
        <form onSubmit={handleSubmit} className="flex space-x-4">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={loading}
            placeholder={`Message ${cloneName}...`}
            autoComplete="off"
            className="flex-1 input-field disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={loading || !sanitize(inputValue)}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Send className="w-4 h-4" />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
