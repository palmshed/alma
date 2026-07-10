import { useState, useCallback } from 'react';
import { api, isQuotaError } from '../services/api';
import type { AttachmentData, MessageData, ConversationData } from '../types';

interface UseConversationReturn {
  messages: MessageData[];
  isLoading: boolean;
  conversationStarted: boolean;
  error: string | null;
  submit: (text: string, mode: string, convMessages?: MessageData[], attachments?: AttachmentData[], model?: string) => Promise<void>;
  clear: () => void;
  loadConversation: (conv: ConversationData) => void;
  reconcileMessages: (newMessages: MessageData[]) => void;
}

interface UseConversationOptions {
  onQuotaError?: (model: string, retryAfter?: number) => void;
}

export function useConversation(options?: UseConversationOptions): UseConversationReturn {
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const conversationStarted = messages.length > 0 || isLoading;

  const submit = useCallback(async (text: string, mode: string, convMessages?: MessageData[], attachments?: AttachmentData[], model?: string) => {
    if (!text.trim() || isLoading) return;
    setIsLoading(true);
    setError(null);

    const ts = new Date().toISOString();
    const attData = attachments?.map(a => ({ id: a.id, filename: a.filename, mime_type: a.mime_type, size: a.size }));
    const userMsg: MessageData = {
      id: '', role: 'user', content: text, timestamp: ts,
      ...(attData && attData.length > 0 ? { attachments: attData as unknown as Record<string, unknown>[] } : {}),
    };
    setMessages(prev => [...prev, userMsg]);

    /* Build full conversation history for outbound request */
    const history = convMessages
      ? [...convMessages, userMsg]
      : [userMsg];

    try {
      if (mode === 'images') {
        const blob = await api.generateImage(text);
        const url = URL.createObjectURL(blob);
        setMessages(prev => [...prev, {
          id: '', role: 'assistant', content: '[Image generated]', image: url, timestamp: new Date().toISOString(),
          model,
        }]);
      } else {
        let responseText = '';
        let thinkingText = '';
        if (mode === 'thinking') {
          const result = await api.generateWithThinking(text, history, model);
          responseText = result.response || '';
          thinkingText = result.thinking_summary?.join('\n') || '';
        } else if (mode === 'web') {
          responseText = await api.generateWithUrlContext(text, history, model);
        } else {
          responseText = await api.generate(text, history, model);
        }
        setMessages(prev => [...prev, {
          id: '', role: 'assistant', content: responseText,
          thinking: thinkingText || undefined,
          timestamp: new Date().toISOString(),
          model,
        }]);
      }
    } catch (err) {
      if (model && isQuotaError(err)) {
        options?.onQuotaError?.(model, err.retryAfter);
      }
      const msg = err instanceof Error ? err.message : 'Request failed';
      setError(msg);
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, options]);

  const loadConversation = useCallback((conv: ConversationData) => {
    setMessages(conv.messages || []);
    setError(null);
    setIsLoading(false);
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    setIsLoading(false);
    setError(null);
  }, []);

  const reconcileMessages = useCallback((newMessages: MessageData[]) => {
    setMessages(newMessages);
  }, []);

  return {
    messages, isLoading, conversationStarted, error,
    submit, clear, loadConversation, reconcileMessages,
  };
}
