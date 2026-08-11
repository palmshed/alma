// SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
// SPDX-License-Identifier: MIT
import type { ApiThinkingResult, AttachmentData, ConversationEntry, ConversationData, CreateConversationPayload, MessageData } from '../types';

const API_BASE =
  import.meta.env.DEV ? 'http://localhost:8000' : '';

async function request<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
  return res.json();
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'include' });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
  return res.json();
}

async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
  return res.json();
}

async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE', credentials: 'include' });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
}

export const api = {
  generate(prompt: string, messages?: MessageData[], mode?: string, language?: string, aiProvider?: string): Promise<string> {
    return request<{ response: string }>('/api/generate', { prompt, messages, mode, language, ai_provider: aiProvider }).then(
      (d) => d.response,
    );
  },

  search(
    prompt: string,
    messages?: MessageData[],
    options?: {
      mode?: string;
      provider?: string;
      max_results?: number;
      safe_search?: boolean;
      language?: string;
      ai_provider?: string;
    },
  ): Promise<import('../types').ApiSearchResult> {
    return request<import('../types').ApiSearchResult>('/api/search', {
      prompt,
      messages,
      mode: options?.mode || 'auto',
      provider: options?.provider || 'auto',
      max_results: options?.max_results ?? 5,
      safe_search: options?.safe_search ?? true,
      language: options?.language || 'auto',
      ai_provider: options?.ai_provider,
    });
  },

  generateWithThinking(
    prompt: string,
    messages?: MessageData[],
    language?: string,
    aiProvider?: string,
  ): Promise<ApiThinkingResult> {
    return request<ApiThinkingResult>('/api/generate-with-thinking', {
      prompt, messages, language, ai_provider: aiProvider,
    });
  },

  async generateImage(prompt: string): Promise<Blob> {
    const res = await fetch(`${API_BASE}/api/generate-image`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
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
      credentials: 'include',
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const msg =
        (await res.json().catch(() => ({}))).error || res.statusText;
      throw new Error(msg);
    }
    return res.blob();
  },

  async uploadAttachment(file: File): Promise<AttachmentData> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/attachments`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });
    if (!res.ok) {
      const msg = (await res.json().catch(() => ({}))).error || res.statusText;
      throw new Error(msg);
    }
    return res.json();
  },

  async deleteAttachment(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/api/attachments/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    if (!res.ok && res.status !== 404) {
      throw new Error('Failed to delete attachment');
    }
  },

  // ── Conversations ──

  listConversations(): Promise<ConversationEntry[]> {
    return apiGet<ConversationEntry[]>('/api/conversations');
  },

  getConversation(id: string): Promise<ConversationData> {
    return apiGet<ConversationData>(`/api/conversations/${id}`);
  },

  createConversation(data: CreateConversationPayload): Promise<ConversationData> {
    return request<ConversationData>('/api/conversations', data);
  },

  updateConversation(id: string, data: ConversationData): Promise<ConversationData> {
    return apiPut<ConversationData>(`/api/conversations/${id}`, data);
  },

  async deleteConversation(id: string): Promise<void> {
    return apiDelete(`/api/conversations/${id}`);
  },
};
