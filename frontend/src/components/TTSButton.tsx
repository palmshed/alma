import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

let currentAudioEl: HTMLAudioElement | null = null;

interface TTSButtonProps {
  text: string;
  auto?: boolean;
  audioBase64?: string;
  voiceError?: string;
}

const TTSButton: React.FC<TTSButtonProps> = ({ text, auto = false, audioBase64, voiceError }) => {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const initializedRef = useRef(false);
  const previousAudioUrlRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stopPreviousAudio = () => {
    if (currentAudioEl && currentAudioEl !== audioRef.current) {
      currentAudioEl.pause();
      currentAudioEl.src = '';
    }
  };

  const playAudio = (url: string) => {
    stopPreviousAudio();
    const audio = new Audio(url);
    currentAudioEl = audio;
    audioRef.current = audio;
    audio.play().catch(() => {});
  };

  const handleTTS = async () => {
    if (!text.trim() || isLoading) return;
    setIsLoading(true);
    try {
      const blob = await api.textToSpeech(text);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      playAudio(url);
    } catch {
      console.error('TTS failed');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (audioBase64) {
      if (previousAudioUrlRef.current) {
        URL.revokeObjectURL(previousAudioUrlRef.current);
      }
      const url = `data:audio/mp3;base64,${audioBase64}`;
      setAudioUrl(url);
      previousAudioUrlRef.current = url;
      if (auto) {
        playAudio(url);
      }
      return;
    }

    if (auto && !initializedRef.current && text.trim()) {
      initializedRef.current = true;
      if (!voiceError) {
        handleTTS();
      }
    }
  }, [auto, text, audioBase64, voiceError]);

  if (!text.trim()) return null;

  if (auto) {
    return (
      <div className="response-actions">
        {isLoading && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Generating voice...</span>
        )}
        {voiceError && !audioUrl && !isLoading && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Voice couldn't be generated. Gemini TTS is temporarily unavailable.</span>
        )}
        {audioUrl && (
          <audio controls className="audio-player" style={{ display: 'block' }}>
            <source src={audioUrl} type="audio/mp3" />
          </audio>
        )}
      </div>
    );
  }

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
