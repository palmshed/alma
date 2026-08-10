// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import { useState, useCallback } from 'react';

interface UseComposerReturn {
  input: string;
  setInput: (value: string) => void;
  hasText: boolean;
  clear: () => void;
}

export function useComposer(initialValue = ''): UseComposerReturn {
  const [input, setInput] = useState(initialValue);
  const hasText = input.trim().length > 0;

  const clear = useCallback(() => setInput(''), []);

  return { input, setInput, hasText, clear };
}
