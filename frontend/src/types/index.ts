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
  thinking?: string | null;
  image?: string | null;
  attachments?: Record<string, unknown>[] | null;
  metadata?: Record<string, unknown> | null;
}

export interface ConversationData {
  id: string;
  title: string;
  mode: string;
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
  messages: MessageData[];
  title_is_manual?: boolean;
  metadata?: Record<string, unknown> | null;
}
