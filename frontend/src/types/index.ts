// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
export interface AttachmentData {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  checksum: string;
  created_at: string;
}

export interface ApiThinkingResult {
  response: string;
  thinking_summary: string[];
}

export interface ModeOption {
  value: string;
  label: string;
  icon: string;
}

export interface ModelOption {
  value: string;
  label: string;
  shortLabel?: string;
}

export interface ConversationEntry {
  id: string;
  title: string;
  mode: string;
  created_at: string;
  updated_at: string;
}

export interface MessageData {
  id?: string;
  role: string;
  timestamp: string;
  content: string;
  model?: string;
  thinking?: string | null;
  image?: string | null;
  attachments?: Record<string, unknown>[] | null;
  metadata?: Record<string, unknown> | null;
  thinking_duration_sec?: number;
}

export type ModelAvailabilityState = 'ready' | 'cooling-down' | 'unavailable';

export interface ModelAvailability {
  state: ModelAvailabilityState;
  availableAt?: number;
}

export interface ConversationData {
  id: string;
  title: string;
  mode: string;
  model?: string;
  schema_version?: number;
  created_at: string;
  updated_at: string;
  messages: MessageData[];
  title_is_manual?: boolean;
  metadata?: Record<string, unknown> | null;
}

export interface CreateConversationPayload {
  title?: string;
  mode: string;
  model?: string;
  messages: MessageData[];
  title_is_manual?: boolean;
  metadata?: Record<string, unknown> | null;
}
