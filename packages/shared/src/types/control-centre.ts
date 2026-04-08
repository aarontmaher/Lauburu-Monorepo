import type { MemoryItemStatus, MemoryItemType } from '../constants/enums';

/** Suggestion from the MCP pending suggestions queue */
export interface Suggestion {
  id: string;
  title: string;
  source: string;
  safety: string;
  effort: string;
  status: string;
  category?: string;
  area: string;
}

/** Submit suggestion input — matches MCP submit_suggestion params */
export interface SuggestionInput {
  title: string;
  detail: string;
  source: string;
  area: string;
}

/** Single agent work status entry */
export interface AgentWorkStatus {
  task: string | null;
  status: string;
  branch: string | null;
  commit: string | null;
  last_commit: string | null;
  summary: string | null;
  updated_at: string | null;
}

/** Full work status response — keyed by agent name */
export interface WorkStatusResponse {
  schema_version: number;
  agents: Record<string, AgentWorkStatus>;
  updated_at: string | null;
}

/** Automation audit status for a single agent */
export interface AuditAgentStatus {
  complete: boolean;
  file: string | null;
}

/** Automation state from AUDIT_STATE.json */
export interface AutomationState {
  version: number;
  loop: number;
  phase: string;
  started_at: string;
  updated_at: string;
  audit_status: Record<string, AuditAgentStatus>;
  human_approved: boolean;
  stats: {
    total_issues_found: number;
    approved_count: number;
    implemented_count: number;
    verified_count: number;
    deferred_count: number;
    rejected_count: number;
  };
}

/** Handoff artifact */
export interface Handoff {
  path: string;
  schema_version: number;
  date: string;
  current_state: string;
  commits: Array<{ commit: string; summary: string }>;
  suggestion_status: Array<{ item: string; status: string }>;
  smoke_tests: string;
  remaining: string[];
}

/** Prompt job from the MCP control centre */
export interface PromptJob {
  id: string;
  prompt: string;
  status: 'pending' | 'claimed' | 'completed' | 'failed' | 'cancelled';
  target_agent?: string;
  priority?: string;
  source_client?: string;
  claimed_by?: string | null;
  result_summary?: string | null;
  result_artifact?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
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
