// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import { useState, useCallback, useRef } from 'react';
import { api, isQuotaError } from '../services/api';
import type { AttachmentData, MessageData, ConversationData } from '../types';

interface UseConversationReturn {
  messages: MessageData[];
  isLoading: boolean;
  conversationStarted: boolean;
  error: string | null;
  submit: (text: string, mode: string, convMessages?: MessageData[], attachments?: AttachmentData[], model?: string) => Promise<boolean>;
  clear: () => void;
  loadConversation: (conv: ConversationData) => void;
  reconcileMessages: (newMessages: MessageData[]) => void;
  getMessages: () => MessageData[];
}

interface UseConversationOptions {
  onQuotaError?: (model: string, retryAfter?: number) => void;
  autoMode?: boolean;
  getFallbackModel?: (failedModel: string) => string | undefined;
}

export function useConversation(options?: UseConversationOptions): UseConversationReturn {
  const [messages, setMessages] = useState<MessageData[]>([]);
  const messagesRef = useRef<MessageData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const conversationStarted = messages.length > 0 || isLoading;

  const submit = useCallback(async (text: string, mode: string, convMessages?: MessageData[], attachments?: AttachmentData[], model?: string) => {
    if (!text.trim() || isLoading) return false;
    setIsLoading(true);
    setError(null);

    const ts = new Date().toISOString();
    const attData = attachments?.map(a => ({ id: a.id, filename: a.filename, mime_type: a.mime_type, size: a.size }));
    const userMsg: MessageData = {
      id: '', role: 'user', content: text, timestamp: ts,
      ...(attData && attData.length > 0 ? { attachments: attData as unknown as Record<string, unknown>[] } : {}),
    };
    setMessages(prev => {
      const next = [...prev, userMsg];
      messagesRef.current = next;
      return next;
    });

    /* Build full conversation history for outbound request */
    const history = convMessages
      ? [...convMessages, userMsg]
      : [userMsg];

    let usedFallback = false;
    let actualModel = model;
    const firstModel = model;

    async function tryRequest(requestModel: string): Promise<{ responseText: string; thinkingText: string; durationMs: number }> {
      const t0 = performance.now();
      let responseText: string;
      let thinkingText: string;
      if (mode === 'images') {
        const blob = await api.generateImage(text);
        const url = URL.createObjectURL(blob);
        responseText = '[Image generated]';
        thinkingText = '';
      } else if (mode === 'thinking') {
        const result = await api.generateWithThinking(text, history, requestModel);
        responseText = result.response || '';
        thinkingText = result.thinking_summary?.map((s: string) => s.replace(/[,;:\s-]+$/, '')).join('\n') || '';
      } else if (mode === 'web') {
        responseText = await api.generateWithUrlContext(text, history, requestModel);
        thinkingText = '';
      } else {
        responseText = await api.generate(text, history, requestModel);
        thinkingText = '';
      }
      return { responseText, thinkingText, durationMs: performance.now() - t0 };
    }

    try {
      try {
        const result = await tryRequest(actualModel!);
        const msg: MessageData = {
          id: '', role: 'assistant', content: result.responseText,
          thinking: result.thinkingText || undefined,
          timestamp: new Date().toISOString(),
          model: actualModel,
          ...(mode === 'thinking' && result.durationMs ? { thinking_duration_sec: Math.round(result.durationMs / 1000) } : {}),
        };
        if (usedFallback && options?.autoMode) {
          msg.metadata = { autoFallback: true, requestedModel: 'auto', resolvedModel: firstModel, fallbackModel: actualModel };
        }
        setMessages(prev => {
          const next = [...prev, msg];
          messagesRef.current = next;
          return next;
        });
        return true;
      } catch (err) {
        if (actualModel && isQuotaError(err)) {
          options?.onQuotaError?.(actualModel, err.retryAfter);
          if (options?.autoMode && options?.getFallbackModel) {
            const fallback = options.getFallbackModel(actualModel);
            if (fallback && fallback !== actualModel) {
              usedFallback = true;
              actualModel = fallback;
              const result = await tryRequest(fallback);
              const msg: MessageData = {
                id: '', role: 'assistant', content: result.responseText,
                thinking: result.thinkingText || undefined,
                timestamp: new Date().toISOString(),
                model: fallback,
                metadata: { autoFallback: true, requestedModel: 'auto', resolvedModel: firstModel, fallbackModel: fallback },
                ...(mode === 'thinking' ? { thinking_duration_sec: Math.round(result.durationMs / 1000) } : {}),
              };
              setMessages(prev => {
                const next = [...prev, msg];
                messagesRef.current = next;
                return next;
              });
              return true;
            }
          }
        }
        throw err;
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      setError(msg);
      console.error(err);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, options]);

  const loadConversation = useCallback((conv: ConversationData) => {
    const next = conv.messages || [];
    messagesRef.current = next;
    setMessages(next);
    setError(null);
    setIsLoading(false);
  }, []);

  const clear = useCallback(() => {
    messagesRef.current = [];
    setMessages([]);
    setIsLoading(false);
    setError(null);
  }, []);

  const reconcileMessages = useCallback((newMessages: MessageData[]) => {
    messagesRef.current = newMessages;
    setMessages(newMessages);
  }, []);

  const getMessages = useCallback(() => messagesRef.current, []);

  return {
    messages, isLoading, conversationStarted, error,
    submit, clear, loadConversation, reconcileMessages, getMessages,
  };
}
