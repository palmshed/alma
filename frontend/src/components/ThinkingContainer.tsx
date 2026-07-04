import React from 'react';
// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT

interface ThinkingContainerProps {
  content: string;
}

const ThinkingContainer: React.FC<ThinkingContainerProps> = ({ content }) => {
  if (!content) return null;

  return (
    <div className="thinking-container">
      <div style={{
        whiteSpace: 'pre-wrap',
        color: 'var(--text-secondary)',
        fontSize: '0.95rem',
        lineHeight: '1.6',
        fontFamily: 'monospace'
      }}>
        {content}
      </div>
    </div>
  );
};

export default ThinkingContainer;
