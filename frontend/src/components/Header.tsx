// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useState, useRef, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { ACCENT_PRESETS } from '../utils';

interface HeaderProps {
  theme?: 'dark' | 'light';
  onThemeToggle?: () => void;
  onMenuToggle?: () => void;
  showTitle?: boolean;
  onNewChat?: () => void;
  accentColor?: string;
  onAccentChange?: (color: string) => void;
}

const Header: React.FC<HeaderProps> = ({
  theme = 'dark',
  onThemeToggle,
  onMenuToggle,
  showTitle = false,
  onNewChat,
  accentColor = '#24d455',
  onAccentChange,
}) => {
  const [showAccentPicker, setShowAccentPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showAccentPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowAccentPicker(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showAccentPicker]);

  return (
    <header className="app-header">
      <div className="app-header-left">
        <button className="btn btn--ghost app-header-logo-btn" onClick={onNewChat} type="button" aria-label="Start a new conversation">
          <svg
            className="app-header-logo"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.7}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M13 8c0-2.76-2.46-5-5.5-5S2 5.24 2 8h2l1-1 1 1h4" />
            <path d="M13 7.14A5.82 5.82 0 0 1 16.5 6c3.04 0 5.5 2.24 5.5 5h-3l-1-1-1 1h-3" />
            <path d="M5.89 9.71c-2.15 2.15-2.3 5.47-.35 7.43l4.24-4.25.7-.7.71-.71 2.12-2.12c-1.95-1.96-5.27-1.8-7.42.35" />
            <path d="M11 15.5c.5 2.5-.17 4.5-1 6.5h4c2-5.5-.5-12-1-14" />
          </svg>
          {showTitle && <span className="app-header-title">Alma</span>}
        </button>
      </div>

      <div className="app-header-right">
        <div ref={pickerRef} style={{ position: 'relative', display: 'flex' }}>
          <button
            className="accent-picker-btn btn btn--ghost app-header-btn"
            onClick={() => setShowAccentPicker(v => !v)}
            aria-label="Change accent color"
            type="button"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <circle cx="13.5" cy="6.5" r="1.5" fill="#24d455" stroke="none"/>
              <circle cx="17.5" cy="10.5" r="1.5" fill="#3b82f6" stroke="none"/>
              <circle cx="8.5" cy="7.5" r="1.5" fill="#f59e0b" stroke="none"/>
              <circle cx="6.5" cy="12.5" r="1.5" fill="#ec4899" stroke="none"/>
              <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.5-.67 1.5-1.5 0-.4-.13-.73-.4-1-.27-.27-.4-.6-.4-1 0-.93.67-1.5 1.5-1.5H16c3.31 0 6-2.69 6-6 0-5.52-4.5-10-10-10z"/>
            </svg>
          </button>
          {showAccentPicker && (
            <div className="accent-picker-popup">
              {ACCENT_PRESETS.map((p) => (
                <button
                  key={p.color}
                  className={`accent-swatch${accentColor === p.color ? ' active' : ''}`}
                  style={{ background: p.color }}
                  onClick={() => { onAccentChange?.(p.color); setShowAccentPicker(false); }}
                  aria-label={`Set accent to ${p.color}`}
                  type="button"
                />
              ))}
            </div>
          )}
        </div>
        {onThemeToggle && (
          <button
            className="btn btn--ghost app-header-btn"
            onClick={onThemeToggle}
            aria-label="Toggle theme"
            type="button"
            data-testid="theme-toggle"
          >
            {theme === 'dark' ? (
              <Sun size={14} strokeWidth={1.7} />
            ) : (
              <Moon size={14} strokeWidth={1.7} />
            )}
          </button>
        )}
        {onMenuToggle && (
          <button
            className="btn btn--ghost app-header-btn"
            onClick={onMenuToggle}
            aria-label="Open menu"
            type="button"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <circle cx="12" cy="5" r="1.2" fill="currentColor" stroke="none"/>
              <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/>
              <circle cx="12" cy="19" r="1.2" fill="currentColor" stroke="none"/>
            </svg>
          </button>
        )}
      </div>
    </header>
  );
};

export default Header;
