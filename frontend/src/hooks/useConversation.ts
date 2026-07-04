import { useState, useCallback } from 'react';
import { api } from '../services/api';
import { getEndpoint } from '../utils';

interface UseConversationReturn {
  response: string;
  thinking: string;
  imageUrl: string;
  audioUrl: string;
  isLoading: boolean;
  conversationStarted: boolean;
  submit: (text: string, mode: string) => Promise<void>;
  setAudioUrl: (url: string) => void;
  clear: () => void;
}

export function useConversation(): UseConversationReturn {
  const [response, setResponse] = useState('');
  const [thinking, setThinking] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationStarted, setConversationStarted] = useState(false);

  const submit = useCallback(async (text: string, mode: string) => {
    if (!text.trim() || isLoading) return;
    setIsLoading(true);
    setConversationStarted(true);

    try {
      if (mode === 'images') {
        const blob = await api.generateImage(text);
        setImageUrl(URL.createObjectURL(blob));
      } else if (mode === 'thinking') {
        const result = await api.generateWithThinking(text);
        setThinking(result.thinking_summary?.join('\n') || '');
        setResponse(result.response || '');
      } else if (mode === 'web') {
        const result = await api.generateWithUrlContext(text);
        setResponse(result || '');
      } else {
        const result = await api.generate(text);
        setResponse(result || '');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clear = useCallback(() => {
    setResponse('');
    setThinking('');
    setImageUrl('');
    setAudioUrl('');
    setIsLoading(false);
    setConversationStarted(false);
  }, []);

  return {
    response,
    thinking,
    imageUrl,
    audioUrl,
    isLoading,
    conversationStarted,
    submit,
    setAudioUrl,
    clear,
  };
}
