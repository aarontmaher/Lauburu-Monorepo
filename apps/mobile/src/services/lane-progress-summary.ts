/**
 * Pure summariser for the Admin/Dev lane progress strip. Maps an
 * MCP `project.get_current_state` payload to a small per-lane
 * shape the UI can render directly: status, age, fresh/stale
 * badge, progress percentage (or "unknown"), and a recommended
 * next prompt target if the MCP server provided one.
 *
 * Anti-rules:
 *
 * - **Never fabricate progress.** Missing or non-finite progress
 *   percentages render as null → UI displays "unknown". Returning
 *   0% would falsely imply the lane has not started.
 * - **Never invent a recommended next prompt.** The text is taken
 *   verbatim from the server payload; missing → null → UI "—".
 * - **Stale wins over fresh.** A lane is stale when the MCP
 *   freshness payload is stale, OR when the lane's own age
 *   exceeds `LANE_FRESH_WINDOW_MS`. The UI never colours a stale
 *   lane as fresh.
 * - **Unavailable is distinct.** When the snapshot is null or has
 *   no agents, the summary returns `{ source: 'unavailable' }`
 *   and the UI renders an explicit "MCP unavailable" affordance
 *   instead of an empty strip (which the older Admin/Dev tab
 *   confusingly showed as "lanes 0").
 */

export interface McpLaneProgressInputAgent {
  id?: string | null;
  status?: string | null;
  taskSummary?: string | null;
  lastCommit?: string | null;
  updatedAt?: string | null;
  lastSeenAt?: string | null;
  progressPct?: number | null;
  /**
   * Free-form recommendation. Treated as `recommendedNextPromptText`
   * when present. Non-empty server payloads win over the defaulted
   * "queue a prompt" placeholder. Never fabricated client-side.
   */
  recommendedNextPrompt?: string | null;
  /** Server-emitted next-prompt target (lane id). When missing, the lane's own id is used. */
  recommendedNextPromptTarget?: string | null;
  /** Server-emitted ≤140 char summary (preferred over recommendedNextPrompt for badges). */
  recommendedNextPromptSummary?: string | null;
  /**
   * Optional `terminalIdleAt` ISO timestamp the bridge can populate
   * when terminal evidence shows the lane is actually idle even
   * though MCP `status` may still read 'working'. Rule 1 in
   * `docs/OPERATING_RULES.md` requires terminal truth to win.
   */
  terminalIdleAt?: string | null;
}

export interface McpLaneProgressInput {
  source?: string | null;
  freshness?: {
    isStale?: boolean;
    staleReason?: string;
    updatedAt?: string | null;
    ageMs?: number | null;
  } | null;
  agents?: ReadonlyArray<McpLaneProgressInputAgent> | null;
}

export type LaneFreshness = 'fresh' | 'stale' | 'unknown';

/**
 * Canonical idle-status enum for Rule 1 / Rule 24. UI rendering and
 * MCP/control-centre summaries MUST emit one of these values; a
 * lane is treated as needing a recommended next prompt when its
 * idleStatus is anything other than 'working'.
 */
export type IdleStatus =
  | 'working'
  | 'idle'
  | 'stale'
  | 'blocked'
  | 'needs_user'
  | 'needs_review'
  | 'complete_waiting_approval'
  | 'unknown';

export interface LaneProgressEntry {
  /** Lane id (claude/codex/agent/…) — falls back to 'lane' when missing. */
  id: string;
  /** Lane status string from the MCP payload, lowercased. 'unknown' when missing. */
  status: string;
  /** Age of the lane's last update in ms; null when no timestamp. */
  ageMs: number | null;
  /** Compact human-readable age, e.g. "12s", "3m", "—". */
  ageLabel: string;
  /** Fresh / stale / unknown — never 'fresh' when the MCP payload itself is stale. */
  freshness: LaneFreshness;
  /**
   * Canonical idle status per Rule 1 (file § rule 24). Emits one of
   * the `IdleStatus` values. When the bridge has flagged the lane
   * as terminal-idle (terminalIdleAt set) AND MCP says 'working',
   * idleStatus collapses to 'idle' so a stale 'working' cannot
   * suppress a recommended-next-prompt.
   */
  idleStatus: IdleStatus;
  /** True when this lane should receive a recommended-next-prompt. Per Rule 1, idleStatus !== 'working'. */
  needsPrompt: boolean;
  /** 0..100 integer progress, or null for "unknown". */
  progressPct: number | null;
  /** Server-provided next prompt recommendation, or null. */
  recommendedNextPrompt: string | null;
  /** Per Rule 1: lane id the recommended prompt should target. Defaults to the lane's own id. */
  recommendedNextPromptTarget: string;
  /** Per Rule 1: ≤140 char summary; null when MCP did not emit one. */
  recommendedNextPromptSummary: string | null;
  /** Short task summary from MCP, or null. */
  taskSummary: string | null;
}

export interface LaneProgressSummary {
  source: 'mcp' | 'unavailable';
  /** Snapshot-level freshness — lanes inherit this when stale. */
  snapshotFreshness: LaneFreshness;
  /** Snapshot stale reason (if any). */
  snapshotStaleReason: string | null;
  /** Per-lane entries, in input order. */
  lanes: LaneProgressEntry[];
  /**
   * Per-lane Rule 1 enforcement payload — every lane that needs a
   * prompt according to Rule 1 is listed here. Empty when every
   * lane is `working`. Each entry carries the four canonical
   * fields the spec requires, with `unknown` placeholders when
   * MCP did not yet emit a recommendation. UI MUST render every
   * entry as an immediate "queue a prompt" affordance.
   */
  promptsRequired: Array<{
    laneId: string;
    idleStatus: IdleStatus;
    recommendedNextPromptTarget: string;
    recommendedNextPromptText: string | null;
    recommendedNextPromptSummary: string | null;
    promptProgressPercent: number | 'unknown';
  }>;
}

/** Lanes whose `lastSeenAt` is older than this are considered stale. */
export const LANE_FRESH_WINDOW_MS = 90_000;

function ageLabel(ms: number | null): string {
  if (ms == null || !Number.isFinite(ms) || ms < 0) return '—';
  if (ms < 1_000) return '<1s';
  if (ms < 60_000) return `${Math.floor(ms / 1_000)}s`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h`;
  return `${Math.floor(ms / 86_400_000)}d`;
}

function ageMsFromIso(iso: string | null | undefined, nowMs: number): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return null;
  const ms = nowMs - t;
  return ms >= 0 ? ms : null;
}

/**
 * Sanitise a progress value to either an integer in [0..100] or
 * null. Falsy / non-finite / out-of-range inputs return null so
 * the UI renders "unknown" rather than a misleading 0% bar.
 */
export function sanitiseProgressPct(value: unknown): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  if (value < 0 || value > 100) return null;
  return Math.round(value);
}

/**
 * The canonical idle-state set Rule 1 (file § rule 24) requires a
 * recommended next prompt for. Anything outside this set + 'working'
 * collapses to 'unknown'.
 */
const IDLE_STATUSES: ReadonlySet<IdleStatus> = new Set([
  'idle',
  'stale',
  'blocked',
  'needs_user',
  'needs_review',
  'complete_waiting_approval',
]);

function coerceIdleStatus(raw: string): IdleStatus {
  if (raw === 'working' || raw === 'in_progress' || raw === 'in-progress') return 'working';
  if (IDLE_STATUSES.has(raw as IdleStatus)) return raw as IdleStatus;
  return 'unknown';
}

export function summariseLaneProgress(
  input: McpLaneProgressInput | null | undefined,
  nowMs: number = Date.now(),
): LaneProgressSummary {
  if (!input || !Array.isArray(input.agents) || input.agents.length === 0) {
    return {
      source: 'unavailable',
      snapshotFreshness: 'unknown',
      snapshotStaleReason: null,
      lanes: [],
      promptsRequired: [],
    };
  }
  const snapshotStale = input.freshness?.isStale === true;
  const snapshotStaleReason = snapshotStale
    ? (typeof input.freshness?.staleReason === 'string' && input.freshness.staleReason.length > 0
        ? input.freshness.staleReason
        : 'unknown')
    : null;
  const snapshotFreshness: LaneFreshness = snapshotStale ? 'stale' : 'fresh';

  const lanes: LaneProgressEntry[] = input.agents.map((agent) => {
    const id = typeof agent.id === 'string' && agent.id.length > 0 ? agent.id : 'lane';
    const status = typeof agent.status === 'string' && agent.status.length > 0
      ? agent.status.toLowerCase()
      : 'unknown';
    const lastSeenAgeMs = ageMsFromIso(agent.lastSeenAt, nowMs);
    const updatedAgeMs = ageMsFromIso(agent.updatedAt, nowMs);
    // Use whichever timestamp gives the smaller (= more recent) age.
    const candidates = [lastSeenAgeMs, updatedAgeMs].filter((v): v is number => typeof v === 'number');
    const ageMs = candidates.length > 0 ? Math.min(...candidates) : null;
    const laneStaleByAge = ageMs != null && ageMs > LANE_FRESH_WINDOW_MS;
    const freshness: LaneFreshness = snapshotStale
      ? 'stale'
      : ageMs == null
        ? 'unknown'
        : laneStaleByAge
          ? 'stale'
          : 'fresh';
    const progressPct = sanitiseProgressPct(agent.progressPct);
    const recommendedNextPrompt = typeof agent.recommendedNextPrompt === 'string'
      && agent.recommendedNextPrompt.trim().length > 0
      ? agent.recommendedNextPrompt
      : null;
    const recommendedNextPromptTarget = typeof agent.recommendedNextPromptTarget === 'string'
      && agent.recommendedNextPromptTarget.trim().length > 0
      ? agent.recommendedNextPromptTarget.trim()
      : id;
    const recommendedNextPromptSummary = typeof agent.recommendedNextPromptSummary === 'string'
      && agent.recommendedNextPromptSummary.trim().length > 0
      ? agent.recommendedNextPromptSummary.trim().slice(0, 140)
      : null;
    const taskSummary = typeof agent.taskSummary === 'string' && agent.taskSummary.length > 0
      ? agent.taskSummary
      : null;

    // Rule 1: terminal truth wins. If the bridge says the lane is
    // terminal-idle (terminalIdleAt is set) but MCP `status` still
    // reads 'working', treat the lane as idle so the recommended-
    // next-prompt fires. Otherwise honour MCP `status`.
    let idleStatus = coerceIdleStatus(status);
    const terminalIdleHasTimestamp = typeof agent.terminalIdleAt === 'string' && agent.terminalIdleAt.length > 0;
    if (terminalIdleHasTimestamp && idleStatus === 'working') {
      idleStatus = 'idle';
    }
    // Lanes with a stale-by-age reading collapse to 'stale' so the
    // UI cannot show a green-fresh badge while terminal evidence
    // says the lane has not heart-beat in over a minute.
    if (idleStatus === 'working' && (snapshotStale || laneStaleByAge)) {
      idleStatus = 'stale';
    }

    const needsPrompt = idleStatus !== 'working';

    return {
      id,
      status,
      ageMs,
      ageLabel: ageLabel(ageMs),
      freshness,
      idleStatus,
      needsPrompt,
      progressPct,
      recommendedNextPrompt,
      recommendedNextPromptTarget,
      recommendedNextPromptSummary,
      taskSummary,
    };
  });

  const promptsRequired = lanes
    .filter((lane) => lane.needsPrompt)
    .map((lane) => ({
      laneId: lane.id,
      idleStatus: lane.idleStatus,
      recommendedNextPromptTarget: lane.recommendedNextPromptTarget,
      recommendedNextPromptText: lane.recommendedNextPrompt,
      recommendedNextPromptSummary: lane.recommendedNextPromptSummary,
      promptProgressPercent: lane.progressPct == null ? ('unknown' as const) : lane.progressPct,
    }));

  return {
    source: 'mcp',
    snapshotFreshness,
    snapshotStaleReason,
    lanes,
    promptsRequired,
  };
}
