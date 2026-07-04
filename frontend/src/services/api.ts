import type { ApiThinkingResult } from '../types';

const API_BASE =
  import.meta.env.DEV ? 'http://localhost:8000' : '';

async function request<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  generate(prompt: string): Promise<string> {
    return request<{ response: string }>('/api/generate', { prompt }).then(
      (d) => d.response,
    );
  },

  generateWithThinking(
    prompt: string,
  ): Promise<ApiThinkingResult> {
    return request<ApiThinkingResult>('/api/generate-with-thinking', {
      prompt,
    });
  },

  generateWithUrlContext(prompt: string): Promise<string> {
    return request<{ response: string }>('/api/generate-with-url-context', {
      prompt,
    }).then((d) => d.response);
  },

  async generateImage(prompt: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/api/generate-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    if (!res.ok) {
      const msg =
        (await res.json().catch(() => ({}))).error || res.statusText;
      throw new Error(msg);
    }
    return res.blob();
  },

  async textToSpeech(text: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/api/text-to-speech`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const msg =
        (await res.json().catch(() => ({}))).error || res.statusText;
      throw new Error(msg);
    }
    return res.blob();
  },
};
