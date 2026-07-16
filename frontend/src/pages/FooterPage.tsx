// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useEffect } from 'react';

interface FooterPageProps {
  page: string;
  onClose: () => void;
}

const CONTENT: Record<string, { title: string; body: React.ReactNode }> = {
  terms: {
    title: 'Terms of Use',
    body: (
      <>
        <p>These Terms of Use govern your use of the Alma AI platform provided by Palmshed.</p>
        <h2>Acceptance of Terms</h2>
        <p>By accessing or using Alma, you agree to be bound by these Terms. If you do not agree, do not use the service.</p>
        <h2>Use of Service</h2>
        <p>You may use Alma for lawful purposes only. You agree not to misuse the service or attempt to access it in unauthorized ways.</p>
        <h2>Intellectual Property</h2>
        <p>The Alma platform, its design, and underlying technology are owned by Palmshed. Content you generate remains yours.</p>
        <h2>Limitation of Liability</h2>
        <p>Alma is provided "as is" without warranties of any kind. Palmshed is not liable for damages arising from your use of the service.</p>
      </>
    ),
  },
  privacy: {
    title: 'Privacy Policy',
    body: (
      <>
        <p>Your privacy is important to us. This policy explains how Palmshed collects, uses, and protects your information.</p>
        <h2>Information We Collect</h2>
        <p>We collect information you provide when using Alma, including conversation content and account details if you register. We also collect usage data to improve the service.</p>
        <h2>How We Use Information</h2>
        <p>Your data is used to provide, maintain, and improve Alma. Conversations may be used to train models only with your consent.</p>
        <h2>Data Storage</h2>
        <p>Conversations are stored locally and associated with a device identifier. You can delete conversations at any time.</p>
        <h2>Third Parties</h2>
        <p>We do not sell your data. We may share anonymized data with service providers who help operate the platform.</p>
      </>
    ),
  },
  contact: {
    title: 'Contact Us',
    body: (
      <>
        <p>Questions, feedback, or need help? Open a GitHub issue and we'll get back to you.</p>
        <p>
          <a href="https://github.com/palmshed/alma/issues/new?template=contact.md" className="btn btn--secondary" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            Open an issue
          </a>
        </p>
        <p style={{ marginTop: '2rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Publisher: Palmshed</p>
      </>
    ),
  },
  help: {
    title: 'Help',
    body: (
      <>
        <h2>Getting Started</h2>
        <p>Alma is an AI chat assistant. Type a message in the composer and press Enter or Send to start a conversation.</p>
        <h2>Conversations</h2>
        <p>Your conversations are saved automatically. You can create new conversations, rename them, and delete them from the sidebar. Search is available to find past conversations.</p>
        <h2>Tips</h2>
        <ul>
          <li>Be specific in your questions for better answers.</li>
          <li>Use the sidebar to organize your conversations.</li>
          <li>Conversations are stored locally and tied to your device.</li>
        </ul>
        <h2>Still Need Help?</h2>
      </>
    ),
  },
};

const FooterPage: React.FC<FooterPageProps> = ({ page, onClose }) => {
  const data = CONTENT[page];

  useEffect(() => {
    const prev = document.title;
    document.title = data?.title || 'Alma';
    return () => { document.title = prev; };
  }, [data?.title]);

  if (!data) return null;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-header-left">
          <button className="btn btn--ghost app-header-logo-btn" onClick={onClose} aria-label="Back to Alma">
            <svg className="app-header-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round">
              <path d="M13 8c0-2.76-2.46-5-5.5-5S2 5.24 2 8h2l1-1 1 1h4"/>
              <path d="M13 7.14A5.82 5.82 0 0 1 16.5 6c3.04 0 5.5 2.24 5.5 5h-3l-1-1-1 1h-3"/>
              <path d="M5.89 9.71c-2.15 2.15-2.3 5.47-.35 7.43l4.24-4.25.7-.7.71-.71 2.12-2.12c-1.95-1.96-5.27-1.8-7.42.35"/>
              <path d="M11 15.5c.5 2.5-.17 4.5-1 6.5h4c2-5.5-.5-12-1-14"/>
            </svg>
          </button>
        </div>
        <div className="app-header-right">
          <button className="btn btn--ghost app-header-btn" onClick={onClose} aria-label="Close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" width="14" height="14">
              <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
            </svg>
          </button>
        </div>
      </header>
      <main className="static-page">
        <div className="static-page-content">
          <h1>{data.title}</h1>
          {data.body}
        </div>
      </main>
    </div>
  );
};

export default FooterPage;
