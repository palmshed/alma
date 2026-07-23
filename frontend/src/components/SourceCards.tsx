// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React from 'react';
import { Globe, ExternalLink } from 'lucide-react';
import type { SourceData } from '../types';

interface SourceCardsProps {
  sources: SourceData[];
}

const SourceCards: React.FC<SourceCardsProps> = ({ sources }) => {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="source-cards-container" data-testid="source-cards">
      <div className="source-cards-header">
        <Globe size={14} className="source-cards-header-icon" />
        <span className="source-cards-header-title">Sources</span>
      </div>
      <div className="source-cards-grid">
        {sources.map((source, index) => {
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
              <div className="source-card-top">
                <span className="source-card-domain">{domain}</span>
                <ExternalLink size={12} className="source-card-link-icon" />
              </div>
              <div className="source-card-title">{source.title}</div>
              {source.snippet && <div className="source-card-snippet">{source.snippet}</div>}
            </a>
          );
        })}
      </div>
    </div>
  );
};

export default SourceCards;
