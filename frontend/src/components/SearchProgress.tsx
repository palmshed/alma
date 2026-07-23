// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import React from 'react';
import { Search, BookOpen, Sparkles, CheckCircle2 } from 'lucide-react';

interface SearchProgressProps {
  steps?: string[];
  activeStepIndex?: number;
}

const DEFAULT_STEPS = [
  'Searching the web...',
  'Reading sources...',
  'Generating answer...',
];

const STEP_ICONS = [
  <Search size={14} key="search" />,
  <BookOpen size={14} key="read" />,
  <Sparkles size={14} key="generate" />,
];

const SearchProgress: React.FC<SearchProgressProps> = ({
  steps = DEFAULT_STEPS,
  activeStepIndex = 1,
}) => {
  return (
    <div className="search-progress-container" data-testid="search-progress">
      <div className="search-progress-steps">
        {steps.map((stepText, idx) => {
          const isDone = idx < activeStepIndex;
          const isCurrent = idx === activeStepIndex;
          const icon = isDone ? (
            <CheckCircle2 size={14} className="search-step-icon done" />
          ) : (
            React.cloneElement(STEP_ICONS[idx % STEP_ICONS.length], {
              className: `search-step-icon ${isCurrent ? 'active' : 'pending'}`,
            })
          );

          return (
            <div
              key={idx}
              className={`search-progress-step ${
                isDone ? 'done' : isCurrent ? 'active' : 'pending'
              }`}
            >
              {icon}
              <span className="search-step-label">{stepText}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SearchProgress;
