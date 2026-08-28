/**
 * Read-side client for tester feedback. Pairs with the submit client in
 * tester-feedback.ts and the server routes in chat-app/src/server/routes/
 * feedback.ts. Attachment images are served at the same origin, so the
 * attachmentUrl() helper composes the fully-qualified URL a native
 * <Image> can render without any extra headers.
 */
import { AI_PUBLIC_BASE } from './ai-backend-config';

function baseOrigin(): string {
  try {
    return new URL(AI_PUBLIC_BASE).origin;
  } catch {
    return 'http://localhost:3000';
  }
}

function recentEndpoint(): string {
  return `${baseOrigin()}/api/feedback/recent`;
}

/**
 * Compose the URL for a stored attachment. The server guards
 * filenames with a /^fb_[a-z0-9_]+_[0-9]+\.(jpg|png)$/ regex, AND
 * now requires the admin token (x-athlete-memory-token) on every
 * GET. Returns a string URL — pair with `attachmentImageSource()`
 * if you need a React Native <Image> source object that includes
 * the admin token header.
 */
export function attachmentUrl(filename: string): string {
  return `${baseOrigin()}/api/feedback/attachments/${encodeURIComponent(filename)}`;
}

/**
 * React-Native `<Image source={...}>` helper that sets the admin
 * token header. Required since the feedback attachments endpoint
 * is admin-gated to prevent PII leak — the in-app Feedback Viewer
 * is admin-only, so it has the same env token (`EXPO_PUBLIC_
 * ATHLETE_MEMORY_TOKEN`) that the rest of the Admin/Dev surface
 * uses.
 */
export function attachmentImageSource(filename: string): { uri: string; headers?: Record<string, string> } {
  const token = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
  const uri = attachmentUrl(filename);
  if (token.length === 0) return { uri };
  return { uri, headers: { 'x-athlete-memory-token': token } };
}

export interface StoredAttachmentRef {
  filename: string;
  mime: string;
  sizeBytes: number;
  widthPx?: number;
  heightPx?: number;
}

export interface FeedbackRecord {
  id: string;
  createdAt: string;
  type: string;
  severity: string;
  message: string;
  userId: string | null;
  athleteId: string | null;
  context?: Record<string, string | number | boolean | null>;
  attachments?: StoredAttachmentRef[];
}

export interface FetchRecentResult {
  ok: boolean;
  records: FeedbackRecord[];
  error?: string;
}

export async function fetchRecentFeedback(): Promise<FetchRecentResult> {
  const url = recentEndpoint();
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10_000);
    const token = process.env.EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN ?? '';
    const resp = await fetch(url, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        // Admin-token gate on the server. The Feedback Viewer is
        // owner/admin-only by route gate, so the admin token is the
        // correct credential here. Public users cannot reach this
        // route from the app.
        ...(token.length > 0 ? { 'x-athlete-memory-token': token } : {}),
      },
    });
    clearTimeout(timer);
    if (!resp.ok) {
      return { ok: false, records: [], error: `HTTP ${resp.status}` };
    }
    const data = (await resp.json()) as { ok?: boolean; records?: FeedbackRecord[]; error?: string };
    if (!data.ok || !Array.isArray(data.records)) {
      return { ok: false, records: [], error: data.error ?? 'Malformed response.' };
    }
    return { ok: true, records: data.records };
  } catch (e: any) {
    return { ok: false, records: [], error: e?.message ?? 'Network error' };
  }
}

/**
 * One-string dump suitable for Copy full report. Keeps field order
 * stable (id/time/type/severity on top, context as sorted key=value
 * lines, attachments as filenames) so testers pasting into ChatGPT get
 * a predictable shape.
 */
export function formatFullReport(r: FeedbackRecord): string {
  const lines: string[] = [];
  lines.push(`id: ${r.id}`);
  lines.push(`time: ${r.createdAt}`);
  lines.push(`type: ${r.type}`);
  lines.push(`severity: ${r.severity}`);
  if (r.userId) lines.push(`userId: ${r.userId}`);
  if (r.athleteId) lines.push(`athleteId: ${r.athleteId}`);
  if (r.message) lines.push('', 'message:', r.message);
  if (r.context && Object.keys(r.context).length > 0) {
    lines.push('', 'context:');
    for (const key of Object.keys(r.context).sort()) {
      lines.push(`  ${key}: ${String(r.context[key] ?? '')}`);
    }
  }
  if (r.attachments && r.attachments.length > 0) {
    lines.push('', 'attachments:');
    for (const a of r.attachments) {
      lines.push(`  ${a.filename} (${a.mime}, ${a.sizeBytes} bytes)`);
    }
  }
  return lines.join('\n');
}
