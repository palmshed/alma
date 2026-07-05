import React, { useState, useEffect, useCallback } from 'react';
import type { ConversationEntry } from '../types';
import { api } from '../services/api';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat?: () => void;
  onSelectConversation?: (id: string) => void;
  onDeleteConversation?: (id: string) => void;
  activeConversationId?: string | null;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  activeConversationId,
}) => {
  const [conversations, setConversations] = useState<ConversationEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

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
      try {
        const conv = await api.getConversation(id);
        conv.title = trimmed;
        await api.updateConversation(id, conv);
        setConversations((prev) =>
          prev.map((c) => (c.id === id ? { ...c, title: trimmed } : c)),
        );
      } catch {
        // ignore rename failure
      }
      setEditingId(null);
    },
    [editTitle],
  );

  const handleDelete = useCallback(
    async (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      setConfirmDeleteId(id);
    },
    [],
  );

  const handleConfirmDelete = useCallback(async () => {
    if (!confirmDeleteId) return;
    try {
      await api.deleteConversation(confirmDeleteId);
      setConversations((prev) => prev.filter((c) => c.id !== confirmDeleteId));
    } catch {
      // ignore delete failure
    }
    if (confirmDeleteId === activeConversationId) {
      onDeleteConversation?.(confirmDeleteId);
    }
    setConfirmDeleteId(null);
  }, [confirmDeleteId, activeConversationId, onDeleteConversation]);

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
    <aside className={`sidebar${isOpen ? ' sidebar--open' : ''}`}>
      <div className="sidebar-header">
        <button
          className="btn btn--ghost sidebar-close"
          onClick={onClose}
          aria-label="Close menu"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
            <path d="M18 6 6 18"/>
            <path d="m6 6 12 12"/>
          </svg>
        </button>
      </div>
      <div className="sidebar-content">
        <div className="sidebar-product-label">Alma</div>
        <button
          className="btn btn--ghost sidebar-new-chat"
          onClick={() => { onNewChat?.(); onClose(); }}
          type="button"
        >
          + New conversation
        </button>

        <div className="sidebar-section-label">Chats</div>

        {loading && conversations.length === 0 && (
          <div className="sidebar-empty">Loading...</div>
        )}

        {!loading && conversations.length === 0 && (
          <div className="sidebar-empty">No conversations yet</div>
        )}

        <div className="sidebar-conversation-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`sidebar-conversation-item${conv.id === activeConversationId ? ' sidebar-conversation-item--active' : ''}`}
              onClick={() => handleSelect(conv.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSelect(conv.id); }}
            >
              <div className="sidebar-conversation-item-main">
                {editingId === conv.id ? (
                  <input
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
                  />
                ) : (
                  <>
                    <span className="sidebar-conversation-title">
                      {conv.title}
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
      </div>
      <div className="sidebar-footer">
        Built by<br />Palmshed
      </div>

      {confirmDeleteId && (
        <>
          <div className="sidebar-overlay-inline" onClick={handleCancelDelete} />
          <div className="sidebar-dialog" role="dialog" aria-modal="true">
            <p className="sidebar-dialog-title">Delete conversation?</p>
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
