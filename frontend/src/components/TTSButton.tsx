import React, { useState } from 'react';
import { api } from '../services/api';

interface TTSButtonProps {
  text: string;
  onAudio: (url: string) => void;
}

const TTSButton: React.FC<TTSButtonProps> = ({ text, onAudio }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleTTS = async () => {
    if (!text.trim()) return;
    setIsLoading(true);
    try {
      const blob = await api.textToSpeech(text);
      const url = URL.createObjectURL(blob);
      onAudio(url);
    } catch {
    } finally {
      setIsLoading(false);
    }
  };

  if (!text.trim()) return null;

  return (
    <button
      onClick={handleTTS}
      disabled={isLoading}
      className={`button button-secondary ${isLoading ? 'loading' : ''}`}
    >
      {isLoading ? 'Generating...' : 'Listen'}
    </button>
  );
};

export default TTSButton;
