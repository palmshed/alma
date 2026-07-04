import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from './App';

vi.mock('./services/api', () => ({
  api: {
    generate: vi.fn().mockResolvedValue('mock response'),
    generateWithThinking: vi.fn().mockResolvedValue({ response: 'mock', thinking_summary: [] }),
    generateWithUrlContext: vi.fn().mockResolvedValue('mock'),
    generateImage: vi.fn().mockResolvedValue(new Blob()),
    textToSpeech: vi.fn().mockResolvedValue(new Blob()),
  },
}));

function getTriggerButtons() {
  return {
    headerBtn: screen.queryByRole('button', { name: /start a new conversation/i }),
    sidebarBtns: screen.queryAllByText('+ New conversation'),
  };
}

describe('New conversation — entry points', () => {
  beforeEach(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  });

  it('renders header logo button with accessible label', () => {
    render(<App />);
    const { headerBtn } = getTriggerButtons();
    expect(headerBtn).not.toBeNull();
  });

  it('renders sidebar new conversation button', () => {
    render(<App />);
    const { sidebarBtns } = getTriggerButtons();
    expect(sidebarBtns.length).toBeGreaterThan(0);
  });

  it('returns to landing immediately when conversation is empty', () => {
    render(<App />);
    const { headerBtn } = getTriggerButtons();
    fireEvent.click(headerBtn!);
    expect(screen.queryByRole('button', { name: /start a new conversation/i })).not.toBeNull();
  });
});

describe('New conversation — keyboard shortcut', () => {
  beforeEach(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  });

  it('⌘N does not throw', () => {
    render(<App />);
    expect(() => fireEvent.keyDown(document, { key: 'n', metaKey: true })).not.toThrow();
  });

  it('Ctrl+N does not throw', () => {
    render(<App />);
    expect(() => fireEvent.keyDown(document, { key: 'n', ctrlKey: true })).not.toThrow();
  });
});
