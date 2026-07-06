import React, { useState } from 'react';
import { api } from '../services/api';

interface TTSButtonProps {
  text: string;
}

const TTSButton: React.FC<TTSButtonProps> = ({ text }) => {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleTTS = async () => {
    if (!text.trim()) return;
    setIsLoading(true);
    try {
      const blob = await api.textToSpeech(text);
      setAudioUrl(URL.createObjectURL(blob));
    } catch {
      console.error('TTS failed');
    } finally {
      setIsLoading(false);
    }
  };

  if (!text.trim()) return null;

  return (
    <div className="response-actions">
      <button
        onClick={handleTTS}
        disabled={isLoading}
        className={`btn btn--ghost message-tts-btn ${isLoading ? 'loading' : ''}`}
      >
        {isLoading ? 'Generating...' : 'Listen'}
      </button>
      {audioUrl && (
        <audio controls className="audio-player" style={{ display: 'block' }}>
          <source src={audioUrl} type="audio/mp3" />
        </audio>
      )}
    </div>
  );
};

export default TTSButton;
