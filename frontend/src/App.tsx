import React, { useState, useCallback, useEffect, useRef } from 'react';
import Header from './components/Header';
import Composer from './components/Composer';
import SegmentedControl from './components/SegmentedControl';
import Chip from './components/Chip';
import LoadingDots from './components/LoadingDots';
import ResponseContainer from './components/ResponseContainer';
import ThinkingContainer from './components/ThinkingContainer';
import ImageContainer from './components/ImageContainer';
import TTSButton from './components/TTSButton';
import UserMessage from './components/UserMessage';
import Sidebar from './components/Sidebar';
import LandingLayout from './layouts/LandingLayout';
import ConversationLayout from './layouts/ConversationLayout';
import { useComposer } from './hooks/useComposer';
import { useConversation } from './hooks/useConversation';
import { MODES, SUGGESTIONS } from './utils';
import { api } from './services/api';
import { ConversationData } from './types';

const STORAGE_ACTIVE_CONV = 'alma_active_conversation';

function getStorage(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function setStorage(key: string, value: string): void {
  try { localStorage.setItem(key, value); } catch { /* noop */ }
}
function removeStorage(key: string): void {
  try { localStorage.removeItem(key); } catch { /* noop */ }
}

function App() {
  const [mode, setMode] = useState('canvas');
  const initialStored = getStorage(STORAGE_ACTIVE_CONV);
  const [restoring, setRestoring] = useState(!!initialStored);
  const { input, setInput, clear: composerClear } = useComposer();
  const {
    messages, isLoading, conversationStarted, error,
    submit, clear: conversationClear, loadConversation, reconcileMessages,
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
  const restoredRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const reconcilingRef = useRef(false);

  useEffect(() => {
    if (!sidebarOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false);
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [sidebarOpen]);

  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const storedId = getStorage(STORAGE_ACTIVE_CONV);
    if (!storedId) return;
    let cancelled = false;
    api.getConversation(storedId).then((conv) => {
      if (cancelled) return;
      activeConversationRef.current = conv;
      setActiveConversationId(storedId);
      loadConversation(conv);
      if (conv.mode) setMode(conv.mode);
    }).catch(() => {
      if (!cancelled) removeStorage(STORAGE_ACTIVE_CONV);
    }).finally(() => {
      if (!cancelled) setRestoring(false);
    });
    return () => { cancelled = true; };
  }, [loadConversation]);

  /* Persist messages when assistant responds */
  const persistTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => {
    if (messages.length === 0) return;
    const last = messages[messages.length - 1];
    if (last.role !== 'assistant') return;

    /* Skip if this render came from reconciling after a persist */
    if (reconcilingRef.current) {
      reconcilingRef.current = false;
      return;
    }

    const conv = activeConversationRef.current;
    if (!conv) return;

    clearTimeout(persistTimeoutRef.current);
    persistTimeoutRef.current = setTimeout(() => {
      conv.messages = messages;
      conv.metadata = { ...(conv.metadata || {}), status: 'complete' };
      api.updateConversation(conv.id, JSON.parse(JSON.stringify(conv)))
        .then((updated) => {
          activeConversationRef.current = updated;
          reconcilingRef.current = true;
          reconcileMessages(updated.messages);
        })
        .catch(() => {});
    }, 100);
  }, [messages, reconcileMessages]);

  /* Persist failure status */
  useEffect(() => {
    if (!error || !activeConversationId) return;
    const conv = activeConversationRef.current;
    if (!conv) return;
    conv.metadata = { ...(conv.metadata || {}), status: 'failed' };
    api.updateConversation(activeConversationId, JSON.parse(JSON.stringify(conv)))
      .catch(() => {});
  }, [error, activeConversationId]);

  useEffect(() => {
    if (activeConversationId) {
      setStorage(STORAGE_ACTIVE_CONV, activeConversationId);
    } else {
      removeStorage(STORAGE_ACTIVE_CONV);
    }
  }, [activeConversationId]);

  /* Scroll to bottom on new messages */
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleThemeToggle = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  }, [theme]);

  const handleSubmit = useCallback(async (text: string) => {
    composerClear();
    lastPromptRef.current = text;
    try {
      if (activeConversationId) {
        const payload = JSON.parse(JSON.stringify(activeConversationRef.current));
        payload.messages.push({ role: 'user', content: text, timestamp: new Date().toISOString() });
        payload.metadata = { ...(payload.metadata || {}), status: 'pending' };
        const updated = await api.updateConversation(activeConversationId, payload);
        activeConversationRef.current = updated;
      } else {
        const payload = {
          title: text.slice(0, 60),
          mode,
          messages: [{ role: 'user', content: text, timestamp: new Date().toISOString() }],
          metadata: { status: 'pending' },
        };
        const conv = await api.createConversation(payload);
        setActiveConversationId(conv.id);
        activeConversationRef.current = conv;
      }
    } catch {
      /* Continue anyway — the user's message will be in local state */
    }
    submit(text, mode, messages);
  }, [submit, mode, activeConversationId, composerClear, messages]);

  const handleNewChat = useCallback(() => {
    if (isLoading) return;
    const hasMessages = messages.length > 0;
    if (hasMessages) {
      setShowNewChatDialog(true);
    } else {
      conversationClear();
      composerClear();
    }
  }, [messages, isLoading, conversationClear, composerClear]);

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

  if (restoring) {
    return (
      <div className="app-container">
        <Header theme={theme} onThemeToggle={handleThemeToggle} onMenuToggle={() => setSidebarOpen(true)} showTitle={false} onNewChat={handleNewChat} />
      </div>
    );
  }

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
          scrollRef={scrollRef}
          messages={
            <>
              {messages.map((msg, i) => {
                if (msg.role === 'user') {
                  return <UserMessage key={i} content={msg.content} />;
                }
                if (msg.role === 'assistant') {
                  return (
                    <React.Fragment key={i}>
                      {msg.thinking && <ThinkingContainer content={msg.thinking} />}
                      {msg.image ? (
                        <ImageContainer imageUrl={msg.image} />
                      ) : (
                        <ResponseContainer content={msg.content} />
                      )}
                      {msg.content && <TTSButton text={msg.content} />}
                    </React.Fragment>
                  );
                }
                return null;
              })}
              {isLoading && (
                <div className="conversation-loading">
                  <LoadingDots label="Generating" />
                </div>
              )}
              {error && !isLoading && (
                <div className="response-container">
                  <em>Error: {error}</em>
                </div>
              )}
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
            if (conv.mode) setMode(conv.mode);
          }).catch(() => {});
        }}
        onDeleteConversation={async () => {
          try {
            const list = await api.listConversations();
            const sorted = list.sort(
              (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
            );
            if (sorted.length > 0) {
              const next = sorted[0];
              const conv = await api.getConversation(next.id);
              activeConversationRef.current = conv;
              setActiveConversationId(next.id);
              loadConversation(conv);
              if (conv.mode) setMode(conv.mode);
              return;
            }
          } catch {}
          setActiveConversationId(undefined);
          activeConversationRef.current = null;
          conversationClear();
          composerClear();
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
