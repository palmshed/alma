// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import { useState, useCallback, useRef } from 'react';
import { api } from '../services/api';
import type { AttachmentData, MessageData, ConversationData } from '../types';

interface UseConversationReturn {
  messages: MessageData[];
  isLoading: boolean;
  conversationStarted: boolean;
  error: string | null;
  submit: (text: string, mode: string, convMessages?: MessageData[], attachments?: AttachmentData[], language?: string, model?: string) => Promise<boolean>;
  clear: () => void;
  loadConversation: (conv: ConversationData) => void;
  reconcileMessages: (newMessages: MessageData[]) => void;
  getMessages: () => MessageData[];
}

export function useConversation(): UseConversationReturn {
  const [messages, setMessages] = useState<MessageData[]>([]);
  const messagesRef = useRef<MessageData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const conversationStarted = messages.length > 0 || isLoading;

  const submit = useCallback(async (text: string, mode: string, convMessages?: MessageData[], attachments?: AttachmentData[], language?: string, model?: string) => {
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
    const baseMessages = (convMessages && convMessages.length >= messagesRef.current.length)
      ? convMessages
      : messagesRef.current.slice(0, -1);
    const history = [...baseMessages, userMsg];

    async function tryRequest(): Promise<{ responseText: string; thinkingText: string; durationMs: number; sourcesData?: any[]; stepsData?: string[]; intent?: string }> {
      const t0 = performance.now();
      let responseText: string;
      let thinkingText: string;
      let sourcesData: any[] | undefined;
      let stepsData: string[] | undefined;
      let intent: string | undefined;

      if (mode === 'images') {
        const blob = await api.generateImage(text);
        const url = URL.createObjectURL(blob);
        responseText = '[Image generated]';
        thinkingText = '';
      } else if (mode === 'thinking') {
        const result = await api.generateWithThinking(text, history, language, model);
        responseText = result.response || '';
        thinkingText = result.thinking_summary?.map((s: string) => s.replace(/[,;:\s-]+$/, '')).join('\n') || '';
      } else if (['search', 'auto', 'code', 'web'].includes(mode)) {
        const searchRes = await api.search(text, history, { mode, language, ai_provider: model });
        responseText = searchRes.response || '';
        thinkingText = '';
        sourcesData = searchRes.sources;
        stepsData = searchRes.search_steps;
        intent = searchRes.intent;
      } else {
        responseText = await api.generate(text, history, mode, language, model);
        thinkingText = '';
      }
      return { responseText, thinkingText, durationMs: performance.now() - t0, sourcesData, stepsData, intent };
    }

    try {
      const result = await tryRequest();
      const msg: MessageData = {
        id: '', role: 'assistant', content: result.responseText,
        thinking: result.thinkingText || undefined,
        timestamp: new Date().toISOString(),
        sources: result.sourcesData || undefined,
        search_steps: result.stepsData || undefined,
        intent: result.intent,
        ...(mode === 'thinking' && result.durationMs ? { thinking_duration_sec: Math.round(result.durationMs / 1000) } : {}),
      };
      setMessages(prev => {
        const next = [...prev, msg];
        messagesRef.current = next;
        return next;
      });
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      setError(msg);
      console.error(err);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

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
