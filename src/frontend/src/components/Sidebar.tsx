// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import type { ConversationEntry } from '../types';
import { api } from '../services/api';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat?: () => void;
  onSelectConversation?: (id: string) => void;
  onDeleteConversation?: (id: string) => void;
  activeConversationId?: string | null;
  onNavigate?: (page: string) => void;
}

function highlightText(text: string, query: string) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  activeConversationId,
  onNavigate,
}) => {
  const [conversations, setConversations] = useState<ConversationEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showLinks, setShowLinks] = useState(false);
  const deleteDialogRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const filteredConversations = useMemo(() => {
    if (!searchQuery) return conversations;
    const q = searchQuery.toLowerCase();
    return conversations.filter((c) => c.title.toLowerCase().includes(q));
  }, [conversations, searchQuery]);

  const showError = useCallback((msg: string) => {
    setError(msg);
    setTimeout(() => setError(null), 4000);
  }, []);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listConversations();
      list.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );
      setConversations(list);
    } catch {
      setConversations([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) fetchConversations();
  }, [isOpen, fetchConversations]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (editingId && renameInputRef.current) {
      renameInputRef.current.focus();
    }
  }, [editingId]);

  useEffect(() => {
    if (!confirmDeleteId || !deleteDialogRef.current) return;
    const dialog = deleteDialogRef.current;
    const focusable = dialog.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (first) setTimeout(() => first.focus(), 0);

    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setConfirmDeleteId(null);
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
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [confirmDeleteId]);

  const handleSelect = useCallback(
    (id: string) => {
      onSelectConversation?.(id);
      onClose();
    },
    [onSelectConversation, onClose],
  );

  const handleStartRename = useCallback(
    (e: React.MouseEvent, id: string, currentTitle: string) => {
      e.stopPropagation();
      setEditingId(id);
      setEditTitle(currentTitle);
    },
    [],
  );

  const handleFinishRename = useCallback(
    async (id: string) => {
      const trimmed = editTitle.trim();
      if (!trimmed) {
        setEditingId(null);
        return;
      }
      const prevConv = conversations.find((c) => c.id === id);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title: trimmed } : c)),
      );
      try {
        const conv = await api.getConversation(id);
        conv.title = trimmed;
        conv.title_is_manual = true;
        await api.updateConversation(id, conv);
      } catch {
        if (prevConv) {
          setConversations((prev) =>
            prev.map((c) => (c.id === id ? prevConv : c)),
          );
        }
        showError('Failed to rename conversation');
      }
      setEditingId(null);
    },
    [editTitle, conversations, showError],
  );

  const handleDelete = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      setConfirmDeleteId(id);
    },
    [],
  );

  const handleConfirmDelete = useCallback(async () => {
    if (!confirmDeleteId) return;
    const deletedConv = conversations.find((c) => c.id === confirmDeleteId);
    setConversations((prev) => prev.filter((c) => c.id !== confirmDeleteId));
    try {
      await api.deleteConversation(confirmDeleteId);
    } catch {
      if (deletedConv) {
        setConversations((prev) => {
          const restored = [...prev, deletedConv];
          restored.sort(
            (a, b) =>
              new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
          );
          return restored;
        });
      }
      showError('Failed to delete conversation');
      setConfirmDeleteId(null);
      return;
    }
    if (confirmDeleteId === activeConversationId) {
      onDeleteConversation?.(confirmDeleteId);
    }
    setConfirmDeleteId(null);
  }, [confirmDeleteId, activeConversationId, onDeleteConversation, conversations, showError]);

  const handleCancelDelete = useCallback(() => {
    setConfirmDeleteId(null);
  }, []);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  };

  return (
    <aside
      className={`sidebar${isOpen ? ' sidebar--open' : ''}`}
      role="complementary"
      aria-label="Conversation history"
      data-testid="sidebar"
    >
      <div className="sidebar-content">
        <div className="sidebar-header-row">
          <div className="sidebar-product-label">Alma</div>
          <button className="btn btn--ghost app-header-btn" onClick={onClose} aria-label="Close menu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <path d="M18 6 6 18"/>
              <path d="m6 6 12 12"/>
            </svg>
          </button>
        </div>
        <button
          className="btn btn--ghost sidebar-new-chat"
          onClick={() => { onNewChat?.(); onClose(); }}
          type="button"
        >
          + New conversation
        </button>

        <div className="sidebar-section-label">Chats</div>

        <div className="sidebar-search">
          <input
            ref={searchInputRef}
            className="sidebar-search-input"
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search conversations"
            data-testid="sidebar-search-input"
          />
          {searchQuery && (
            <button
              className="sidebar-search-clear"
              onClick={() => {
                setSearchQuery('');
                searchInputRef.current?.focus();
              }}
              aria-label="Clear search"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
                <path d="M18 6 6 18"/>
                <path d="m6 6 12 12"/>
              </svg>
            </button>
          )}
        </div>

        {error && (
          <div className="sidebar-error" role="alert">{error}</div>
        )}

        {filteredConversations.length > 0 && (
          <div className="sidebar-conversation-list" role="list">
          {filteredConversations.map((conv) => (
            <div
              key={conv.id}
              className={`sidebar-conversation-item${conv.id === activeConversationId ? ' sidebar-conversation-item--active' : ''}`}
              onClick={() => handleSelect(conv.id)}
              role="listitem"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(conv.id);
                }
              }}
              data-testid="sidebar-conversation-item"
            >
              <div className="sidebar-conversation-item-main">
                {editingId === conv.id ? (
                  <input
                    ref={renameInputRef}
                    className="sidebar-conversation-rename-input"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onBlur={() => handleFinishRename(conv.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleFinishRename(conv.id);
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                    onClick={(e) => e.stopPropagation()}
                    autoFocus
                    aria-label="Rename conversation"
                  />
                ) : (
                  <>
                    <span className="sidebar-conversation-title">
                      {highlightText(conv.title, searchQuery)}
                    </span>
                    <span className="sidebar-conversation-date">
                      {formatDate(conv.updated_at)}
                    </span>
                  </>
                )}
              </div>
              <div className="sidebar-conversation-actions">
                {editingId !== conv.id && (
                  <>
                    <button
                      className="btn btn--ghost sidebar-action-btn"
                      onClick={(e) => handleStartRename(e, conv.id, conv.title)}
                      aria-label="Rename conversation"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12">
                        <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                      </svg>
                    </button>
                    <button
                      className="btn btn--ghost sidebar-action-btn"
                      onClick={(e) => handleDelete(e, conv.id)}
                      aria-label="Delete conversation"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12">
                        <path d="M3 6h18"/>
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                      </svg>
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
        )}

        {!loading && conversations.length === 0 && !searchQuery && (
          <div className="sidebar-empty">No conversations yet</div>
        )}

        {!loading && conversations.length > 0 && searchQuery && filteredConversations.length === 0 && (
          <div className="sidebar-empty">No conversations found.</div>
        )}
      </div>
      <div className="sidebar-footer">
        <div className="sidebar-footer-top">
          <div className="sidebar-footer-brand">Built by Palmshed</div>
          <button className="btn btn--ghost sidebar-footer-toggle" onClick={() => setShowLinks(!showLinks)} aria-label="More links" type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <circle cx="5" cy="12" r="1.2" fill="currentColor" stroke="none"/>
              <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/>
              <circle cx="19" cy="12" r="1.2" fill="currentColor" stroke="none"/>
            </svg>
          </button>
        </div>
        {showLinks && (
          <div className="sidebar-footer-links">
            <button className="sidebar-footer-link" onClick={() => onNavigate?.('terms')} type="button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              Terms
            </button>
            <button className="sidebar-footer-link" onClick={() => onNavigate?.('privacy')} type="button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              Privacy
            </button>
            <button className="sidebar-footer-link" onClick={() => onNavigate?.('contact')} type="button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              Contact
            </button>
            <button className="sidebar-footer-link" onClick={() => onNavigate?.('help')} type="button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              Help
            </button>
            <a href="https://github.com/palmshed/alma/issues/new?template=bug_report.md" className="sidebar-footer-link" target="_blank" rel="noopener noreferrer">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="12" height="12"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              Report
            </a>
          </div>
        )}
      </div>

      {confirmDeleteId && (
        <>
          <div className="sidebar-overlay-inline" onClick={handleCancelDelete} />
          <div className="sidebar-dialog" ref={deleteDialogRef} role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title" data-testid="delete-dialog">
            <p id="delete-dialog-title" className="sidebar-dialog-title">Delete conversation?</p>
            <p className="sidebar-dialog-description">
              This cannot be undone.
            </p>
            <div className="sidebar-dialog-actions">
              <button className="btn sidebar-dialog-btn" onClick={handleCancelDelete} type="button">
                Cancel
              </button>
              <button className="btn btn--primary sidebar-dialog-btn sidebar-dialog-btn--delete" onClick={handleConfirmDelete} type="button">
                Delete
              </button>
            </div>
          </div>
        </>
      )}
    </aside>
  );
};

export default Sidebar;
