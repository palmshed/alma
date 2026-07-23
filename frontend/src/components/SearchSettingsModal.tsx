// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React from 'react';
import { X, Sliders, ShieldCheck, Zap } from 'lucide-react';
import type { SearchSettings } from '../types';

interface SearchSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: SearchSettings;
  onUpdate: (settings: Partial<SearchSettings>) => void;
}

const PROVIDERS = [
  { value: 'auto', label: 'Auto (Best available)' },
  { value: 'tavily', label: 'Tavily Search' },
  { value: 'brave', label: 'Brave Search' },
  { value: 'exa', label: 'Exa' },
  { value: 'serpapi', label: 'SerpAPI (Google)' },
  { value: 'searxng', label: 'SearXNG (Self-hosted)' },
];

const SearchSettingsModal: React.FC<SearchSettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onUpdate,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} data-testid="search-settings-overlay">
      <div className="modal-content search-settings-modal" onClick={(e) => e.stopPropagation()} data-testid="search-settings-modal">
        <div className="modal-header">
          <div className="modal-header-title">
            <Sliders size={18} />
            <span>Search Settings</span>
          </div>
          <button className="btn btn--ghost modal-close-btn" onClick={onClose} aria-label="Close settings">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body search-settings-body">
          {/* Provider Select */}
          <div className="setting-row">
            <label className="setting-label">
              <span className="setting-name">Search Provider</span>
              <span className="setting-desc">Choose web search API provider</span>
            </label>
            <select
              className="setting-select"
              value={settings.provider}
              onChange={(e) => onUpdate({ provider: e.target.value })}
              data-testid="search-provider-select"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {/* Max Results */}
          <div className="setting-row">
            <label className="setting-label">
              <span className="setting-name">Maximum Results</span>
              <span className="setting-desc">Number of sources to retrieve ({settings.maxResults})</span>
            </label>
            <input
              type="range"
              min="3"
              max="10"
              value={settings.maxResults}
              onChange={(e) => onUpdate({ maxResults: parseInt(e.target.value, 10) })}
              className="setting-range"
              data-testid="search-max-results"
            />
          </div>

          {/* Safe Search */}
          <div className="setting-row toggle-row">
            <label className="setting-label">
              <div className="setting-with-icon">
                <ShieldCheck size={16} />
                <span className="setting-name">Safe Search</span>
              </div>
              <span className="setting-desc">Filter explicit content from web results</span>
            </label>
            <input
              type="checkbox"
              className="setting-checkbox"
              checked={settings.safeSearch}
              onChange={(e) => onUpdate({ safeSearch: e.target.checked })}
              data-testid="search-safe-toggle"
            />
          </div>

          {/* Automatic Search */}
          <div className="setting-row toggle-row">
            <label className="setting-label">
              <div className="setting-with-icon">
                <Zap size={16} />
                <span className="setting-name">Automatic Search</span>
              </div>
              <span className="setting-desc">Automatically trigger search when intent is detected in Auto mode</span>
            </label>
            <input
              type="checkbox"
              className="setting-checkbox"
              checked={settings.autoSearch}
              onChange={(e) => onUpdate({ autoSearch: e.target.checked })}
              data-testid="search-auto-toggle"
            />
          </div>

          {/* Landing Suggestions */}
          <div className="setting-row toggle-row">
            <label className="setting-label">
              <div className="setting-with-icon">
                <Zap size={16} />
                <span className="setting-name">Landing Suggestions</span>
              </div>
              <span className="setting-desc">Show suggestion chips on the landing page</span>
            </label>
            <input
              type="checkbox"
              className="setting-checkbox"
              checked={settings.showSuggestions}
              onChange={(e) => onUpdate({ showSuggestions: e.target.checked })}
              data-testid="search-suggestions-toggle"
            />
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn--primary" onClick={onClose} data-testid="search-settings-done">
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default SearchSettingsModal;
