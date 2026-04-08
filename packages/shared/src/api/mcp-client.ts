/**
 * MCP Control Centre API client.
 * Matches the website's _CC_API_BASE fetch patterns.
 */
import { MCP_API_BASE } from '../constants/config';
import type { PromptJob, WorkStatus, SharedMemoryItem, Suggestion } from '../types/control-centre';

async function mcpFetch<T>(path: string, options?: RequestInit): Promise<T | null> {
  try {
    const resp = await fetch(`${MCP_API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers ?? {}),
      },
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<T>;
  } catch {
    return null;
  }
}

// --- Prompt Jobs ---

export async function listPromptJobs(): Promise<PromptJob[] | null> {
  return mcpFetch<PromptJob[]>('/prompt-jobs');
}

// --- Work Status ---

export async function getWorkStatus(): Promise<WorkStatus[] | null> {
  return mcpFetch<WorkStatus[]>('/work-status');
}

// --- Shared Memory ---

export async function getSharedMemory(
  userId: string,
): Promise<SharedMemoryItem[] | null> {
  return mcpFetch<SharedMemoryItem[]>(`/shared-memory?user_id=${userId}`);
}

export async function postSharedMemory(
  userId: string,
  action: string,
  item: Partial<SharedMemoryItem>,
): Promise<boolean> {
  const result = await mcpFetch('/shared-memory', {
    method: 'POST',
    body: JSON.stringify({ action, user_id: userId, item }),
  });
  return result !== null;
}

// --- Suggestions ---

export async function submitSuggestion(
  title: string,
  body: string,
): Promise<Suggestion | null> {
  return mcpFetch<Suggestion>('/suggestions', {
    method: 'POST',
    body: JSON.stringify({ title, body }),
  });
}

export async function listPendingSuggestions(): Promise<Suggestion[] | null> {
  return mcpFetch<Suggestion[]>('/suggestions?status=pending');
}
