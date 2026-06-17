/**
 * MCP Control Centre HTTP API client.
 * Calls the same endpoints as the website's _CC_API_BASE.
 *
 * Available HTTP endpoints (verified):
 *   GET  /api/work-status    → { ok, item: WorkStatusResponse }
 *   GET  /api/prompt-jobs    → { ok, items: PromptJob[] }
 *   GET  /api/suggestions    → { ok, items: [] }  (submitted suggestions)
 *   POST /api/suggestions    → submit a new suggestion
 *   GET  /api/shared-memory  → { ok, items: SharedMemoryItem[] }
 *   POST /api/shared-memory  → update shared memory
 *
 * Not available over HTTP (MCP-only):
 *   list_pending_suggestions, get_automation_state, get_handoff
 */
import { MCP_API_BASE } from '../constants/config';
import type {
  PromptJob,
  WorkStatusResponse,
  SharedMemoryItem,
  SuggestionInput,
} from '../types/control-centre';

const TIMEOUT_MS = 8000;

async function mcpFetch<T>(path: string, options?: RequestInit): Promise<T | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const resp = await fetch(`${MCP_API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers ?? {}),
      },
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<T>;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

// --- Work Status ---

interface WorkStatusEnvelope {
  ok: boolean;
  item: WorkStatusResponse;
}

export async function getWorkStatus(): Promise<WorkStatusResponse | null> {
  const data = await mcpFetch<WorkStatusEnvelope>('/work-status');
  return data?.ok ? data.item : null;
}

// --- Prompt Jobs ---

interface PromptJobsEnvelope {
  ok: boolean;
  items: PromptJob[];
}

export async function listPromptJobs(): Promise<PromptJob[] | null> {
  const data = await mcpFetch<PromptJobsEnvelope>('/prompt-jobs');
  return data?.ok ? data.items : null;
}

// --- Suggestions (submitted by users) ---

interface SuggestionsEnvelope {
  ok: boolean;
  items: Array<Record<string, unknown>>;
}

export async function listSubmittedSuggestions(): Promise<Array<Record<string, unknown>> | null> {
  const data = await mcpFetch<SuggestionsEnvelope>('/suggestions');
  return data?.ok ? data.items : null;
}

export async function submitSuggestion(input: SuggestionInput): Promise<boolean> {
  const data = await mcpFetch<{ ok: boolean }>('/suggestions', {
    method: 'POST',
    body: JSON.stringify(input),
  });
  return data?.ok ?? false;
}

// --- Shared Memory ---

export async function getSharedMemory(
  userId: string,
): Promise<SharedMemoryItem[] | null> {
  const data = await mcpFetch<{ ok: boolean; items: SharedMemoryItem[] }>(
    `/shared-memory?user_id=${encodeURIComponent(userId)}`,
  );
  return data?.ok ? data.items : null;
}

export async function postSharedMemory(
  userId: string,
  action: string,
  item: Partial<SharedMemoryItem>,
): Promise<boolean> {
  const data = await mcpFetch<{ ok: boolean }>('/shared-memory', {
    method: 'POST',
    body: JSON.stringify({ action, user_id: userId, item }),
  });
  return data?.ok ?? false;
}
