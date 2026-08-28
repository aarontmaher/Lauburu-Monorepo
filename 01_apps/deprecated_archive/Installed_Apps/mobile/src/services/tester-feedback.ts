/**
 * Tester feedback submission.
 * Fire-and-forget style — never blocks the app.
 *
 * Attachments are sent as base64-embedded images inside the JSON body
 * (capped at a few per submission, resized on-device before upload).
 * This avoids requiring multipart/form-data handling on the backend
 * and keeps the submission path identical whether or not a photo is
 * attached.
 */
import { AI_PUBLIC_BASE } from './ai-backend-config';

// Derive the feedback base from AI_PUBLIC_BASE.
// AI_PUBLIC_BASE looks like https://host/api/athlete-memory
// Feedback route is /api/feedback on the same origin.
function feedbackEndpoint(): string {
  try {
    const url = new URL(AI_PUBLIC_BASE);
    return `${url.origin}/api/feedback`;
  } catch {
    return 'http://localhost:3000/api/feedback';
  }
}

export type FeedbackType =
  | 'ui_cleanup'
  | 'bug'
  | 'app_error'
  | 'ai_answer_issue'
  | 'health_source_issue'
  | 'apple_health_issue'
  | 'samsung_health_connect_issue'
  | 'nutrition_issue'
  | 'hiit_workout_issue'
  | 'suggestion'
  | 'general';

export type FeedbackSeverity = 'low' | 'medium' | 'high' | 'blocking';

/**
 * Image attachment. `dataBase64` is the raw base64 payload without
 * a data-URI prefix. The backend reattaches the MIME type from `mime`.
 */
export interface FeedbackAttachment {
  mime: 'image/jpeg' | 'image/png';
  dataBase64: string;
  name?: string;
  widthPx?: number;
  heightPx?: number;
  sizeBytes?: number;
}

export interface FeedbackPayload {
  type: FeedbackType;
  severity: FeedbackSeverity;
  message: string;
  userId?: string | null;
  athleteId?: string | null;
  context?: Record<string, string | number | boolean | null>;
  attachments?: FeedbackAttachment[];
}

export interface FeedbackResult {
  ok: boolean;
  id?: string;
  error?: string;
}

/** Max attachments allowed per submission — keeps payload bounded. */
export const MAX_ATTACHMENTS = 3;

/**
 * Max bytes per attachment after client-side compression. 800KB leaves
 * room for 3 × ~800KB = 2.4MB + text, which Express bodyParser.json
 * handles comfortably when configured with a generous limit. Oversized
 * attachments are rejected client-side before upload.
 */
export const MAX_ATTACHMENT_BYTES = 800_000;

export async function submitTesterFeedback(payload: FeedbackPayload): Promise<FeedbackResult> {
  const url = feedbackEndpoint();
  try {
    const controller = new AbortController();
    // Longer timeout when attachments are present — base64 uploads
    // over a slow cell connection can legitimately take 30-60s for
    // 3 × ~800KB images. Tester reports of "Aborted" came from the
    // prior 30s ceiling firing during weak signal. Bumped to 60s with
    // attachments / 30s without.
    const timeoutMs = payload.attachments?.length ? 60_000 : 30_000;
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const resp = await fetch(url, {
      method: 'POST',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    clearTimeout(timer);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !(data as any).ok) {
      return { ok: false, error: (data as any).error ?? `HTTP ${resp.status}` };
    }
    return { ok: true, id: (data as any).id };
  } catch (e: any) {
    // Map AbortError → friendlier reason. Caller decides whether to
    // surface it; FeedbackFab uses this to show "Submit timed out —
    // your draft is saved. Tap Send to retry."
    const msg = e?.message ?? 'Network error';
    if (e?.name === 'AbortError' || /abort/i.test(msg)) {
      return { ok: false, error: 'Submit timed out (slow connection?). Your draft is saved — tap Send to retry.' };
    }
    return { ok: false, error: msg };
  }
}
