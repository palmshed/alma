// SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
// SPDX-License-Identifier: MIT
import React from 'react';
import { Globe } from 'lucide-react';
import type { SourceData } from '../types';

interface SourceCardsProps {
  sources: SourceData[];
}

const SourceCards: React.FC<SourceCardsProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="source-cards-container" data-testid="source-cards">
      <div className="source-cards-header">
        <Globe size={12} className="source-cards-header-icon" />
        <span className="source-cards-header-title">Sources</span>
      </div>
      <div className="source-cards-list">
        {sources.map((source, index) => {
          const n = index + 1;
          const domain = source.domain || (source.url ? new URL(source.url).hostname.replace('www.', '') : 'web');
          return (
            <a
              key={index}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-card"
              title={source.snippet || source.title}
            >
              <span className="source-card-index">{n}</span>
              <span className="source-card-domain">{domain}</span>
              <span className="source-card-title">{source.title}</span>
            </a>
          );
        })}
      </div>
    </div>
  );
};

export default SourceCards;
