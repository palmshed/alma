// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import type { ModelOption, ModeOption } from '../types';

export const MODELS: ModelOption[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'openrouter', label: 'OpenRouter' },
];

export function getModelLabel(value: string): string {
  return MODELS.find(m => m.value === value)?.label || 'Auto';
}

const CITATION_RE = /\[(\d+(?:\]\s*\[\d+)*)\]/g;

export function linkCitations(content: string, sources: { url?: string }[] | undefined | null): string {
  if (!content || !sources || sources.length === 0) return content;
  return content.replace(CITATION_RE, (match, nums: string) => {
    return nums
      .split(/\s*\[\s*/)
      .map((n) => {
        const idx = parseInt(n.trim(), 10) - 1;
        const src = sources[idx];
        return src && src.url ? `[${idx + 1}](${src.url})` : `[${n.trim()}]`;
      })
      .join('');
  });
}

export const MODES: ModeOption[] = [
  { value: 'auto', label: 'Auto', icon: 'zap' },
  { value: 'chat', label: 'Chat', icon: 'message-square' },
  { value: 'code', label: 'Code', icon: 'code' },
  { value: 'canvas', label: 'Canvas', icon: 'layers' },
  { value: 'thinking', label: 'Thinking', icon: 'sparkles' },
  { value: 'images', label: 'Images', icon: 'image' },
];

export const SUGGESTIONS: Record<string, string[]> = {
  auto: ['Explain this code', 'Summarize this article', 'Generate release notes'],
  chat: ['Explain this code', 'Summarize this article', 'Generate release notes'],
  code: ['Explain this code', 'Refactor this function', 'Write unit tests for this module'],
  canvas: ['Summarize this article', 'Explain this code', 'Generate release notes'],
  thinking: ['Solve step by step: train distance problem', 'Explain the water cycle', 'Calculate compound interest'],
  images: ['A peaceful sunset over mountains', 'A futuristic city with neon lights', 'A cute robot with big eyes'],
};

export const LANGUAGES = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'en', label: 'English' },
  { value: 'bn', label: 'বাংলা' },
  { value: 'hi', label: 'हिन्दी' },
  { value: 'ta', label: 'தமிழ்' },
  { value: 'te', label: 'తెలుగు' },
  { value: 'mr', label: 'मराठी' },
  { value: 'es', label: 'Español' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
  { value: 'zh', label: '中文' },
  { value: 'ja', label: '日本語' },
];

export function getLanguageLabel(value: string): string {
  return LANGUAGES.find(l => l.value === value)?.label || 'Auto-detect';
}

export const ACCENT_PRESETS = [
  { color: '#24d455', hover: '#1fbf4a' },
  { color: '#3b82f6', hover: '#2563eb' },
  { color: '#8b5cf6', hover: '#7c3aed' },
  { color: '#f59e0b', hover: '#d97706' },
  { color: '#ec4899', hover: '#db2777' },
  { color: '#14b8a6', hover: '#0d9488' },
  { color: '#9ca3af', hover: '#6b7280' },
];

export function getEndpoint(mode: string): string {
  switch (mode) {
    case 'thinking': return '/api/generate-with-thinking';
    case 'web':
    case 'search':
    case 'auto':
    case 'code': return '/api/search';
    default: return '/api/generate';
  }
}

let _audioCtx: AudioContext | null = null;
function getAudioCtx(): AudioContext {
  if (!_audioCtx) _audioCtx = new AudioContext();
  return _audioCtx;
}

export function playNavSound(): void {
  try {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(420, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(640, ctx.currentTime + 0.07);
    gain.gain.setValueAtTime(0.06, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.12);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.12);
  } catch {}
}
