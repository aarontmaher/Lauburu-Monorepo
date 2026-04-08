import type { MemoryItemStatus, MemoryItemType } from '../constants/enums';

/** Suggestion submitted via the app or website */
export interface Suggestion {
  id: string;
  user_id: string;
  title: string;
  body: string;
  status: string;
  created_at: string;
  updated_at: string;
}

/** Prompt job from the MCP control centre */
export interface PromptJob {
  id: string;
  prompt: string;
  status: 'pending' | 'claimed' | 'completed' | 'failed' | 'cancelled';
  agent?: string;
  result?: string;
  created_at: string;
  updated_at: string;
}

/** Work status from the MCP control centre */
export interface WorkStatus {
  agent: string;
  status: string;
  last_updated: string;
  current_task?: string;
}

/** Shared memory item — matches website schema */
export interface SharedMemoryItem {
  id: string;
  type: MemoryItemType;
  status: MemoryItemStatus;
  title: string;
  body: string;
  scope: 'personal' | 'general';
  confidence: number; // 0.0-1.0
  evidence?: string[];
  counterpoints?: string[];
  tags?: string[];
  approved_for_website?: boolean;
  review_history?: Array<{
    action: string;
    by: string;
    at: string;
    note?: string;
  }>;
  created_at: string;
  updated_at: string;
}
