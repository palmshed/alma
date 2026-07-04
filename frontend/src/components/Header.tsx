import React from 'react';
import { Sun, Moon, Menu } from 'lucide-react';

interface HeaderProps {
  theme?: 'dark' | 'light';
  onThemeToggle?: () => void;
  onMenuToggle?: () => void;
  showTitle?: boolean;
  onNewChat?: () => void;
}

const Header: React.FC<HeaderProps> = ({
  theme = 'dark',
  onThemeToggle,
  onMenuToggle,
  showTitle = false,
  onNewChat,
}) => (
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
      {onThemeToggle && (
        <button
          className="btn btn--ghost app-header-btn"
          onClick={onThemeToggle}
          aria-label="Toggle theme"
          type="button"
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
          <Menu size={14} strokeWidth={1.7} />
        </button>
      )}
    </div>
  </header>
);

export default Header;
