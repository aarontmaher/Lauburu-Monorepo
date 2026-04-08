/**
 * Feedback persistence API.
 *
 * Uses the MCP /api/user-health endpoint with provider='feedback'
 * to store training examples without backend changes.
 *
 * Records are keyed by (date, provider='feedback') so each day
 * gets one feedback record that can be updated via append/dedup.
 */
import { MCP_API_BASE } from '../constants/config';
import type { TrainingExample } from '../types/feedback';

const TIMEOUT_MS = 10000;

interface PersistResult {
  ok: boolean;
  record_count?: number;
  error?: string;
}

/**
 * Persist training examples to MCP backend.
 * Uses /api/user-health POST with provider='feedback'.
 */
export async function persistTrainingExamples(
  userId: string,
  accessToken: string,
  examples: TrainingExample[],
): Promise<PersistResult> {
  if (examples.length === 0) return { ok: true, record_count: 0 };

  const records = examples.map((ex) => ({
    date: ex.date,
    provider: 'feedback',
    type: 'training_example',
    version: ex.version,
    data: ex,
  }));

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const resp = await fetch(`${MCP_API_BASE}/user-health?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        user_id: userId,
        action: 'append',
        records,
      }),
    });

    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { ok: false, error: body.error ?? `HTTP ${resp.status}` };
    }

    const body = await resp.json();
    return { ok: body.ok ?? true, record_count: body.record_count };
  } catch (e: any) {
    return { ok: false, error: e?.message ?? 'Network error' };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Fetch existing training examples from backend.
 */
export async function fetchTrainingExamples(
  userId: string,
): Promise<TrainingExample[]> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const resp = await fetch(
      `${MCP_API_BASE}/user-health?user_id=${encodeURIComponent(userId)}`,
      { signal: controller.signal },
    );
    if (!resp.ok) return [];

    const body = await resp.json();
    const records = body?.item?.records ?? [];

    return records
      .filter((r: any) => r.provider === 'feedback' && r.type === 'training_example')
      .map((r: any) => r.data as TrainingExample)
      .filter(Boolean);
  } catch {
    return [];
  } finally {
    clearTimeout(timer);
  }
}
