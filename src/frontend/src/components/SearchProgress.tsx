// SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
// SPDX-License-Identifier: MIT
import React from 'react';

const SearchProgress: React.FC = () => {
  return (
    <div className="search-progress-container" data-testid="search-progress">
      <span className="search-progress-dot" aria-hidden="true" />
      <span className="search-progress-label">Searching the web…</span>
    </div>
  );
};

export default SearchProgress;
