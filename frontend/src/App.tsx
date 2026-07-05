import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import Header from './components/Header';
import Composer from './components/Composer';
import SegmentedControl from './components/SegmentedControl';
import Chip from './components/Chip';
import LoadingDots from './components/LoadingDots';
import ResponseContainer from './components/ResponseContainer';
import ThinkingContainer from './components/ThinkingContainer';
import ImageContainer from './components/ImageContainer';
import TTSButton from './components/TTSButton';
import AudioPlayer from './components/AudioPlayer';
import Sidebar from './components/Sidebar';
import LandingLayout from './layouts/LandingLayout';
import ConversationLayout from './layouts/ConversationLayout';
import { useComposer } from './hooks/useComposer';
import { useConversation } from './hooks/useConversation';
import { MODES, SUGGESTIONS } from './utils';
import { api } from './services/api';
import { ConversationData, MessageData } from './types';

function App() {
  const [mode, setMode] = useState('canvas');
  const { input, setInput, clear: composerClear } = useComposer();
  const {
    response,
    thinking,
    imageUrl,
    audioUrl,
    isLoading,
    conversationStarted,
    submit,
    setAudioUrl,
    clear: conversationClear,
    loadConversation,
  } = useConversation();
  const [theme, setTheme] = useState<'dark' | 'light'>(
    (document.documentElement.getAttribute('data-theme') as 'dark' | 'light') || 'dark'
  );
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const lastPromptRef = useRef<string>('');
  const activeConversationRef = useRef<ConversationData | null>(null);

  useEffect(() => {
    if (!sidebarOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [sidebarOpen]);

  const handleThemeToggle = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  }, [theme]);

  const handleSubmit = useCallback((text: string) => {
    lastPromptRef.current = text;
    submit(text, mode);
  }, [submit, mode]);

  const handleNewChat = useCallback(() => {
    if (isLoading) return;
    const hasMessages = !!(response || thinking || imageUrl || audioUrl);
    if (hasMessages) {
      setShowNewChatDialog(true);
    } else {
      conversationClear();
      composerClear();
    }
  }, [response, thinking, imageUrl, audioUrl, isLoading, conversationClear, composerClear]);

  const handleConfirmNewChat = useCallback(() => {
    conversationClear();
    composerClear();
    setActiveConversationId(undefined);
    activeConversationRef.current = null;
    setShowNewChatDialog(false);
  }, [conversationClear, composerClear]);

  const handleCancelNewChat = useCallback(() => {
    setShowNewChatDialog(false);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        handleNewChat();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [handleNewChat]);

  const activeConv = useMemo(() => activeConversationId, [activeConversationId]);

  useEffect(() => {
    if (!response && !thinking) return;
    const prompt = lastPromptRef.current;
    if (!prompt) return;

    lastPromptRef.current = '';

    const existing = activeConversationRef.current?.messages ?? [];
    const newMessages: MessageData[] = [
      ...existing,
      { role: 'user', content: prompt, timestamp: new Date().toISOString() },
      { role: 'assistant', content: response || '', thinking: thinking || undefined, timestamp: new Date().toISOString() },
    ];
    const nextTitle = existing.length === 0
      ? (response || prompt).slice(0, 60)
      : undefined;

    if (activeConv) {
      api.updateConversation(activeConv, { messages: newMessages, ...(nextTitle ? { title: nextTitle } : {}) }).catch(() => {});
    } else {
      api.createConversation({ title: nextTitle ?? 'New conversation', messages: newMessages })
        .then((conv) => {
          setActiveConversationId(conv.id);
          activeConversationRef.current = conv;
        })
        .catch(() => {});
    }
  }, [response, thinking, activeConv]);

  useEffect(() => {
    if (!showNewChatDialog) {
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
        previousFocusRef.current = null;
      }
      return;
    }

    previousFocusRef.current = document.activeElement as HTMLElement;

    const dialog = dialogRef.current;
    if (!dialog) return;

    const focusable = dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (first) first.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setShowNewChatDialog(false);
        return;
      }
      if (e.key === 'Tab') {
        const active = document.activeElement;
        if (e.shiftKey && active === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [showNewChatDialog]);

  const suggestions = SUGGESTIONS[mode] || [];

  const composer = (
    <Composer
      value={input}
      onChange={setInput}
      onSubmit={handleSubmit}
      placeholder="Ask anything..."
      loading={isLoading}
      onClear={composerClear}
      autoFocus
    />
  );

  return (
    <div className="app-container">
      <Header theme={theme} onThemeToggle={handleThemeToggle} onMenuToggle={() => setSidebarOpen(true)} showTitle={conversationStarted} onNewChat={handleNewChat} />

      {!conversationStarted ? (
        <LandingLayout
          hero={
            <>
              <svg className="landing-palm" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
                <path d="M13 8c0-2.76-2.46-5-5.5-5S2 5.24 2 8h2l1-1 1 1h4" />
                <path d="M13 7.14A5.82 5.82 0 0 1 16.5 6c3.04 0 5.5 2.24 5.5 5h-3l-1-1-1 1h-3" />
                <path d="M5.89 9.71c-2.15 2.15-2.3 5.47-.35 7.43l4.24-4.25.7-.7.71-.71 2.12-2.12c-1.95-1.96-5.27-1.8-7.42.35" />
                <path d="M11 15.5c.5 2.5-.17 4.5-1 6.5h4c2-5.5-.5-12-1-14" />
              </svg>
              <span className="landing-title">Alma</span>
            </>
          }
          composer={composer}
          suggestions={
            !input && suggestions.length > 0 ? (
              <div className="landing-suggestions">
                {suggestions.map((s) => (
                  <Chip key={s} label={s} onClick={() => { setInput(s); submit(s, mode); }} />
                ))}
              </div>
            ) : undefined
          }
          modes={
            <SegmentedControl
              options={MODES}
              value={mode}
              onChange={setMode}
            />
          }
        />
      ) : (
        <ConversationLayout
          messages={
            <>
              {isLoading && (
                <div className="conversation-loading">
                  <LoadingDots label="Generating" />
                </div>
              )}
              {thinking && <ThinkingContainer content={thinking} />}
              {response && <ResponseContainer content={response} />}
              {imageUrl && <ImageContainer imageUrl={imageUrl} />}
              {response && <TTSButton text={response} onAudio={setAudioUrl} />}
              {audioUrl && <AudioPlayer src={audioUrl} />}
            </>
          }
          composer={
            <>
              {composer}
              <SegmentedControl
                options={MODES}
                value={mode}
                onChange={setMode}
              />
            </>
          }
        />
      )}

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectConversation={(id) => {
          api.getConversation(id).then((conv) => {
            activeConversationRef.current = conv;
            setActiveConversationId(id);
            loadConversation(conv);
          }).catch(() => {});
        }}
        onDeleteConversation={() => {
          setActiveConversationId(undefined);
          activeConversationRef.current = null;
        }}
        activeConversationId={activeConversationId}
      />

      {showNewChatDialog && (
        <>
          <div className="dialog-overlay" onClick={handleCancelNewChat} />
          <div className="dialog" ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="dialog-title">
            <p id="dialog-title" className="dialog-title">Start a new conversation?</p>
            <p className="dialog-description">Your current conversation will be cleared.</p>
            <div className="dialog-actions">
              <button className="btn dialog-btn dialog-btn--cancel" onClick={handleCancelNewChat} type="button">Cancel</button>
              <button className="btn btn--primary dialog-btn dialog-btn--confirm" onClick={handleConfirmNewChat} type="button">New conversation</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;
