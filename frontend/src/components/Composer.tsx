// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useRef, useEffect } from 'react';
import { Paperclip } from 'lucide-react';

interface ComposerProps {
  onSubmit: (text: string) => void;
  placeholder?: string;
  placeholderVisible?: boolean;
  disabled?: boolean;
  loading?: boolean;
  value: string;
  onChange: (value: string) => void;
  onAttach?: () => void;
  autoFocus?: boolean;
}

const Composer: React.FC<ComposerProps> = ({
  onSubmit,
  placeholder = 'Ask anything...',
  placeholderVisible = true,
  disabled,
  loading,
  value,
  onChange,
  onAttach,
  autoFocus,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const hasText = value.trim().length > 0;

  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (hasText && !disabled && !loading) onSubmit(value);
    }
  };

  return (
    <div className="composer">
      <div className="composer-input-row">
        {onAttach && (
          <button
            className="composer-btn composer-btn--attach"
            onClick={onAttach}
            disabled={disabled}
            type="button"
            aria-label="Attach file"
          >
            <Paperclip size={16} strokeWidth={1.7} />
          </button>
        )}

        <textarea
          ref={textareaRef}
          className={`composer-textarea${!placeholderVisible ? ' placeholder-hidden' : ''}`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          autoFocus={autoFocus}
        />

        <div className="composer-actions">
          <button
            className={`composer-btn composer-btn--send${hasText ? ' has-text' : ''}`}
            onClick={() => onSubmit(value)}
            disabled={!hasText || disabled || loading}
            type="submit"
            aria-label="Send message"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
              <path d="M12 19V5"/>
              <path d="m5 12 7-7 7 7"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Composer;
