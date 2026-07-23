import React, { useState, useCallback, useEffect, useRef } from 'react';
import Header from './components/Header';
import Composer from './components/Composer';
import ModeMenu from './components/ModeMenu';
import ModelMenu from './components/ModelMenu';
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
import FooterPage from './pages/FooterPage';
import SourceCards from './components/SourceCards';
import SearchProgress from './components/SearchProgress';
import { useComposer } from './hooks/useComposer';
import { useConversation } from './hooks/useConversation';
import { MODES, MODELS, SUGGESTIONS, ACCENT_PRESETS, playNavSound, getModelLabel, resolveModel } from './utils';
import { api } from './services/api';
import { AttachmentData, ConversationData, ModelAvailability, SearchSettings } from './types';

const PLACEHOLDERS = [
  'Ask anything...',
  'Debug a bug...',
  'Send a message...',
  'Fix an issue...',
  'Explore a topic...',
];

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
  const submitKeyLabel = typeof navigator !== 'undefined' && /Mac|iPhone|iPad|iPod/.test(navigator.userAgent)
    ? 'Return'
    : 'Enter';
  const [mode, setMode] = useState('search');
  const [selectedModel, setSelectedModel] = useState(MODELS[0].value);
  const [searchSettings, setSearchSettings] = useState<SearchSettings>(() => {
    try {
      const stored = localStorage.getItem('alma_search_settings');
      const defaults = { provider: 'auto', maxResults: 5, safeSearch: true, autoSearch: true, showSuggestions: false };
      return stored ? { ...defaults, ...JSON.parse(stored) } : defaults;
    } catch {
      return { provider: 'auto', maxResults: 5, safeSearch: true, autoSearch: true, showSuggestions: false };
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('alma_search_settings', JSON.stringify(searchSettings));
    } catch { /* noop */ }
  }, [searchSettings]);
  const initialStored = getStorage(STORAGE_ACTIVE_CONV);
  const [restoring, setRestoring] = useState(!!initialStored);
  const [placeholderIndex, setPlaceholderIndex] = useState(Math.floor(Math.random() * PLACEHOLDERS.length));
  const [placeholderVisible, setPlaceholderVisible] = useState(true);
  const { input, setInput, clear: composerClear } = useComposer();
  const [modelAvailability, setModelAvailability] = useState<Record<string, ModelAvailability>>({});
  const {
    messages, isLoading, conversationStarted, error,
    submit, clear: conversationClear, loadConversation, getMessages,
  } = useConversation({
    autoMode: selectedModel === 'auto',
    getFallbackModel: (failedModel) => {
      const next = resolveModel(selectedModel, modelAvailability);
      return next !== failedModel ? next : undefined;
    },
    onQuotaError: (model, retryAfter) => {
      if (retryAfter) {
        setModelAvailability(prev => ({
          ...prev,
          [model]: { state: 'cooling-down', availableAt: Date.now() + retryAfter * 1000 },
        }));
        setTimeout(() => {
          setModelAvailability(prev => ({ ...prev, [model]: { state: 'ready' } }));
        }, retryAfter * 1000);
      } else {
        setModelAvailability(prev => ({
          ...prev,
          [model]: { state: 'unavailable' },
        }));
      }
    },
  });
  const [theme, setTheme] = useState<'dark' | 'light'>(
    (document.documentElement.getAttribute('data-theme') as 'dark' | 'light') || 'dark'
  );
  const [accentColor, setAccentColor] = useState(() => {
    try { return localStorage.getItem('accent') || '#24d455'; } catch { return '#24d455'; }
  });
  const [pendingAttachments, setPendingAttachments] = useState<AttachmentData[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
  const [currentPage, setCurrentPage] = useState<string | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const lastPromptRef = useRef<string>('');
  const activeConversationRef = useRef<ConversationData | null>(null);
  const restoredRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);

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
      if (conv.model) setSelectedModel(conv.model);
    }).catch(() => {
      if (!cancelled) removeStorage(STORAGE_ACTIVE_CONV);
    }).finally(() => {
      if (!cancelled) setRestoring(false);
    });
    return () => { cancelled = true; };
  }, [loadConversation]);

  /* Play sound on mode change */
  const prevModeRef = useRef(mode);
  useEffect(() => {
    if (prevModeRef.current !== mode) {
      prevModeRef.current = mode;
      playNavSound();
    }
  }, [mode]);

  /* Rotate placeholder every 8s with fade */
  useEffect(() => {
    const id = setInterval(() => {
      setPlaceholderVisible(false);
      setTimeout(() => {
        setPlaceholderIndex(i => (i + 1) % PLACEHOLDERS.length);
        setPlaceholderVisible(true);
      }, 800);
    }, 8000);
    return () => clearInterval(id);
  }, []);

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

  /* Blur composer on submit so it doesn't stay selected during generation */
  useEffect(() => {
    if (isLoading && document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
  }, [isLoading]);

  useEffect(() => {
    const preset = ACCENT_PRESETS.find(p => p.color === accentColor) || ACCENT_PRESETS[0];
    document.documentElement.style.setProperty('--accent', preset.color);
    document.documentElement.style.setProperty('--accent-hover', preset.hover);
    try { localStorage.setItem('accent', accentColor); } catch {}
  }, [accentColor]);

  const handleNavigate = useCallback((page: string) => {
    setSidebarOpen(false);
    setCurrentPage(page);
  }, []);

  const handleClosePage = useCallback(() => {
    setCurrentPage(null);
  }, []);

  const handleThemeToggle = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  }, [theme]);

  const handleAttach = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const uploaded: AttachmentData[] = [];
    for (const file of Array.from(files)) {
      try {
        const att = await api.uploadAttachment(file);
        uploaded.push(att);
      } catch (err) {
        console.error('Upload failed:', file.name, err);
      }
    }
    setPendingAttachments(prev => [...prev, ...uploaded]);
    e.target.value = '';
  }, []);

  const handleRemoveAttachment = useCallback(async (att: AttachmentData) => {
    setPendingAttachments(prev => prev.filter(a => a.id !== att.id));
    try {
      await api.deleteAttachment(att.id);
    } catch {
      /* ignore — server-side cleanup is best-effort */
    }
  }, []);

  const handleSubmit = useCallback((text: string) => {
    const atts = pendingAttachments.length > 0 ? pendingAttachments : undefined;
    composerClear();
    setPendingAttachments([]);
    lastPromptRef.current = text;
    const actualModel = resolveModel(selectedModel, modelAvailability);
    const userMessage = {
      role: 'user' as const,
      content: text,
      timestamp: new Date().toISOString(),
      ...(atts ? { attachments: atts.map(a => ({ id: a.id, filename: a.filename, mime_type: a.mime_type, size: a.size })) } : {}),
    };

    /* Update the interface before waiting for Vercel to persist the conversation. */
    const currentMsgs = getMessages();
    const generation = submit(text, mode, currentMsgs, atts, actualModel);
    const existingConversation = activeConversationRef.current;
    const savedConversation = existingConversation
      ? Promise.resolve({
        ...existingConversation,
        messages: [...existingConversation.messages, userMessage],
        metadata: { ...(existingConversation.metadata || {}), status: 'pending' },
      })
      : api.createConversation({
        title: text.slice(0, 60),
        mode,
        model: actualModel,
        messages: [userMessage],
        metadata: { status: 'pending' },
      }).then((conversation) => {
        setActiveConversationId(conversation.id);
        return conversation;
      });

    void Promise.all([generation, savedConversation])
      .then(([succeeded, conversation]) => {
        const completedConversation = {
          ...conversation,
          messages: getMessages(),
          metadata: { ...(conversation.metadata || {}), status: succeeded ? 'complete' : 'failed' },
        };
        activeConversationRef.current = completedConversation;
        return api.updateConversation(conversation.id, JSON.parse(JSON.stringify(completedConversation)));
      })
      .then((updated) => {
        activeConversationRef.current = updated;
      })
      .catch(() => {
        /* The visible conversation remains available if background persistence fails. */
      });
  }, [submit, mode, selectedModel, composerClear, messages, pendingAttachments, modelAvailability, getMessages]);

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
    const shown = getStorage('alma_disclaimer_shown');
    if (!shown) {
      setShowDisclaimer(true);
      setStorage('alma_disclaimer_shown', '1');
    }
  }, []);

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
  const placeholder = PLACEHOLDERS[placeholderIndex];

  const composer = (
    <Composer
      value={input}
      onChange={setInput}
      onSubmit={handleSubmit}
      onAttach={handleAttach}
      placeholder={placeholder}
      placeholderVisible={placeholderVisible}
      loading={isLoading}
      autoFocus
    />
  );

  if (restoring) {
    return (
      <div className="app-container">
        <Header
          theme={theme}
          onThemeToggle={handleThemeToggle}
          onMenuToggle={() => setSidebarOpen(true)}
          showTitle={false}
          onNewChat={handleNewChat}
          accentColor={accentColor}
          onAccentChange={setAccentColor}
          showSuggestions={searchSettings.showSuggestions}
          onShowSuggestionsChange={(v) => setSearchSettings(prev => ({ ...prev, showSuggestions: v }))}
          onShowShortcuts={() => setShowShortcuts(true)}
          onShowAbout={() => setShowDisclaimer(true)}
          searchSettings={searchSettings}
          onSearchSettingsChange={(u) => setSearchSettings(prev => ({ ...prev, ...u }))}
        />
      </div>
    );
  }

  if (currentPage) {
    return <FooterPage page={currentPage} onClose={handleClosePage} />;
  }

  return (
    <div className="app-container">
      <Header
        theme={theme}
        onThemeToggle={handleThemeToggle}
        onMenuToggle={() => setSidebarOpen(true)}
        showTitle={conversationStarted}
        onNewChat={handleNewChat}
        accentColor={accentColor}
        onAccentChange={setAccentColor}
        showSuggestions={searchSettings.showSuggestions}
        onShowSuggestionsChange={(v) => setSearchSettings(prev => ({ ...prev, showSuggestions: v }))}
        onShowShortcuts={() => setShowShortcuts(true)}
        onShowAbout={() => setShowDisclaimer(true)}
        searchSettings={searchSettings}
        onSearchSettingsChange={(u) => setSearchSettings(prev => ({ ...prev, ...u }))}
      />

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        multiple
        accept="image/png,image/jpeg,image/webp,image/gif,application/pdf,text/plain,text/markdown"
        style={{ display: 'none' }}
      />

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
          composer={
            <div className="composer-wrapper">
              {composer}
              {pendingAttachments.length > 0 && (
                <div className="pending-attachments">
                  {pendingAttachments.map(a => (
                    <span key={a.id} className="attachment-chip">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width={12} height={12}>
                        <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                      </svg>
                      {a.filename}
                      <button
                        className="attachment-chip-remove"
                        onClick={() => handleRemoveAttachment(a)}
                        type="button"
                        aria-label={`Remove ${a.filename}`}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width={10} height={10}>
                          <path d="M18 6 6 18" /><path d="m6 6 12 12" />
                        </svg>
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          }
          suggestions={
            searchSettings.showSuggestions && !input && suggestions.length > 0 ? (
              <div className="landing-suggestions">
                {suggestions.map((s) => (
                  <Chip key={s} label={s} onClick={() => { setInput(s); document.querySelector<HTMLTextAreaElement>('.composer-textarea')?.focus(); }} />
                ))}
              </div>
            ) : undefined
          }
          modes={
            <div className={`composer-toolbar${MODELS.length <= 1 ? ' composer-toolbar--no-model' : ''}${MODES.length <= 1 ? ' composer-toolbar--no-mode' : ''}`}>
              {MODELS.length > 1 && (
                <ModelMenu
                  options={MODELS}
                  value={selectedModel}
                  onChange={setSelectedModel}
                  availability={modelAvailability}
                />
              )}
              {MODES.length > 1 && (
                <ModeMenu
                  options={MODES}
                  value={mode}
                  onChange={setMode}
                />
              )}
            </div>
          }
        />
      ) : (
        <ConversationLayout
          scrollRef={scrollRef}
          messages={
            <>
              {messages.map((msg, i) => {
                if (msg.role === 'user') {
                  return (
                    <div key={i}>
                      <UserMessage content={msg.content} />
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="message-attachments">
                          {msg.attachments.map((att: Record<string, unknown>) => {
                            const isImage = typeof att.mime_type === 'string' && att.mime_type.startsWith('image/');
                            const attId = typeof att.id === 'string' ? att.id : '';
                            const filename = typeof att.filename === 'string' ? att.filename : 'file';
                            const mime = typeof att.mime_type === 'string' ? att.mime_type : '';
                            if (isImage) {
                              return (
                                <a key={attId} href={`/api/attachments/${attId}`} target="_blank" rel="noopener noreferrer" className="attachment-image-link">
                                  <img src={`/api/attachments/${attId}`} alt={filename} className="attachment-image" loading="lazy" />
                                </a>
                              );
                            }
                            return (
                              <a key={attId} href={`/api/attachments/${attId}`} target="_blank" rel="noopener noreferrer" className="attachment-chip" download={filename}>
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width={12} height={12}>
                                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                                </svg>
                                {filename}
                              </a>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                }
                if (msg.role === 'assistant') {
                  return (
                    <React.Fragment key={i}>
                      {msg.model && (
                        <div className={`response-model${msg.metadata?.autoFallback ? ' response-model--fallback' : ''}`}>
                          <>{getModelLabel(msg.model)}{msg.metadata?.autoFallback && <span className="response-model-badge"> Auto fallback</span>}</>
                        </div>
                      )}
                      {msg.thinking && <ThinkingContainer content={msg.thinking} durationSec={msg.thinking_duration_sec} />}
                      {msg.image ? (
                        <ImageContainer imageUrl={msg.image} />
                      ) : (
                        <ResponseContainer content={msg.content}>
                          <TTSButton text={msg.content} />
                        </ResponseContainer>
                      )}
                      {msg.sources && msg.sources.length > 0 && (
                        <SourceCards sources={msg.sources} />
                      )}
                    </React.Fragment>
                  );
                }
                return null;
              })}
              {isLoading && (
                <div className="conversation-loading">
                  {['search', 'auto', 'code', 'web'].includes(mode) ? (
                    <SearchProgress />
                  ) : (
                    <LoadingDots label="Generating" />
                  )}
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
              <div className="composer-wrapper">
                {composer}
                {pendingAttachments.length > 0 && (
                  <div className="pending-attachments">
                    {pendingAttachments.map(a => (
                      <span key={a.id} className="attachment-chip">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width={12} height={12}>
                          <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                        </svg>
                        {a.filename}
                        <button
                          className="attachment-chip-remove"
                          onClick={() => handleRemoveAttachment(a)}
                          type="button"
                          aria-label={`Remove ${a.filename}`}
                        >
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width={10} height={10}>
                            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
                          </svg>
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className={`composer-toolbar${MODELS.length <= 1 ? ' composer-toolbar--no-model' : ''}${MODES.length <= 1 ? ' composer-toolbar--no-mode' : ''}`}>
                {MODELS.length > 1 && (
                  <ModelMenu
                    options={MODELS}
                    value={selectedModel}
                    onChange={setSelectedModel}
                    availability={modelAvailability}
                  />
                )}
                {MODES.length > 1 && (
                  <ModeMenu
                    options={MODES}
                    value={mode}
                    onChange={setMode}
                  />
                )}
              </div>
            </>
          }
        />
      )}

      <div className={`sidebar-overlay${sidebarOpen ? ' sidebar-overlay--active' : ''}`} onClick={() => setSidebarOpen(false)} />
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
            if (conv.model) setSelectedModel(conv.model);
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
        onNavigate={handleNavigate}
      />

      {showDisclaimer && (
        <>
          <div className="dialog-overlay" onClick={() => setShowDisclaimer(false)} />
          <div className="dialog disclaimer-dialog" role="dialog" aria-modal="true">
            <p className="dialog-title">About Alma</p>
            <p className="dialog-description">
              Alma uses AI (large language models) to generate responses.
              The AI can make mistakes. Always verify important information.
            </p>
            <div className="dialog-actions">
              <button className="btn btn--primary dialog-btn dialog-btn--confirm" onClick={() => setShowDisclaimer(false)} type="button">Got it</button>
            </div>
          </div>
        </>
      )}

      {showShortcuts && (
        <>
          <div className="dialog-overlay" onClick={() => setShowShortcuts(false)} />
          <div className="dialog" role="dialog" aria-modal="true">
            <p className="dialog-title">Keyboard Shortcuts</p>
            <div className="dialog-description">
              <table className="shortcuts-table">
                <tbody>
                  <tr><td>New conversation</td><td><kbd>Ctrl</kbd>+<kbd>N</kbd></td></tr>
                  <tr><td>Submit message</td><td><kbd>{submitKeyLabel}</kbd></td></tr>
                  <tr><td>Close sidebar</td><td><kbd>Esc</kbd></td></tr>
                </tbody>
              </table>
            </div>
            <div className="dialog-actions">
              <button className="btn btn--primary dialog-btn dialog-btn--confirm" onClick={() => setShowShortcuts(false)} type="button">Close</button>
            </div>
          </div>
        </>
      )}

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
