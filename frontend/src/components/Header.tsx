// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Sun, Moon, Keyboard, Info, Palette, Globe, ShieldCheck, Zap, ChevronDown } from 'lucide-react';
import { ACCENT_PRESETS } from '../utils';
import type { SearchSettings } from '../types';
import DropdownSelect from './DropdownSelect';

const SEARCH_PROVIDERS = [
  { value: 'auto', label: 'Auto (Best available)' },
  { value: 'tavily', label: 'Tavily' },
  { value: 'brave', label: 'Brave' },
  { value: 'exa', label: 'Exa' },
  { value: 'serpapi', label: 'SerpAPI' },
  { value: 'searxng', label: 'SearXNG' },
];

const DROPDOWN_MIN_HEIGHT = 200;

interface HeaderProps {
  theme?: 'dark' | 'light';
  onThemeToggle?: () => void;
  onMenuToggle?: () => void;
  showTitle?: boolean;
  onNewChat?: () => void;
  accentColor?: string;
  onAccentChange?: (color: string) => void;
  showSuggestions?: boolean;
  onShowSuggestionsChange?: (v: boolean) => void;
  onShowShortcuts?: () => void;
  onShowAbout?: () => void;
  searchSettings?: SearchSettings;
  onSearchSettingsChange?: (updates: Partial<SearchSettings>) => void;
}

const Header: React.FC<HeaderProps> = ({
  theme = 'dark',
  onThemeToggle,
  onMenuToggle,
  showTitle = false,
  onNewChat,
  accentColor = '#24d455',
  onAccentChange,
  showSuggestions = false,
  onShowSuggestionsChange,
  onShowShortcuts,
  onShowAbout,
  searchSettings,
  onSearchSettingsChange,
}) => {
  const [open, setOpen] = useState(false);
  const [showAccentPicker, setShowAccentPicker] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [menuPos, setMenuPos] = useState<{ top: number; right: number }>({ top: 0, right: 0 });

  const close = useCallback(() => { setOpen(false); setShowAccentPicker(false); setShowSearch(false); }, []);

  const calcMenuPos = useCallback(() => {
    if (!triggerRef.current || !dropdownRef.current) return;
    const btnRect = triggerRef.current.getBoundingClientRect();
    const ddHeight = dropdownRef.current.offsetHeight || DROPDOWN_MIN_HEIGHT;
    const gap = 6;
    let top = btnRect.bottom + gap;
    if (top + ddHeight > window.innerHeight - 8) {
      top = btnRect.top - ddHeight - gap;
    }
    if (top < 8) top = 8;
    setMenuPos({ top, right: window.innerWidth - btnRect.right });
  }, []);

  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => calcMenuPos());
    const handler = (e: MouseEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t)) return;
      if (dropdownRef.current?.contains(t)) return;
      if ((t as HTMLElement).closest?.('.dropdown-select-menu')) return;
      close();
    };
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, [open, close, calcMenuPos, showSearch, showSuggestions]);

  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => calcMenuPos());
  }, [open, showSearch, calcMenuPos]);

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

        <div ref={menuRef} className="settings-menu-wrapper">
          <button
            ref={triggerRef}
            className="btn btn--ghost app-header-btn"
            onClick={() => setOpen(v => !v)}
            aria-label="Settings"
            aria-expanded={open}
            type="button"
            data-testid="settings-menu-trigger"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>

          {createPortal(open && (
            <div
              ref={dropdownRef}
              className="settings-dropdown"
              data-testid="settings-dropdown"
              role="menu"
              aria-label="Settings"
              style={{ position: 'fixed', top: menuPos.top, right: menuPos.right, zIndex: 1000 }}
            >
              {/* Theme */}
              <button
                className="settings-dropdown-item"
                onClick={() => { onThemeToggle?.(); }}
                type="button"
                role="menuitem"
                data-testid="settings-theme-toggle"
              >
                <span className="settings-dropdown-icon">
                  {theme === 'dark' ? <Sun size={14} strokeWidth={1.7} /> : <Moon size={14} strokeWidth={1.7} />}
                </span>
                <span className="settings-dropdown-label">Theme</span>
                <span className="settings-dropdown-value">{theme === 'dark' ? 'Dark' : 'Light'}</span>
              </button>

              {/* Accent Color */}
              <div className="settings-dropdown-item settings-dropdown-item--accent">
                <button
                  className="settings-dropdown-item-btn"
                  onClick={() => setShowAccentPicker(v => !v)}
                  type="button"
                  role="menuitem"
                  data-testid="settings-accent-trigger"
                >
                  <span className="settings-dropdown-icon">
                    <Palette size={14} strokeWidth={1.7} />
                  </span>
                  <span className="settings-dropdown-label">Accent</span>
                  <span className="settings-dropdown-accent-dot" style={{ background: accentColor }} />
                </button>
                {showAccentPicker && (
                  <div className="accent-picker-popup accent-picker-popup--dropdown">
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

              {/* Search (expandable section) */}
              <div className="settings-dropdown-item settings-dropdown-item--expandable">
                <button
                  className="settings-dropdown-item-btn"
                  onClick={() => setShowSearch(v => !v)}
                  type="button"
                  role="menuitem"
                  aria-expanded={showSearch}
                  data-testid="settings-search-trigger"
                >
                  <span className="settings-dropdown-icon">
                    <Globe size={14} strokeWidth={1.7} />
                  </span>
                  <span className="settings-dropdown-label">Search</span>
                  <span className={`settings-dropdown-chevron${showSearch ? ' open' : ''}`}>
                    <ChevronDown size={12} strokeWidth={1.7} />
                  </span>
                </button>
              </div>

              {searchSettings && onSearchSettingsChange && (
                <div className={`settings-dropdown-sub${showSearch ? '' : ' settings-dropdown-sub--collapsed'}`}>
                  {/* Provider */}
                  <div className="settings-dropdown-sub-row">
                    <span className="settings-dropdown-sub-label">Provider</span>
                    <DropdownSelect
                      options={SEARCH_PROVIDERS}
                      value={searchSettings.provider}
                      onChange={(v) => onSearchSettingsChange({ provider: v })}
                    />
                  </div>

                  {/* Max Results */}
                  <div className="settings-dropdown-sub-row">
                    <span className="settings-dropdown-sub-label">Max results</span>
                    <input
                      type="range"
                      min="3"
                      max="10"
                      value={searchSettings.maxResults}
                      onChange={(e) => onSearchSettingsChange({ maxResults: parseInt(e.target.value, 10) })}
                      className="settings-dropdown-range"
                      data-testid="settings-search-max-results"
                      aria-valuetext={`${searchSettings.maxResults ?? 3} results`}
                      style={{
                        '--range-progress': `${(((searchSettings.maxResults ?? 3) - 3) / 7) * 100}%`,
                      } as React.CSSProperties}
                    />
                    <span className="settings-dropdown-sub-value">{searchSettings.maxResults}</span>
                  </div>

                  {/* Safe Search */}
                  <button
                    className="settings-dropdown-sub-toggle"
                    onClick={() => onSearchSettingsChange({ safeSearch: !searchSettings.safeSearch })}
                    type="button"
                    role="menuitem"
                    data-testid="settings-search-safe"
                  >
                    <span className="settings-dropdown-icon">
                      <ShieldCheck size={14} strokeWidth={1.7} />
                    </span>
                    <span className="settings-dropdown-label">Safe search</span>
                    <span className={`settings-dropdown-toggle${searchSettings.safeSearch ? ' on' : ''}`}>
                      <span className="settings-dropdown-toggle-track">
                        <span className="settings-dropdown-toggle-thumb" />
                      </span>
                    </span>
                  </button>

                  {/* Auto Search */}
                  <button
                    className="settings-dropdown-sub-toggle"
                    onClick={() => onSearchSettingsChange({ autoSearch: !searchSettings.autoSearch })}
                    type="button"
                    role="menuitem"
                    data-testid="settings-search-auto"
                  >
                    <span className="settings-dropdown-icon">
                      <Zap size={14} strokeWidth={1.7} />
                    </span>
                    <span className="settings-dropdown-label">Auto search</span>
                    <span className={`settings-dropdown-toggle${searchSettings.autoSearch ? ' on' : ''}`}>
                      <span className="settings-dropdown-toggle-track">
                        <span className="settings-dropdown-toggle-thumb" />
                      </span>
                    </span>
                  </button>

                  {/* Landing Suggestions */}
                  <button
                    className="settings-dropdown-sub-toggle"
                    onClick={() => onShowSuggestionsChange?.(!showSuggestions)}
                    type="button"
                    role="menuitem"
                    data-testid="settings-suggestions-toggle"
                  >
                    <span className="settings-dropdown-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
                        <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                      </svg>
                    </span>
                    <span className="settings-dropdown-label">Landing suggestions</span>
                    <span className={`settings-dropdown-toggle${showSuggestions ? ' on' : ''}`}>
                      <span className="settings-dropdown-toggle-track">
                        <span className="settings-dropdown-toggle-thumb" />
                      </span>
                    </span>
                  </button>
                </div>
              )}

              {/* Keyboard Shortcuts */}
              <button
                className="settings-dropdown-item"
                onClick={() => { close(); onShowShortcuts?.(); }}
                type="button"
                role="menuitem"
                data-testid="settings-shortcuts"
              >
                <span className="settings-dropdown-icon">
                  <Keyboard size={14} strokeWidth={1.7} />
                </span>
                <span className="settings-dropdown-label">Keyboard shortcuts</span>
              </button>

              {/* About */}
              <button
                className="settings-dropdown-item"
                onClick={() => { close(); onShowAbout?.(); }}
                type="button"
                role="menuitem"
                data-testid="settings-about"
              >
                <span className="settings-dropdown-icon">
                  <Info size={14} strokeWidth={1.7} />
                </span>
                <span className="settings-dropdown-label">About</span>
              </button>
            </div>
          ), document.body)}
        </div>
      </div>
    </header>
  );
};

export default Header;
