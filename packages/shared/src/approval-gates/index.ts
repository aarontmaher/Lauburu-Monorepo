/**
 * Approval gate model — automation pauses on a gate and resumes
 * only when Aaron approves, defers, or the gate auto-applies its
 * safeDefault on expiry.
 *
 * Pure types + transitions live here so they're shared between the
 * mobile app store and the cloudflare-worker MCP layer when (later)
 * a project.list_approval_gates / project.approve_gate tool ships.
 *
 * Privacy / safety:
 *   - Description text and actionPayload are short, sanitised
 *     summaries — no secrets, no token-shaped strings.
 *   - safeDefault MUST be the conservative outcome (e.g. "skip",
 *     "do_not_run", "wait"); never "proceed" or "deploy". The MVP
 *     enforces this at construction time via assertSafeDefault.
 *   - State transitions are append-only on the wire — every change
 *     records resolvedAt + resolvedBy so an audit can reconstruct
 *     who unblocked what. Mobile-side store enforces this; the
 *     transition functions below are pure and the caller writes
 *     the result back.
 */

/** Core action verbs. Add carefully — every new verb needs a safeDefault rule. */
export type ApprovalActionType =
  | 'eas_build'
  | 'eas_submit'
  | 'worker_deploy'
  | 'play_console_upload'
  | 'testflight_promote'
  | 'public_release'
  | 'mcp_write'
  | 'data_delete'
  | 'other';

export type ApprovalPriority = 'P0' | 'P1' | 'P2' | 'P3';

/** safeDefault is what happens if the gate expires unanswered. The
 *  set is intentionally narrow and biased toward inaction. */
export type ApprovalSafeDefault =
  | 'skip'           // the action does NOT run
  | 'wait'           // the gate stays pending; automation keeps polling but cannot proceed
  | 'rollback'       // a partial action is undone
  | 'notify_only';   // automation surfaces a banner and continues without the action

export type ApprovalStatus =
  | 'pending'        // awaiting Aaron decision
  | 'approved'       // Aaron approved; automation may proceed
  | 'deferred'       // Aaron deferred; the gate resurfaces after deferUntil
  | 'expired'        // expiresAt passed without decision; safeDefault applied
  | 'cancelled'      // gate withdrawn by automation (action no longer needed)
  | 'completed';     // approved + automation acted + result recorded

export interface ApprovalGate {
  id: string;
  title: string;                   // ≤ 80 chars, plain English ("Approve Android v20 Play upload")
  description: string;             // ≤ 400 chars, no secrets, what + why
  priority: ApprovalPriority;
  actionType: ApprovalActionType;
  status: ApprovalStatus;
  safeDefault: ApprovalSafeDefault;
  /** ISO timestamp the gate was opened. */
  createdAt: string;
  /** ISO timestamp the gate auto-applies its safeDefault. */
  expiresAt: string;
  /** ISO timestamp Aaron last touched the gate. null until first action. */
  resolvedAt: string | null;
  /** Free-text identifier of resolver — "Aaron iPhone admin-dev", "automation cancel", etc. */
  resolvedBy: string | null;
  /** ISO timestamp; only set when status === 'deferred'. The gate resurfaces at this time. */
  deferUntil: string | null;
  /** Optional short reason from Aaron when deferring or cancelling. ≤ 200 chars. */
  resolutionNote: string | null;
  /** Pointer to the data/action-ledger pending-actions row this gate unblocks, when applicable. */
  ledgerActionId: string | null;
  /** Free-form short payload describing the next automation step (sanitised, ≤ 400 chars). */
  actionPayload: string | null;
}

/** Result envelope for transitions. The caller is responsible for
 *  persisting `next` and recording the optional ledger note. */
export interface ApprovalTransitionResult {
  ok: boolean;
  reason: string;
  next: ApprovalGate;
  ledgerNote: string | null;
}

const TITLE_MAX = 80;
const DESCRIPTION_MAX = 400;
const PAYLOAD_MAX = 400;
const NOTE_MAX = 200;
const SECRET_PATTERNS: ReadonlyArray<RegExp> = [
  /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/,
  /\bsk-[A-Za-z0-9_-]{16,}\b/,
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bwhsec_[A-Za-z0-9]{20,}\b/,
  /\bAKIA[0-9A-Z]{16}\b/,
];

const SAFE_DEFAULTS_BY_ACTION: Record<ApprovalActionType, ReadonlySet<ApprovalSafeDefault>> = {
  eas_build:           new Set(['skip', 'wait']),
  eas_submit:          new Set(['skip', 'wait']),
  worker_deploy:       new Set(['skip', 'wait']),
  play_console_upload: new Set(['skip', 'wait']),
  testflight_promote:  new Set(['skip', 'wait']),
  public_release:      new Set(['skip']),
  mcp_write:           new Set(['skip', 'rollback', 'wait']),
  data_delete:         new Set(['skip', 'rollback']),
  other:               new Set(['skip', 'wait', 'notify_only', 'rollback']),
};

export function looksLikeSecret(value: string): boolean {
  if (!value) return false;
  return SECRET_PATTERNS.some((pattern) => pattern.test(value));
}

function trimAndCap(value: string, max: number): string {
  return value.replace(/\s+/g, ' ').trim().slice(0, max);
}

export interface ApprovalGateInput {
  id: string;
  title: string;
  description: string;
  priority: ApprovalPriority;
  actionType: ApprovalActionType;
  safeDefault: ApprovalSafeDefault;
  createdAt: string;
  expiresAt: string;
  ledgerActionId?: string | null;
  actionPayload?: string | null;
}

export function makeApprovalGate(input: ApprovalGateInput): ApprovalGate {
  const title = trimAndCap(input.title, TITLE_MAX);
  const description = trimAndCap(input.description, DESCRIPTION_MAX);
  const actionPayload = input.actionPayload != null
    ? trimAndCap(input.actionPayload, PAYLOAD_MAX)
    : null;
  if (!title) throw new Error('approval gate title required');
  if (!description) throw new Error('approval gate description required');
  if (looksLikeSecret(title) || looksLikeSecret(description) || (actionPayload != null && looksLikeSecret(actionPayload))) {
    throw new Error('approval gate fields look secret-shaped — refusing to construct');
  }
  const allowed = SAFE_DEFAULTS_BY_ACTION[input.actionType];
  if (!allowed.has(input.safeDefault)) {
    throw new Error(`safeDefault ${input.safeDefault} not allowed for actionType ${input.actionType}`);
  }
  const created = new Date(input.createdAt).getTime();
  const expires = new Date(input.expiresAt).getTime();
  if (!Number.isFinite(created) || !Number.isFinite(expires)) {
    throw new Error('approval gate createdAt/expiresAt must be parseable ISO dates');
  }
  if (expires <= created) {
    throw new Error('approval gate expiresAt must be after createdAt');
  }
  return {
    id: input.id,
    title,
    description,
    priority: input.priority,
    actionType: input.actionType,
    status: 'pending',
    safeDefault: input.safeDefault,
    createdAt: input.createdAt,
    expiresAt: input.expiresAt,
    resolvedAt: null,
    resolvedBy: null,
    deferUntil: null,
    resolutionNote: null,
    ledgerActionId: input.ledgerActionId ?? null,
    actionPayload,
  };
}

function nowIso(now: () => Date): string {
  return now().toISOString();
}

export function approveGate(
  gate: ApprovalGate,
  resolver: string,
  options: { now?: () => Date; note?: string | null } = {},
): ApprovalTransitionResult {
  const now = options.now ?? (() => new Date());
  if (gate.status !== 'pending' && gate.status !== 'deferred') {
    return {
      ok: false,
      reason: `cannot approve gate in status ${gate.status}; only pending or deferred gates may be approved`,
      next: gate,
      ledgerNote: null,
    };
  }
  const note = options.note != null ? trimAndCap(options.note, NOTE_MAX) : null;
  if (note != null && looksLikeSecret(note)) {
    return { ok: false, reason: 'resolutionNote looks secret-shaped', next: gate, ledgerNote: null };
  }
  const next: ApprovalGate = {
    ...gate,
    status: 'approved',
    resolvedAt: nowIso(now),
    resolvedBy: trimAndCap(resolver, 80),
    resolutionNote: note,
    deferUntil: null,
  };
  return {
    ok: true,
    reason: 'approved',
    next,
    ledgerNote: gate.ledgerActionId
      ? `Approval gate ${gate.id} approved by ${next.resolvedBy} at ${next.resolvedAt}; unblocks ledger action ${gate.ledgerActionId}.`
      : `Approval gate ${gate.id} approved by ${next.resolvedBy} at ${next.resolvedAt}.`,
  };
}

export function deferGate(
  gate: ApprovalGate,
  resolver: string,
  deferUntil: string,
  options: { now?: () => Date; note?: string | null } = {},
): ApprovalTransitionResult {
  const now = options.now ?? (() => new Date());
  if (gate.status !== 'pending' && gate.status !== 'deferred') {
    return { ok: false, reason: `cannot defer gate in status ${gate.status}`, next: gate, ledgerNote: null };
  }
  const deferAt = new Date(deferUntil).getTime();
  if (!Number.isFinite(deferAt)) {
    return { ok: false, reason: 'deferUntil must be a parseable ISO date', next: gate, ledgerNote: null };
  }
  const expiresAt = new Date(gate.expiresAt).getTime();
  if (deferAt >= expiresAt) {
    return { ok: false, reason: 'deferUntil must be before expiresAt', next: gate, ledgerNote: null };
  }
  const note = options.note != null ? trimAndCap(options.note, NOTE_MAX) : null;
  if (note != null && looksLikeSecret(note)) {
    return { ok: false, reason: 'resolutionNote looks secret-shaped', next: gate, ledgerNote: null };
  }
  const next: ApprovalGate = {
    ...gate,
    status: 'deferred',
    resolvedAt: nowIso(now),
    resolvedBy: trimAndCap(resolver, 80),
    resolutionNote: note,
    deferUntil,
  };
  return {
    ok: true,
    reason: 'deferred',
    next,
    ledgerNote: `Approval gate ${gate.id} deferred by ${next.resolvedBy} until ${deferUntil}.`,
  };
}

export function cancelGate(
  gate: ApprovalGate,
  resolver: string,
  options: { now?: () => Date; note?: string | null } = {},
): ApprovalTransitionResult {
  const now = options.now ?? (() => new Date());
  if (gate.status === 'completed' || gate.status === 'cancelled') {
    return { ok: false, reason: `cannot cancel gate in status ${gate.status}`, next: gate, ledgerNote: null };
  }
  const note = options.note != null ? trimAndCap(options.note, NOTE_MAX) : null;
  if (note != null && looksLikeSecret(note)) {
    return { ok: false, reason: 'resolutionNote looks secret-shaped', next: gate, ledgerNote: null };
  }
  const next: ApprovalGate = {
    ...gate,
    status: 'cancelled',
    resolvedAt: nowIso(now),
    resolvedBy: trimAndCap(resolver, 80),
    resolutionNote: note,
  };
  return {
    ok: true,
    reason: 'cancelled',
    next,
    ledgerNote: `Approval gate ${gate.id} cancelled by ${next.resolvedBy}.`,
  };
}

export function completeGate(
  gate: ApprovalGate,
  resolver: string,
  options: { now?: () => Date; note?: string | null } = {},
): ApprovalTransitionResult {
  if (gate.status !== 'approved') {
    return { ok: false, reason: `cannot complete gate in status ${gate.status}; gate must be approved first`, next: gate, ledgerNote: null };
  }
  const now = options.now ?? (() => new Date());
  const note = options.note != null ? trimAndCap(options.note, NOTE_MAX) : null;
  if (note != null && looksLikeSecret(note)) {
    return { ok: false, reason: 'resolutionNote looks secret-shaped', next: gate, ledgerNote: null };
  }
  const next: ApprovalGate = {
    ...gate,
    status: 'completed',
    resolvedAt: nowIso(now),
    resolvedBy: trimAndCap(resolver, 80),
    resolutionNote: note,
  };
  return {
    ok: true,
    reason: 'completed',
    next,
    ledgerNote: `Approval gate ${gate.id} completed by ${next.resolvedBy} at ${next.resolvedAt}.`,
  };
}

/** Apply expiry: pending gates past expiresAt move to status 'expired'
 *  and document the safeDefault decision. Idempotent. */
export function expireIfDue(
  gate: ApprovalGate,
  options: { now?: () => Date } = {},
): ApprovalTransitionResult {
  const now = options.now ?? (() => new Date());
  if (gate.status !== 'pending' && gate.status !== 'deferred') {
    return { ok: false, reason: 'no-op: only pending/deferred gates can expire', next: gate, ledgerNote: null };
  }
  const at = now().getTime();
  const expiresAt = new Date(gate.expiresAt).getTime();
  if (!Number.isFinite(expiresAt) || at < expiresAt) {
    return { ok: false, reason: 'not yet expired', next: gate, ledgerNote: null };
  }
  const next: ApprovalGate = {
    ...gate,
    status: 'expired',
    resolvedAt: nowIso(now),
    resolvedBy: 'system:expiry',
    resolutionNote: `safeDefault=${gate.safeDefault} applied`,
    deferUntil: null,
  };
  return {
    ok: true,
    reason: `expired; safeDefault=${gate.safeDefault} applied`,
    next,
    ledgerNote: `Approval gate ${gate.id} expired at ${next.resolvedAt}; safeDefault=${gate.safeDefault} applied.`,
  };
}

export function isActionable(gate: ApprovalGate): boolean {
  return gate.status === 'pending' || (gate.status === 'deferred' && gate.deferUntil != null && new Date(gate.deferUntil).getTime() <= Date.now());
}

export * from './spend';
export * from './spend-prechecks';
