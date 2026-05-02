/**
 * Tester feedback route — /api/feedback
 *
 * Accepts bug reports, app errors, AI answer issues, suggestions, and
 * general feedback from installed mobile testers. Stored as JSON files
 * under data/tester-feedback/ with one file per submission. Image
 * attachments (base64-embedded in the JSON body) are decoded and
 * written alongside the record under data/tester-feedback/attachments/.
 *
 * Privacy:
 * - Does not require the internal API token (public app-facing route).
 * - Accepts userId and athleteId for scoping; trusts client-sent values
 *   because the shared app-facing auth covers this.
 * - Never writes to stable athlete memory.
 * - Strips any context fields containing 'token', 'secret', 'password',
 *   or 'api_key'.
 * - Rejects attachments above MAX_ATTACHMENT_BYTES after decoding, and
 *   caps attachments per submission at MAX_ATTACHMENTS.
 */

import { Router } from 'express';
import fs from 'fs/promises';
import path from 'path';

const router = Router();

const FEEDBACK_DIR = path.resolve(__dirname, '../../../data/tester-feedback');
const ATTACHMENT_DIR = path.join(FEEDBACK_DIR, 'attachments');

const VALID_TYPES = new Set([
  'ui_cleanup',
  'bug',
  'app_error',
  'ai_answer_issue',
  'health_source_issue',
  'apple_health_issue',
  'samsung_health_connect_issue',
  'nutrition_issue',
  'hiit_workout_issue',
  'suggestion',
  'general',
]);
const VALID_SEVERITY = new Set(['low', 'medium', 'high', 'blocking']);

const MAX_ATTACHMENTS = 3;
// 1MB upper bound per attachment after decoding. Client compresses to
// ~800KB; the extra 200KB absorbs base64 + metadata variance.
const MAX_ATTACHMENT_BYTES = 1_000_000;
const VALID_MIME = new Set(['image/jpeg', 'image/png']);

function sanitizeContext(ctx: Record<string, unknown> | undefined | null): Record<string, unknown> {
  if (!ctx || typeof ctx !== 'object') return {};
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(ctx)) {
    const lower = k.toLowerCase();
    if (lower.includes('token') || lower.includes('secret') || lower.includes('password') || lower.includes('api_key')) {
      continue;
    }
    // Only allow primitive values and small string arrays — no nested secrets
    if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean' || v === null) {
      out[k] = v;
    } else if (Array.isArray(v) && v.every((x) => typeof x === 'string')) {
      out[k] = v.slice(0, 20);
    }
  }
  return out;
}

interface StoredAttachmentRef {
  filename: string;
  mime: string;
  sizeBytes: number;
  widthPx?: number;
  heightPx?: number;
}

interface AttachmentInput {
  mime?: unknown;
  dataBase64?: unknown;
  name?: unknown;
  widthPx?: unknown;
  heightPx?: unknown;
  sizeBytes?: unknown;
}

async function persistAttachments(
  id: string,
  raw: unknown,
): Promise<{ stored: StoredAttachmentRef[]; error?: string }> {
  if (!Array.isArray(raw)) return { stored: [] };
  if (raw.length === 0) return { stored: [] };
  if (raw.length > MAX_ATTACHMENTS) {
    return { stored: [], error: `Too many attachments (max ${MAX_ATTACHMENTS}).` };
  }

  await fs.mkdir(ATTACHMENT_DIR, { recursive: true });
  const stored: StoredAttachmentRef[] = [];

  for (let i = 0; i < raw.length; i++) {
    const item = raw[i] as AttachmentInput;
    const mime = typeof item.mime === 'string' ? item.mime : '';
    const dataBase64 = typeof item.dataBase64 === 'string' ? item.dataBase64 : '';
    if (!VALID_MIME.has(mime)) {
      return { stored, error: `Unsupported attachment type at index ${i}.` };
    }
    if (!dataBase64) {
      return { stored, error: `Empty attachment at index ${i}.` };
    }
    let buf: Buffer;
    try {
      buf = Buffer.from(dataBase64, 'base64');
    } catch {
      return { stored, error: `Invalid base64 at index ${i}.` };
    }
    if (buf.length === 0 || buf.length > MAX_ATTACHMENT_BYTES) {
      return { stored, error: `Attachment ${i} too large or empty.` };
    }
    const ext = mime === 'image/png' ? 'png' : 'jpg';
    const filename = `${id}_${i}.${ext}`;
    await fs.writeFile(path.join(ATTACHMENT_DIR, filename), buf);
    stored.push({
      filename,
      mime,
      sizeBytes: buf.length,
      widthPx: typeof item.widthPx === 'number' ? item.widthPx : undefined,
      heightPx: typeof item.heightPx === 'number' ? item.heightPx : undefined,
    });
  }
  return { stored };
}

function genId(): string {
  return `fb_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

// POST /api/feedback
router.post('/', async (req: any, res: any) => {
  try {
    const { type, message, severity, userId, athleteId, context, attachments } = req.body ?? {};

    const safeType = VALID_TYPES.has(String(type)) ? String(type) : 'general';
    const safeSeverity = VALID_SEVERITY.has(String(severity)) ? String(severity) : 'medium';
    const safeMessage = typeof message === 'string' ? message.slice(0, 4000).trim() : '';
    const hasAttachments = Array.isArray(attachments) && attachments.length > 0;

    if (!safeMessage && !hasAttachments) {
      res.status(400).json({ ok: false, error: 'Feedback needs a message or an attachment.' });
      return;
    }

    const id = genId();
    const attachmentResult = await persistAttachments(id, attachments);
    if (attachmentResult.error) {
      res.status(400).json({ ok: false, error: attachmentResult.error });
      return;
    }

    const now = new Date().toISOString();
    const safeUserId = typeof userId === 'string' ? userId.slice(0, 200) : null;
    const safeAthleteId = typeof athleteId === 'string' ? athleteId.slice(0, 200) : null;
    // Augment the sanitized client context with a server-stamped
    // signed_in boolean so triage can filter anonymous vs identified
    // submissions cleanly without inferring from null userId. Matches
    // the existing privacy contract — we never invent identity, just
    // tag what the client already declared.
    const sanitizedContext = sanitizeContext(context);
    sanitizedContext.signed_in = !!safeUserId;
    const record = {
      id,
      createdAt: now,
      type: safeType,
      severity: safeSeverity,
      message: safeMessage,
      userId: safeUserId,
      athleteId: safeAthleteId,
      context: sanitizedContext,
      attachments: attachmentResult.stored,
    };

    await fs.mkdir(FEEDBACK_DIR, { recursive: true });
    await fs.writeFile(
      path.join(FEEDBACK_DIR, `${id}.json`),
      `${JSON.stringify(record, null, 2)}\n`,
      'utf8',
    );

    res.status(200).json({
      ok: true,
      id,
      receivedAt: now,
      attachmentCount: attachmentResult.stored.length,
    });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Feedback submission failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

/** Archive statuses an admin can set on a record. Soft-delete only —
 *  the JSON file remains on disk so we can audit decisions later. */
const VALID_ARCHIVE_STATUSES = new Set([
  'archived', 'dismissed', 'spam', 'test', 'not_actionable',
]);

/** Best-effort heuristic — flags records whose message + attachment
 *  combo is unlikely to be actionable. Used by /triage-suggestions
 *  to PROPOSE archiving, never auto-archive. */
function classifyLikelyNotActionable(record: any): { suggested: boolean; reason: string | null } {
  const msg = String(record?.message ?? '').trim().toLowerCase();
  const attCount = (record?.attachments ?? []).length;
  if (msg.length === 0 && attCount === 0) return { suggested: true, reason: 'empty_message_no_attachment' };
  if (msg.length <= 3) return { suggested: true, reason: `near_empty_message_${msg.length}_chars` };
  // Common smoke-test patterns.
  if (/^(hi|hey|hello|test|testing|asdf|qwer|abc|123|\.+|\?+)\s*$/i.test(msg)) {
    return { suggested: true, reason: 'placeholder_text' };
  }
  // Records the system itself created for verification.
  if (msg.includes('e2e verification entry') || msg.includes('safe to delete') || msg.includes('signed_in flag verification')) {
    return { suggested: true, reason: 'self_test_entry' };
  }
  return { suggested: false, reason: null };
}

/** Internal-only auth gate for archive operations. Reuses
 *  ATHLETE_MEMORY_API_TOKEN — same shared-secret already in use for
 *  /api/athlete-memory/* routes. Public users cannot archive. */
function requireAdminToken(req: any, res: any, next: any): void {
  const expected = process.env.ATHLETE_MEMORY_API_TOKEN;
  if (!expected) {
    res.status(503).json({ ok: false, error: 'Admin endpoints disabled until ATHLETE_MEMORY_API_TOKEN is configured.' });
    return;
  }
  const presented = req.header('x-athlete-memory-token');
  if (presented !== expected) {
    res.status(403).json({ ok: false, error: 'Forbidden.' });
    return;
  }
  next();
}

// GET /api/feedback/recent — admin/export helper.
// Returns the last N feedback records with context + attachment refs so
// Aaron can paste one into ChatGPT or compile a daily digest. Does not
// include attachment bytes (paths only — fetch those via /attachments).
//
// Hides archived/dismissed/spam/test/not_actionable records by default.
// Pass ?includeArchived=true to see all records (e.g. for triage review
// or restoring an accidentally-archived item).
router.get('/recent', async (req: any, res: any) => {
  try {
    const includeArchived = String(req.query.includeArchived ?? '') === 'true'
      || String(req.query.includeArchived ?? '') === '1';
    await fs.mkdir(FEEDBACK_DIR, { recursive: true });
    const files = await fs.readdir(FEEDBACK_DIR);
    // Read more than 25 raw files because we may filter some out.
    const jsons = files.filter((f) => f.endsWith('.json')).sort().reverse().slice(0, 100);
    const records = (await Promise.all(
      jsons.map(async (f) => {
        try {
          const raw = await fs.readFile(path.join(FEEDBACK_DIR, f), 'utf8');
          return JSON.parse(raw);
        } catch { return null; }
      }),
    )).filter(Boolean);
    const visible = includeArchived
      ? records
      : records.filter((r) => !r.archived || !r.archived.status);
    res.status(200).json({
      ok: true,
      records: visible.slice(0, 25),
      hidden_count: records.length - visible.length,
      include_archived: includeArchived,
    });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Failed to load feedback.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// POST /api/feedback/:id/archive — soft-delete a feedback record.
// Body: { status: 'archived'|'dismissed'|'spam'|'test'|'not_actionable',
//         reason?: string }
// Auth: x-athlete-memory-token (admin-only). Public users get 403.
//
// Soft-delete: the JSON file stays on disk, just gets an `archived`
// stanza appended. Future call to GET /recent will hide it unless
// ?includeArchived=true. Reversible via /:id/unarchive.
router.post('/:id/archive', requireAdminToken, async (req: any, res: any) => {
  try {
    const { id } = req.params;
    if (!/^fb_[A-Za-z0-9_]+$/.test(String(id))) {
      res.status(400).json({ ok: false, error: 'Invalid feedback id.' });
      return;
    }
    const { status, reason } = req.body ?? {};
    const safeStatus = VALID_ARCHIVE_STATUSES.has(String(status)) ? String(status) : 'archived';
    const safeReason = typeof reason === 'string' ? reason.slice(0, 500) : null;
    const filePath = path.join(FEEDBACK_DIR, `${id}.json`);
    const raw = await fs.readFile(filePath, 'utf8').catch(() => null);
    if (!raw) { res.status(404).json({ ok: false, error: 'Feedback not found.' }); return; }
    const record = JSON.parse(raw);
    record.archived = {
      status: safeStatus,
      reason: safeReason,
      archived_at: new Date().toISOString(),
    };
    await fs.writeFile(filePath, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
    res.status(200).json({ ok: true, id, archived: record.archived });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Archive failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// POST /api/feedback/:id/unarchive — reverse a soft-delete.
router.post('/:id/unarchive', requireAdminToken, async (req: any, res: any) => {
  try {
    const { id } = req.params;
    if (!/^fb_[A-Za-z0-9_]+$/.test(String(id))) {
      res.status(400).json({ ok: false, error: 'Invalid feedback id.' });
      return;
    }
    const filePath = path.join(FEEDBACK_DIR, `${id}.json`);
    const raw = await fs.readFile(filePath, 'utf8').catch(() => null);
    if (!raw) { res.status(404).json({ ok: false, error: 'Feedback not found.' }); return; }
    const record = JSON.parse(raw);
    delete record.archived;
    await fs.writeFile(filePath, `${JSON.stringify(record, null, 2)}\n`, 'utf8');
    res.status(200).json({ ok: true, id, restored: true });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Unarchive failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// GET /api/feedback/triage-suggestions — admin helper. Returns a list
// of feedback ids that look likely-not-actionable (placeholder text,
// near-empty messages, self-test entries) so Aaron can review then
// archive in bulk. Read-only — does NOT auto-archive.
router.get('/triage-suggestions', requireAdminToken, async (_req: any, res: any) => {
  try {
    await fs.mkdir(FEEDBACK_DIR, { recursive: true });
    const files = await fs.readdir(FEEDBACK_DIR);
    const jsons = files.filter((f) => f.endsWith('.json'));
    const records = (await Promise.all(
      jsons.map(async (f) => {
        try {
          const raw = await fs.readFile(path.join(FEEDBACK_DIR, f), 'utf8');
          return JSON.parse(raw);
        } catch { return null; }
      }),
    )).filter(Boolean);
    const suggestions = records
      .filter((r) => !r.archived?.status)
      .map((r) => {
        const c = classifyLikelyNotActionable(r);
        return c.suggested ? {
          id: r.id,
          createdAt: r.createdAt,
          type: r.type,
          severity: r.severity,
          message: r.message,
          attachment_count: (r.attachments ?? []).length,
          suggested_archive_status: c.reason === 'self_test_entry' ? 'test' : 'not_actionable',
          reason: c.reason,
        } : null;
      })
      .filter(Boolean);
    res.status(200).json({
      ok: true,
      total_records: records.length,
      not_already_archived: records.filter((r) => !r.archived?.status).length,
      suggestions,
      hint: 'POST /api/feedback/<id>/archive {"status":"not_actionable"} to soft-delete each. Use ?includeArchived=true on /recent to see them again.',
    });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Triage suggestions failed.',
      detail: error instanceof Error ? error.message : 'unknown',
    });
  }
});

// GET /api/feedback/attachments/:filename — serves a stored attachment
// for inline viewing. Filenames are prefixed with feedback IDs and are
// not user-controlled inputs from the client.
router.get('/attachments/:filename', async (req: any, res: any) => {
  try {
    const filename = String(req.params.filename ?? '');
    // Guard against path traversal — only allow fb_*_<n>.(jpg|png)
    if (!/^fb_[a-z0-9_]+_[0-9]+\.(jpg|png)$/i.test(filename)) {
      res.status(400).json({ ok: false, error: 'Invalid filename.' });
      return;
    }
    const filePath = path.join(ATTACHMENT_DIR, filename);
    const buf = await fs.readFile(filePath);
    const mime = filename.endsWith('.png') ? 'image/png' : 'image/jpeg';
    res.setHeader('Content-Type', mime);
    res.status(200).send(buf);
  } catch {
    res.status(404).json({ ok: false, error: 'Attachment not found.' });
  }
});

export default router;
