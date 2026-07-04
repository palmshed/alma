import type { ModeOption } from '../types';

export const MODES: ModeOption[] = [
  { value: 'canvas', label: 'Canvas', icon: 'layers' },
  { value: 'thinking', label: 'Thinking', icon: 'sparkles' },
  { value: 'web', label: 'Web', icon: 'globe' },
  { value: 'images', label: 'Images', icon: 'image' },
];

export const SUGGESTIONS: Record<string, string[]> = {
  canvas: ['Summarize this article', 'Explain this code', 'Generate release notes'],
  thinking: ['Solve step by step: train distance problem', 'Explain the water cycle', 'Calculate compound interest'],
  web: ['Search Wikipedia for quantum physics', 'Find latest AI research', 'Check GitHub trends'],
  images: ['A peaceful sunset over mountains', 'A futuristic city with neon lights', 'A cute robot with big eyes'],
};

export function getEndpoint(mode: string): string {
  switch (mode) {
    case 'thinking': return '/api/generate-with-thinking';
    case 'web': return '/api/generate-with-url-context';
    default: return '/api/generate';
  }
}
