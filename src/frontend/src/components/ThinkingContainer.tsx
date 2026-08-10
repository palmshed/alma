// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React, { useState } from 'react';

interface ThinkingContainerProps {
  content: string;
  durationSec?: number;
}

const THINKING_BOILERPLATE = /^(My thought process:|I need to:|Let's think:|Let's think about|Let's start by|Let me think|I'll think|I should start|First,|First:|Okay,|Alright,|So,)\s*/i;

function stripBoilerplate(text: string): string {
  return text.replace(THINKING_BOILERPLATE, '');
}

function formatDuration(sec?: number): string {
  if (sec == null) return 'Show reasoning';
  return `Thought for ${sec}s`;
}

function lineCount(text: string): number {
  if (!text) return 0;
  let count = 1;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '\n') count++;
  }
  return count;
}

const ThinkingContainer: React.FC<ThinkingContainerProps> = ({ content, durationSec }) => {
  const [expanded, setExpanded] = useState(false);
  if (!content) return null;

  const cleaned = stripBoilerplate(content);
  const isShort = lineCount(cleaned) <= 2;

  if (isShort) {
    return (
      <div className="thinking-container">
        <div className="thinking-content">
          <div style={{
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace'
          }}>
            {cleaned}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="thinking-container">
      <button
        className="thinking-toggle"
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        <span className="thinking-toggle-icon">{expanded ? '\u25BC' : '\u25B6'}</span>
        {formatDuration(durationSec)}
      </button>
      {expanded && (
        <div className="thinking-content">
          <div style={{
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace'
          }}>
            {cleaned}
          </div>
        </div>
      )}
    </div>
  );
};

export default ThinkingContainer;
