export interface User {
  id: string;
  email: string;
  full_name?: string;
  role?: string;
  created_at: string;
  updated_at: string;
  consent_data_processing?: boolean;
  consent_voice_processing?: boolean;
  consent_video_processing?: boolean;
  consent_third_party_apis?: boolean;
  consent_whatsapp_ingestion?: boolean;
  billing_plan?: string;
  billing_period_start?: string;
  billing_period_end?: string;
  deleted_at?: string;
  last_data_export_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ToneConfig {
  warmth: number;
  humor: number;
  formality: number;
}

export interface Clone {
  id: string;
  user_id: string;
  name: string;
  description: string;
  tone_config: ToneConfig;
  avatar_url?: string;
  avatar_image_url?: string;
  llm_provider?: string;
  llm_model?: string;
  embedding_provider?: string;
  tts_provider?: string;
  tts_voice_id?: string;
  temperature?: number;
  max_tokens?: number;
  created_at: string;
  updated_at: string;
}

export interface CloneWithStats extends Clone {
  memory_count: number;
  conversation_count: number;
}

export interface Memory {
  id: string;
  user_id: string;
  clone_id: string;
  title?: string;
  content: string;
  source_type: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'clone' | 'system';
  content: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  clone_id: string;
  title?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  user_message: Message;
  clone_message: Message;
}

export interface Document {
  id: string;
  clone_id: string;
  user_id: string;
  title: string;
  content: string;
  source_type: string;
  created_at: string;
  updated_at: string;
}

export interface AIConfig {
  llm_provider?: string;
  llm_model?: string;
  embedding_provider?: string;
  tts_provider?: string;
  tts_voice_id?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface TTSResponse {
  audio_base64: string;
  format: string;
}

export interface DocumentWithStats extends Document {
  chunk_count: number;
}

export interface APIKey {
  id: string;
  user_id: string;
  label: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_requests: number;
  rate_limit_window_seconds: number;
  created_at: string;
  last_used_at?: string;
  revoked_at?: string;
}

export interface APIKeyCreateResponse extends APIKey {
  raw_key: string;
  warning: string;
}

export interface APIKeyCreate {
  label: string;
  scopes: string[];
  rate_limit_requests?: number;
  rate_limit_window_seconds?: number;
}

export interface AdminUserSummary {
  id: string;
  email: string;
  full_name?: string;
  role: string;
  billing_plan: string;
  created_at: string;
  clone_count: number;
  message_count_this_month: number;
}

export interface AdminCloneSummary {
  id: string;
  name: string;
  user_id: string;
  user_email: string;
  created_at: string;
  memory_count: number;
  conversation_count: number;
  document_count: number;
}

export interface PlatformStats {
  total_users: number;
  total_clones: number;
  total_conversations: number;
  total_messages: number;
  total_documents: number;
  active_users_this_month: number;
  users_by_plan: Record<string, number>;
}

export interface BillingQuota {
  plan: string;
  max_clones: number;
  max_messages_per_month: number;
  max_documents_per_clone: number;
}

export interface UsageStats {
  clones: {
    current: number;
    max: number;
    percentage: number;
  };
  messages_this_month: {
    current: number;
    max: number;
    percentage: number;
  };
  billing_plan: string;
}

export interface AvatarUploadResponse {
  avatar_image_url: string;
  message: string;
}
