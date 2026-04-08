/**
 * Supabase Edge Function API layer.
 * Matches the website's fetch patterns exactly.
 * All functions require JWT authorization.
 */
import { SUPABASE_FUNCTIONS_URL } from '../constants/config';
import type { ProgressEntry, NoteEntry, UserProfile, SuccessLogEntry } from '../types/user';
import type { DailyMetricsRow } from '../types/health';

export type GetAccessToken = () => Promise<string | null>;

async function apiFetch<T>(
  endpoint: string,
  getToken: GetAccessToken,
  options?: RequestInit,
): Promise<T | null> {
  const token = await getToken();
  if (!token) return null;

  try {
    const resp = await fetch(`${SUPABASE_FUNCTIONS_URL}/${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options?.headers ?? {}),
      },
    });
    if (!resp.ok) return null;
    return resp.json() as Promise<T>;
  } catch {
    return null;
  }
}

// --- Progress ---

export async function getProgress(
  getToken: GetAccessToken,
): Promise<ProgressEntry[] | null> {
  const data = await apiFetch<{ items: ProgressEntry[] }>('progress', getToken);
  return data?.items ?? null;
}

export async function updateProgress(
  getToken: GetAccessToken,
  techniqueKey: string,
  status: string,
): Promise<boolean> {
  const result = await apiFetch('progress', getToken, {
    method: 'POST',
    body: JSON.stringify({ technique_key: techniqueKey, status }),
  });
  return result !== null;
}

// --- Profile ---

export async function getProfile(
  getToken: GetAccessToken,
): Promise<UserProfile | null> {
  return apiFetch<UserProfile>('profile', getToken);
}

// --- Notes ---

export async function getNotes(
  getToken: GetAccessToken,
): Promise<NoteEntry[] | null> {
  const data = await apiFetch<{ items: NoteEntry[] }>('notes', getToken);
  return data?.items ?? null;
}

export async function saveNote(
  getToken: GetAccessToken,
  techniqueKey: string,
  noteText: string,
): Promise<boolean> {
  const result = await apiFetch('notes', getToken, {
    method: 'POST',
    body: JSON.stringify({ technique_key: techniqueKey, note_text: noteText }),
  });
  return result !== null;
}

// --- Success Log ---

export async function getSuccessLog(
  getToken: GetAccessToken,
): Promise<SuccessLogEntry[] | null> {
  const data = await apiFetch<{ items: SuccessLogEntry[] }>('success-log', getToken);
  return data?.items ?? null;
}

export async function logSuccess(
  getToken: GetAccessToken,
  techniqueKey: string,
): Promise<boolean> {
  const result = await apiFetch('success-log', getToken, {
    method: 'POST',
    body: JSON.stringify({ technique_key: techniqueKey }),
  });
  return result !== null;
}

// --- Health ---

/** Response from GET /health-status?provider=... */
export interface HealthStatusResponse {
  ok: boolean;
  provider: string;
  status: string; // 'not_connected' | 'manual_import' | 'oauth' | etc
  connection_mode?: string;
  last_sync_at: string | null;
  last_error: string | null;
  sync_failed_count?: number;
}

export async function getHealthStatus(
  getToken: GetAccessToken,
  provider: string,
): Promise<HealthStatusResponse | null> {
  return apiFetch<HealthStatusResponse>(
    `health-status?provider=${encodeURIComponent(provider)}`,
    getToken,
  );
}

/** Response from POST /health-import */
export interface HealthImportResult {
  ok: boolean;
  import_id: string;
  record_count: number;
  date_range: { start: string; end: string };
  connection_status: string;
}

/**
 * Import health data to backend.
 * Matches the edge function contract: { provider, import_mode, raw_payload }.
 * raw_payload is an array of daily records with date + metric fields.
 */
export async function importHealthData(
  getToken: GetAccessToken,
  provider: string,
  importMode: string,
  rawPayload: Record<string, unknown>[],
): Promise<HealthImportResult | null> {
  return apiFetch<HealthImportResult>('health-import', getToken, {
    method: 'POST',
    body: JSON.stringify({
      provider,
      import_mode: importMode,
      raw_payload: rawPayload,
    }),
  });
}
