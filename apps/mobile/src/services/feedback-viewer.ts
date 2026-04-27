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
 * Compose the public URL for a stored attachment. The server guards
 * filenames with a /^fb_[a-z0-9_]+_[0-9]+\.(jpg|png)$/ regex, so only
 * strings matching that pattern are worth sending.
 */
export function attachmentUrl(filename: string): string {
  return `${baseOrigin()}/api/feedback/attachments/${encodeURIComponent(filename)}`;
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
    const resp = await fetch(url, {
      method: 'GET',
      signal: controller.signal,
      headers: { Accept: 'application/json' },
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
