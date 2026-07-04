import React, { useRef, useEffect } from 'react';
import { Paperclip, Send } from 'lucide-react';

interface ComposerProps {
  onSubmit: (text: string) => void;
  placeholder?: string;
  disabled?: boolean;
  loading?: boolean;
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  onAttach?: () => void;
  autoFocus?: boolean;
}

const Composer: React.FC<ComposerProps> = ({
  onSubmit,
  placeholder = 'Ask anything...',
  disabled,
  loading,
  value,
  onChange,
  onClear,
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
          className="composer-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          autoFocus={autoFocus}
        />

        <div className="composer-actions">
          {hasText && onClear && (
            <button
              className="composer-btn"
              onClick={onClear}
              disabled={disabled}
              type="button"
              aria-label="Clear input"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.7}
                strokeLinecap="round"
                strokeLinejoin="round"
                width={16}
                height={16}
              >
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </button>
          )}

          <button
            className={`composer-btn composer-btn--send${hasText ? ' has-text' : ''}`}
            onClick={() => onSubmit(value)}
            disabled={!hasText || disabled || loading}
            type="submit"
            aria-label="Send message"
          >
            {loading ? (
              <span className="composer-loading-dots">
                <span /><span /><span />
              </span>
            ) : (
              <Send size={18} strokeWidth={1.7} />
            )}
          </button>
        </div>
      </div>

      {loading && (
        <div className="composer-loading-bar" />
      )}
    </div>
  );
};

export default Composer;
