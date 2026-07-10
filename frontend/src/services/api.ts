import type { ApiThinkingResult, AttachmentData, ConversationEntry, ConversationData, CreateConversationPayload, MessageData } from '../types';

const API_BASE =
  import.meta.env.DEV ? 'http://localhost:8000' : '';

export class ApiError extends Error {
  status: number;
  retryAfter?: number;

  constructor(msg: string, status: number, retryAfter?: number) {
    super(msg);
    this.name = 'ApiError';
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

export function isQuotaError(err: unknown): err is ApiError {
  return err instanceof ApiError && (err.status === 429 || err.status === 503);
}

async function request<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    const retryAfter = res.headers.get('Retry-After');
    throw new ApiError(msg, res.status, retryAfter ? parseInt(retryAfter, 10) : undefined);
  }
  return res.json();
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
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
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
  return res.json();
}

async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
  if (!res.ok) {
    const msg = (await res.json().catch(() => ({}))).error || res.statusText;
    throw new Error(msg);
  }
}

export const api = {
  generate(prompt: string, messages?: MessageData[], model?: string): Promise<string> {
    return request<{ response: string }>('/api/generate', { prompt, messages, model }).then(
      (d) => d.response,
    );
  },

  generateWithThinking(
    prompt: string,
    messages?: MessageData[],
    model?: string,
  ): Promise<ApiThinkingResult> {
    return request<ApiThinkingResult>('/api/generate-with-thinking', {
      prompt, messages, model,
    });
  },

  generateWithUrlContext(prompt: string, messages?: MessageData[], model?: string): Promise<string> {
    return request<{ response: string }>('/api/generate-with-url-context', {
      prompt, messages, model,
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

  async uploadAttachment(file: File): Promise<AttachmentData> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/attachments`, {
      method: 'POST',
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
