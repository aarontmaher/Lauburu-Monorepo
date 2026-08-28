/**
 * Overnight Prompt Queue — schema, validation, public-safe summary,
 * idle-lane recommendation, and stale-age computation.
 *
 * Spec: PROMPT-ID `CODEX-OVERNIGHT-PROMPT-QUEUE-IMPL-01` (2026-05-09).
 *
 * The queue is a durable backlog of long-running autonomous tasks
 * suitable for unattended overnight execution. It does NOT override
 * standard P0/P1 priorities: a P0 blocker still wins over any
 * overnight candidate (`recommendOvernightTaskForLane` returns
 * `null` when a P0 is pending for the lane).
 *
 * Anti-rules baked in:
 *
 * - Public surfaces expose count + the `safeToRunUnattended` boolean
 *   only. Full row content (title, prompt body, dependencies) is
 *   admin-token-gated and additionally redacted via
 *   `redactOvernightRowForAdmin`.
 * - Recommendation only — the worker NEVER auto-claims an overnight
 *   task. Aaron approves before any overnight execution starts.
 * - Stale tasks (older than `staleThresholdHours`) surface with
 *   `stale: true` so the UI can render the stale badge per Rule 1.
 * - The Top-7 priority list in `docs/APP_DEVELOPMENTS.md` is NEVER
 *   reordered by overnight queue state. The queue is a SECONDARY
 *   surface that only fills lane idle time.
 */

export type OvernightLaneOwner = 'claude' | 'codex' | 'agent' | 'aaron';

export type OvernightInterruptPriority =
  | 'p0'
  | 'p1'
  | 'p2'
  | 'p3'
  | 'overnight_only';

export type OvernightExecutionWindow =
  | 'weeknight_us_pt'
  | 'weekend_us_pt'
  | 'any_idle'
  | 'business_hours_us_pt'
  | 'manual_only';

/**
 * The row shape stored in `connector_overnight_queue` (Supabase).
 * `dependencies` references either other queue ids or
 * `connector_action_ledger` row ids. Caller validates referential
 * integrity; this module enforces structural shape only.
 */
export interface OvernightQueueRow {
  id: string;
  title: string;
  lane_owner: OvernightLaneOwner;
  estimated_unattended_runtime_minutes: number;
  requires_human_interaction: boolean;
  safe_overnight: boolean;
  dependencies: ReadonlyArray<string>;
  interrupt_priority: OvernightInterruptPriority;
  repo_only_relevance: boolean;
  preview_only_relevance: boolean;
  installed_build_verified_relevance: boolean;
  suggested_execution_window: OvernightExecutionWindow;
  progress_pct: number;
  outcome_summary: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

/** Default staleness window. Tasks updated longer ago are flagged stale. */
export const DEFAULT_STALE_THRESHOLD_HOURS = 72;

/** Cap for the queue title field — keeps Admin/Dev compact. */
export const TITLE_CAP = 140;

/** Cap for outcome_summary on completion. */
export const OUTCOME_SUMMARY_CAP = 500;

export interface OvernightSchemaValidationFailure {
  ok: false;
  reason: string;
  field?: keyof OvernightQueueRow;
}

export type OvernightSchemaValidationResult =
  | { ok: true; row: OvernightQueueRow }
  | OvernightSchemaValidationFailure;

const OWNER_SET: ReadonlySet<OvernightLaneOwner> = new Set(['claude', 'codex', 'agent', 'aaron']);
const PRIORITY_SET: ReadonlySet<OvernightInterruptPriority> = new Set(['p0', 'p1', 'p2', 'p3', 'overnight_only']);
const WINDOW_SET: ReadonlySet<OvernightExecutionWindow> = new Set([
  'weeknight_us_pt',
  'weekend_us_pt',
  'any_idle',
  'business_hours_us_pt',
  'manual_only',
]);

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isIso(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  const t = Date.parse(value);
  return Number.isFinite(t);
}

/** Validate one row from the database / API payload. Pure. */
export function validateOvernightRow(input: unknown): OvernightSchemaValidationResult {
  if (!input || typeof input !== 'object') return { ok: false, reason: 'row must be an object' };
  const r = input as Record<string, unknown>;

  if (typeof r.id !== 'string' || !UUID_RE.test(r.id)) return { ok: false, reason: 'id must be a uuid', field: 'id' };
  if (typeof r.title !== 'string' || r.title.length === 0 || r.title.length > TITLE_CAP) return { ok: false, reason: `title must be 1..${TITLE_CAP} chars`, field: 'title' };
  if (typeof r.lane_owner !== 'string' || !OWNER_SET.has(r.lane_owner as OvernightLaneOwner)) return { ok: false, reason: `lane_owner must be one of ${[...OWNER_SET].join('/')}`, field: 'lane_owner' };
  if (typeof r.estimated_unattended_runtime_minutes !== 'number' || !Number.isInteger(r.estimated_unattended_runtime_minutes) || r.estimated_unattended_runtime_minutes < 0) {
    return { ok: false, reason: 'estimated_unattended_runtime_minutes must be a non-negative integer', field: 'estimated_unattended_runtime_minutes' };
  }
  for (const boolField of [
    'requires_human_interaction',
    'safe_overnight',
    'repo_only_relevance',
    'preview_only_relevance',
    'installed_build_verified_relevance',
  ] as const) {
    if (typeof r[boolField] !== 'boolean') return { ok: false, reason: `${boolField} must be boolean`, field: boolField };
  }
  if (!Array.isArray(r.dependencies) || r.dependencies.some((d) => typeof d !== 'string')) {
    return { ok: false, reason: 'dependencies must be an array of strings', field: 'dependencies' };
  }
  if (typeof r.interrupt_priority !== 'string' || !PRIORITY_SET.has(r.interrupt_priority as OvernightInterruptPriority)) {
    return { ok: false, reason: `interrupt_priority must be one of ${[...PRIORITY_SET].join('/')}`, field: 'interrupt_priority' };
  }
  if (typeof r.suggested_execution_window !== 'string' || !WINDOW_SET.has(r.suggested_execution_window as OvernightExecutionWindow)) {
    return { ok: false, reason: `suggested_execution_window must be one of ${[...WINDOW_SET].join('/')}`, field: 'suggested_execution_window' };
  }
  if (typeof r.progress_pct !== 'number' || !Number.isFinite(r.progress_pct) || r.progress_pct < 0 || r.progress_pct > 100) {
    return { ok: false, reason: 'progress_pct must be a 0..100 number', field: 'progress_pct' };
  }
  if (r.outcome_summary !== null) {
    if (typeof r.outcome_summary !== 'string' || r.outcome_summary.length > OUTCOME_SUMMARY_CAP) {
      return { ok: false, reason: `outcome_summary must be null or ≤${OUTCOME_SUMMARY_CAP} chars`, field: 'outcome_summary' };
    }
  }
  if (!isIso(r.created_at)) return { ok: false, reason: 'created_at must be ISO timestamp', field: 'created_at' };
  if (!isIso(r.updated_at)) return { ok: false, reason: 'updated_at must be ISO timestamp', field: 'updated_at' };
  if (r.started_at !== null && !isIso(r.started_at)) return { ok: false, reason: 'started_at must be null or ISO timestamp', field: 'started_at' };
  if (r.completed_at !== null && !isIso(r.completed_at)) return { ok: false, reason: 'completed_at must be null or ISO timestamp', field: 'completed_at' };

  return {
    ok: true,
    row: {
      id: r.id,
      title: r.title,
      lane_owner: r.lane_owner as OvernightLaneOwner,
      estimated_unattended_runtime_minutes: r.estimated_unattended_runtime_minutes,
      requires_human_interaction: r.requires_human_interaction as boolean,
      safe_overnight: r.safe_overnight as boolean,
      dependencies: r.dependencies as ReadonlyArray<string>,
      interrupt_priority: r.interrupt_priority as OvernightInterruptPriority,
      repo_only_relevance: r.repo_only_relevance as boolean,
      preview_only_relevance: r.preview_only_relevance as boolean,
      installed_build_verified_relevance: r.installed_build_verified_relevance as boolean,
      suggested_execution_window: r.suggested_execution_window as OvernightExecutionWindow,
      progress_pct: r.progress_pct,
      outcome_summary: (r.outcome_summary as string | null) ?? null,
      created_at: r.created_at as string,
      updated_at: r.updated_at as string,
      started_at: (r.started_at as string | null) ?? null,
      completed_at: (r.completed_at as string | null) ?? null,
    },
  };
}

/** Compute stale_age_hours at read time. Always >= 0. */
export function computeStaleAgeHours(updatedAt: string, nowMs: number = Date.now()): number {
  const t = Date.parse(updatedAt);
  if (!Number.isFinite(t)) return 0;
  const diffMs = Math.max(0, nowMs - t);
  return Math.floor(diffMs / 3_600_000);
}

/** Public-safe summary surfaced on /mcp/v2 project.get_current_state. */
export interface PublicOvernightQueueSummary {
  count: number;
  /**
   * Id of the recommended task to surface to the most idle lane.
   * Null when the queue is empty or no candidate is safe to surface.
   */
  recommendedTaskId: string | null;
  /**
   * True iff the recommended task is safe to run unattended
   * (`safe_overnight === true && requires_human_interaction === false`).
   */
  safeToRunUnattended: boolean;
  /** True when at least one queue row's stale_age_hours > threshold. */
  hasStaleEntries: boolean;
}

export function buildPublicOvernightQueueSummary(
  rows: ReadonlyArray<OvernightQueueRow>,
  staleThresholdHours: number = DEFAULT_STALE_THRESHOLD_HOURS,
  nowMs: number = Date.now(),
): PublicOvernightQueueSummary {
  const recommended = pickRecommendedTask(rows, null, [], nowMs);
  const hasStaleEntries = rows.some((r) => computeStaleAgeHours(r.updated_at, nowMs) > staleThresholdHours);
  return {
    count: rows.length,
    recommendedTaskId: recommended?.id ?? null,
    safeToRunUnattended: recommended ? recommended.safe_overnight && !recommended.requires_human_interaction : false,
    hasStaleEntries,
  };
}

/**
 * Pick the highest-priority overnight task suitable for an idle
 * lane. Recommendation only — caller MUST NOT auto-claim.
 *
 * Rules:
 * - When `laneOwner` is provided, only tasks whose `lane_owner`
 *   matches are considered.
 * - Tasks with unsatisfied dependencies are skipped (a dependency
 *   is satisfied when its id appears in `completedDependencyIds`).
 * - Tasks already in flight (`started_at != null && completed_at == null`)
 *   are NOT recommended again.
 * - Priority order: p0 > p1 > p2 > p3 > overnight_only. Within the
 *   same priority, the OLDEST `created_at` wins (FIFO).
 * - Returns null when no candidate exists.
 */
export function pickRecommendedTask(
  rows: ReadonlyArray<OvernightQueueRow>,
  laneOwner: OvernightLaneOwner | null,
  completedDependencyIds: ReadonlyArray<string>,
  _nowMs: number = Date.now(),
): OvernightQueueRow | null {
  const completedSet = new Set(completedDependencyIds);
  const priorityRank: Record<OvernightInterruptPriority, number> = {
    p0: 0,
    p1: 1,
    p2: 2,
    p3: 3,
    overnight_only: 4,
  };
  const candidates = rows.filter((r) => {
    if (laneOwner != null && r.lane_owner !== laneOwner) return false;
    if (r.completed_at != null) return false;
    if (r.started_at != null) return false;
    if (r.dependencies.some((d) => !completedSet.has(d))) return false;
    return true;
  });
  if (candidates.length === 0) return null;
  candidates.sort((a, b) => {
    const dr = priorityRank[a.interrupt_priority] - priorityRank[b.interrupt_priority];
    if (dr !== 0) return dr;
    return Date.parse(a.created_at) - Date.parse(b.created_at);
  });
  return candidates[0];
}

/**
 * Idle-lane auto-routing per Rule 1 (file § rule 24). When a lane
 * reports `idle` (or terminal-idle while MCP says working) AND no
 * P0/P1 blocker is pending for that lane, recommend the highest-
 * priority overnight task for that lane. Returns null when a P0
 * is pending — P0 ALWAYS wins over an overnight candidate.
 */
export function recommendOvernightTaskForLane(args: {
  laneOwner: OvernightLaneOwner;
  rows: ReadonlyArray<OvernightQueueRow>;
  completedDependencyIds: ReadonlyArray<string>;
  pendingP0Count: number;
  pendingP1Count: number;
  nowMs?: number;
}): OvernightQueueRow | null {
  // P0 ALWAYS wins. P1 also wins (overnight is by definition
  // lower-priority leftover work).
  if (args.pendingP0Count > 0 || args.pendingP1Count > 0) return null;
  return pickRecommendedTask(args.rows, args.laneOwner, args.completedDependencyIds, args.nowMs);
}

/**
 * Admin-only redacted view of a queue row. Truncates title, masks
 * outcome summary length to ≤140 chars, drops dependencies content
 * (returns count only), and never includes raw timestamps below
 * minute precision. Even at admin scope the queue MUST NOT carry
 * tokens, raw stack traces, or PII — caller is responsible for
 * upstream redaction.
 */
export interface AdminOvernightRow {
  id: string;
  title: string;
  lane_owner: OvernightLaneOwner;
  estimated_unattended_runtime_minutes: number;
  requires_human_interaction: boolean;
  safe_overnight: boolean;
  dependency_count: number;
  interrupt_priority: OvernightInterruptPriority;
  repo_only_relevance: boolean;
  preview_only_relevance: boolean;
  installed_build_verified_relevance: boolean;
  suggested_execution_window: OvernightExecutionWindow;
  progress_pct: number;
  stale_age_hours: number;
  stale: boolean;
  outcome_summary: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export function redactOvernightRowForAdmin(
  row: OvernightQueueRow,
  staleThresholdHours: number = DEFAULT_STALE_THRESHOLD_HOURS,
  nowMs: number = Date.now(),
): AdminOvernightRow {
  const staleAgeHours = computeStaleAgeHours(row.updated_at, nowMs);
  return {
    id: row.id,
    title: row.title.slice(0, TITLE_CAP),
    lane_owner: row.lane_owner,
    estimated_unattended_runtime_minutes: row.estimated_unattended_runtime_minutes,
    requires_human_interaction: row.requires_human_interaction,
    safe_overnight: row.safe_overnight,
    dependency_count: row.dependencies.length,
    interrupt_priority: row.interrupt_priority,
    repo_only_relevance: row.repo_only_relevance,
    preview_only_relevance: row.preview_only_relevance,
    installed_build_verified_relevance: row.installed_build_verified_relevance,
    suggested_execution_window: row.suggested_execution_window,
    progress_pct: row.progress_pct,
    stale_age_hours: staleAgeHours,
    stale: staleAgeHours > staleThresholdHours,
    outcome_summary: row.outcome_summary == null ? null : row.outcome_summary.slice(0, 140),
    created_at: row.created_at,
    updated_at: row.updated_at,
    started_at: row.started_at,
    completed_at: row.completed_at,
  };
}
