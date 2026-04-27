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
    const record = {
      id,
      createdAt: now,
      type: safeType,
      severity: safeSeverity,
      message: safeMessage,
      userId: typeof userId === 'string' ? userId.slice(0, 200) : null,
      athleteId: typeof athleteId === 'string' ? athleteId.slice(0, 200) : null,
      context: sanitizeContext(context),
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

// GET /api/feedback/recent — admin/export helper.
// Returns the last N feedback records with context + attachment refs so
// Aaron can paste one into ChatGPT or compile a daily digest. Does not
// include attachment bytes (paths only — fetch those via /attachments).
router.get('/recent', async (_req: any, res: any) => {
  try {
    await fs.mkdir(FEEDBACK_DIR, { recursive: true });
    const files = await fs.readdir(FEEDBACK_DIR);
    const jsons = files.filter((f) => f.endsWith('.json')).sort().reverse().slice(0, 25);
    const records = await Promise.all(
      jsons.map(async (f) => {
        try {
          const raw = await fs.readFile(path.join(FEEDBACK_DIR, f), 'utf8');
          return JSON.parse(raw);
        } catch {
          return null;
        }
      }),
    );
    res.status(200).json({ ok: true, records: records.filter(Boolean) });
  } catch (error) {
    res.status(500).json({
      ok: false,
      error: 'Failed to load feedback.',
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
