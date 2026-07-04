import React from 'react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat?: () => void;
}

const sections = [
  { label: 'Chats' },
  { label: 'Projects' },
  { label: 'Knowledge' },
  { label: 'Settings' },
];

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, onNewChat }) => (
  <aside className={`sidebar${isOpen ? ' sidebar--open' : ''}`}>
    <div className="sidebar-header">
      <button className="btn btn--ghost sidebar-close" onClick={onClose} aria-label="Close menu">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
          <path d="M18 6 6 18"/>
          <path d="m6 6 12 12"/>
        </svg>
      </button>
    </div>
    <div className="sidebar-content">
      <div className="sidebar-product-label">Alma</div>
      <button className="btn btn--ghost sidebar-new-chat" onClick={() => { onNewChat?.(); onClose(); }} type="button">
        + New conversation
      </button>
      {sections.map((s) => (
        <div key={s.label}>
          <div className="sidebar-section-label">{s.label}</div>
        </div>
      ))}
    </div>
    <div className="sidebar-footer">Built by<br />Palmshed</div>
  </aside>
);

export default Sidebar;
