/**
 * Pure decision layer for the Samsung phone Admin/Dev controller.
 *
 * Given a snapshot of MCP/lane/approval state, returns the set of
 * notifications that should fire NOW. Honest by construction:
 *
 *   - never fabricates a "completion" — only categories the caller
 *     supplies explicit evidence for (e.g. installedDeviceQaPending)
 *     can fire;
 *   - never claims live status — every decision carries a
 *     ControllerEvidenceLabel so the UI / push channel renders
 *     repo-only / preview-only / live-now correctly;
 *   - every body includes the current top priority and the
 *     recommended next action where the caller supplies them, so
 *     Aaron sees the same string on the lock screen as in the
 *     Admin/Dev "Now" tile;
 *   - dedupeKey is stable per (category, lane, freshness) so
 *     repeated polls do not respawn the same notification.
 *
 * The module imports nothing from React Native, expo, or zustand,
 * so it is unit-testable in plain Node.
 */
import type { AndroidControllerContext } from './android-controller-context';
import type { LaneProgressSummary, IdleStatus } from './lane-progress-summary';
import type { ControllerEvidenceLabel } from './controller-overview-client';

export type ControllerNotificationCategory =
  | 'idle_lane'
  | 'all_lanes_idle'
  | 'lane_blocked'
  | 'approval_needed'
  | 'mcp_stale'
  | 'installed_device_qa_needed';

/** Stable order so the UI / store iterate decisions deterministically. */
const CATEGORY_PRIORITY: ControllerNotificationCategory[] = [
  'mcp_stale',
  'lane_blocked',
  'approval_needed',
  'installed_device_qa_needed',
  'all_lanes_idle',
  'idle_lane',
];

export interface ControllerNotificationDecision {
  category: ControllerNotificationCategory;
  /** Stable per (category, lane, freshness slice) — store uses this to suppress duplicates. */
  dedupeKey: string;
  /** ≤ 60 char title. Public-safe — no secrets, no raw logs. */
  title: string;
  /** ≤ 240 char body. Includes top priority + recommended next action when supplied. */
  body: string;
  evidenceLabel: ControllerEvidenceLabel;
  /** The current top priority surfaced into this decision (verbatim, ≤ 120 chars). */
  topPriority: string | null;
  /** The recommended next action (verbatim, ≤ 200 chars). null when unknown. */
  recommendedNextAction: string | null;
  /** Optional lane id this decision is anchored to. */
  laneId: string | null;
}

export interface DecisionInput {
  /** Mapped controller context (output of buildAndroidControllerContext). null on iOS / non-admin. */
  context: AndroidControllerContext | null;
  /** Per-lane summary used to detect idle / blocked / needs-user. */
  laneSummary: LaneProgressSummary;
  /** Pending approval gates count (status === 'pending'). */
  approvalsPending: number;
  /** Caller asserts installed-device QA is required (e.g. evidence labelled mirror-only). */
  installedDeviceQaPending: boolean;
  /** Top priority string from MCP / connector. */
  topPriority: string | null;
  /** Recommended next action string from MCP / connector. */
  recommendedNextAction: string | null;
  /** Now timestamp for deterministic dedupeKey slicing. */
  nowMs?: number;
}

const IDLE_BLOCKED: ReadonlySet<IdleStatus> = new Set([
  'blocked',
  'needs_user',
  'needs_review',
  'complete_waiting_approval',
]);

const IDLE_IDLE: ReadonlySet<IdleStatus> = new Set(['idle', 'stale']);

const PRIMARY_LANES = ['claude', 'codex', 'agent'] as const;

function clampText(value: string | null | undefined, max: number): string | null {
  if (typeof value !== 'string') return null;
  const compact = value.replace(/\s+/g, ' ').trim();
  if (compact.length === 0) return null;
  return compact.length > max ? compact.slice(0, max) : compact;
}

function joinBody(parts: Array<string | null | undefined>, max = 240): string {
  const compact = parts
    .filter((p): p is string => typeof p === 'string' && p.trim().length > 0)
    .map((p) => p.trim())
    .join(' · ');
  return compact.length > max ? compact.slice(0, max) : compact;
}

/**
 * Bucket the dedupeKey by 5-minute slice so a stale state that
 * persists across two foreground refreshes does not re-spawn the
 * same notification, but a stale state that persists for an hour
 * does remind the user a few times.
 */
function dedupeSlice(nowMs: number): string {
  const slice = Math.floor(nowMs / (5 * 60 * 1000));
  return String(slice);
}

export function decideControllerNotifications(input: DecisionInput): ControllerNotificationDecision[] {
  const decisions: ControllerNotificationDecision[] = [];
  const nowMs = typeof input.nowMs === 'number' && Number.isFinite(input.nowMs) ? input.nowMs : Date.now();
  const slice = dedupeSlice(nowMs);
  const topPriority = clampText(input.topPriority, 120);
  const recommendedNextAction = clampText(input.recommendedNextAction, 200);
  const ctx = input.context;

  // 1. MCP stale — fires when MCP freshness is stale OR missing.
  if (ctx) {
    if (ctx.mcp.freshness === 'stale' || ctx.mcp.freshness === 'missing') {
      const reason = clampText(ctx.mcp.staleReason, 80) ?? (ctx.mcp.freshness === 'missing' ? 'no writeback received' : 'writeback older than freshness window');
      decisions.push({
        category: 'mcp_stale',
        dedupeKey: `mcp_stale|${ctx.mcp.freshness}|${slice}`,
        title: `MCP ${ctx.mcp.freshness}`,
        body: joinBody([
          `MCP writeback ${ctx.mcp.freshness}`,
          reason,
          topPriority ? `Priority: ${topPriority}` : null,
          recommendedNextAction ? `Next: ${recommendedNextAction}` : null,
        ]),
        evidenceLabel: 'repo-only',
        topPriority,
        recommendedNextAction,
        laneId: null,
      });
    }
  }

  // 2. Lane blocked / needs-user — one decision per blocked primary lane.
  for (const lane of input.laneSummary.lanes) {
    if (!IDLE_BLOCKED.has(lane.idleStatus)) continue;
    const isPrimary = PRIMARY_LANES.includes(lane.id as (typeof PRIMARY_LANES)[number]);
    decisions.push({
      category: 'lane_blocked',
      dedupeKey: `lane_blocked|${lane.id}|${lane.idleStatus}|${slice}`,
      title: `${lane.id} ${lane.idleStatus}`,
      body: joinBody([
        `Lane ${lane.id} is ${lane.idleStatus}`,
        lane.recommendedNextPromptSummary,
        isPrimary && recommendedNextAction ? `Next: ${recommendedNextAction}` : null,
      ]),
      evidenceLabel: 'repo-only',
      topPriority,
      recommendedNextAction: lane.recommendedNextPromptSummary ?? recommendedNextAction,
      laneId: lane.id,
    });
  }

  // 3. Approval needed — only fires when at least one gate is pending.
  if (input.approvalsPending > 0) {
    decisions.push({
      category: 'approval_needed',
      dedupeKey: `approval_needed|${input.approvalsPending}|${slice}`,
      title: `Approvals: ${input.approvalsPending}`,
      body: joinBody([
        `${input.approvalsPending} pending approval gate${input.approvalsPending === 1 ? '' : 's'}`,
        topPriority ? `Priority: ${topPriority}` : null,
        recommendedNextAction ? `Next: ${recommendedNextAction}` : null,
      ]),
      evidenceLabel: 'repo-only',
      topPriority,
      recommendedNextAction,
      laneId: null,
    });
  }

  // 4. Installed-device QA — caller asserts mirror/simulator evidence
  //    cannot clear the audit gate. Honest by construction: we only
  //    fire when the caller passes the boolean.
  if (input.installedDeviceQaPending) {
    decisions.push({
      category: 'installed_device_qa_needed',
      dedupeKey: `installed_device_qa|${slice}`,
      title: 'Installed-device QA needed',
      body: joinBody([
        'Mirror/simulator evidence cannot clear this gate',
        topPriority ? `Priority: ${topPriority}` : null,
        recommendedNextAction ? `Next: ${recommendedNextAction}` : null,
      ]),
      evidenceLabel: 'repo-only',
      topPriority,
      recommendedNextAction,
      laneId: null,
    });
  }

  // 5. All lanes idle — only when every primary lane is idle/stale
  //    AND none are working / blocked. Suppresses individual idle
  //    notifications for the same lanes.
  const primaryLanes = PRIMARY_LANES.map((id) =>
    input.laneSummary.lanes.find((l) => l.id === id),
  );
  const everyPrimaryPresent = primaryLanes.every((l) => l != null);
  const everyPrimaryIdle = everyPrimaryPresent
    && primaryLanes.every((l) => l != null && IDLE_IDLE.has(l.idleStatus));
  if (everyPrimaryIdle) {
    decisions.push({
      category: 'all_lanes_idle',
      dedupeKey: `all_lanes_idle|${slice}`,
      title: 'All lanes idle',
      body: joinBody([
        'claude, codex, agent are idle',
        topPriority ? `Priority: ${topPriority}` : null,
        recommendedNextAction ? `Next: ${recommendedNextAction}` : 'queue next prompt',
      ]),
      evidenceLabel: 'repo-only',
      topPriority,
      recommendedNextAction,
      laneId: null,
    });
  } else {
    // 6. Per-lane idle (fall-through) — surface each idle primary
    //    lane independently so the user can act on whichever is
    //    waiting. Skipped when all-lanes-idle already fired.
    for (const lane of input.laneSummary.lanes) {
      if (!IDLE_IDLE.has(lane.idleStatus)) continue;
      const isPrimary = PRIMARY_LANES.includes(lane.id as (typeof PRIMARY_LANES)[number]);
      if (!isPrimary) continue;
      decisions.push({
        category: 'idle_lane',
        dedupeKey: `idle_lane|${lane.id}|${lane.idleStatus}|${slice}`,
        title: `${lane.id} idle`,
        body: joinBody([
          `Lane ${lane.id} is ${lane.idleStatus}`,
          lane.recommendedNextPromptSummary,
          recommendedNextAction ? `Next: ${recommendedNextAction}` : null,
        ]),
        evidenceLabel: 'repo-only',
        topPriority,
        recommendedNextAction: lane.recommendedNextPromptSummary ?? recommendedNextAction,
        laneId: lane.id,
      });
    }
  }

  // Stable ordering — most-actionable categories first.
  decisions.sort((a, b) => {
    const ai = CATEGORY_PRIORITY.indexOf(a.category);
    const bi = CATEGORY_PRIORITY.indexOf(b.category);
    if (ai !== bi) return ai - bi;
    return a.dedupeKey.localeCompare(b.dedupeKey);
  });

  return decisions;
}

/**
 * Compute the single highest-priority decision the controller home
 * should highlight at the top of the screen. Returns null when
 * everything is fresh and no action is required.
 */
export function topControllerDecision(decisions: ControllerNotificationDecision[]): ControllerNotificationDecision | null {
  return decisions.length > 0 ? decisions[0] : null;
}

/**
 * Map a category → an existing AndroidControllerNotificationCategory
 * for the lazy-loaded expo-notifications channel. New categories
 * collapse to the closest existing channel so we do not need a
 * native build to ship a new bucket.
 */
export function controllerCategoryToNativeCategory(
  category: ControllerNotificationCategory,
): 'idle_lane' | 'approval_needed' | 'mcp_stale' | 'build_blocked' {
  switch (category) {
    case 'mcp_stale':
      return 'mcp_stale';
    case 'lane_blocked':
    case 'installed_device_qa_needed':
      return 'build_blocked';
    case 'approval_needed':
      return 'approval_needed';
    case 'all_lanes_idle':
    case 'idle_lane':
    default:
      return 'idle_lane';
  }
}
