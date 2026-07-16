// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import type { ModeOption, ModelOption } from '../types';

export const MODES: ModeOption[] = [
  { value: 'canvas', label: 'Canvas', icon: 'layers' },
  { value: 'thinking', label: 'Thinking', icon: 'sparkles' },
  { value: 'web', label: 'Web', icon: 'globe' },
  { value: 'images', label: 'Images', icon: 'image' },
];

export const MODELS: ModelOption[] = [
  { value: 'auto', label: 'Auto (Smart Select)', shortLabel: 'Auto' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
  { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite' },
  { value: 'gemini-3.0-flash', label: 'Gemini 3 Flash' },
  { value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash Lite' },
  { value: 'gemini-3.5-flash', label: 'Gemini 3.5 Flash' },
];

export const MODEL_PRIORITY = ['gemini-2.5-flash', 'gemini-3.5-flash', 'gemini-3.0-flash', 'gemini-2.5-flash-lite', 'gemini-3.1-flash-lite'];

export function resolveModel(selectedModel: string, availability?: Record<string, { state: string; availableAt?: number }>): string {
  if (selectedModel !== 'auto') return selectedModel;
  const now = Date.now();
  for (const m of MODEL_PRIORITY) {
    const av = availability?.[m];
    if (!av || (av.availableAt && now >= av.availableAt)) {
      return m;
    }
  }
  return MODEL_PRIORITY[0];
}

export function getModelLabel(value: string): string {
  return MODELS.find(m => m.value === value)?.label || value;
}

export const SUGGESTIONS: Record<string, string[]> = {
  canvas: ['Summarize this article', 'Explain this code', 'Generate release notes'],
  thinking: ['Solve step by step: train distance problem', 'Explain the water cycle', 'Calculate compound interest'],
  web: ['Search Wikipedia for quantum physics', 'Find latest AI research', 'Check GitHub trends'],
  images: ['A peaceful sunset over mountains', 'A futuristic city with neon lights', 'A cute robot with big eyes'],
};

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
    case 'web': return '/api/generate-with-url-context';
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
