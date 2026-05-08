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
  recommendedNextPrompt?: string | null;
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
  /** 0..100 integer progress, or null for "unknown". */
  progressPct: number | null;
  /** Server-provided next prompt recommendation, or null. */
  recommendedNextPrompt: string | null;
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
    const taskSummary = typeof agent.taskSummary === 'string' && agent.taskSummary.length > 0
      ? agent.taskSummary
      : null;
    return {
      id,
      status,
      ageMs,
      ageLabel: ageLabel(ageMs),
      freshness,
      progressPct,
      recommendedNextPrompt,
      taskSummary,
    };
  });

  return {
    source: 'mcp',
    snapshotFreshness,
    snapshotStaleReason,
    lanes,
  };
}
