import {
  decideControllerNotifications,
  topControllerDecision,
  controllerCategoryToNativeCategory,
  type DecisionInput,
} from './controller-notification-decisions';
import type { LaneProgressEntry, LaneProgressSummary } from './lane-progress-summary';
import type { AndroidControllerContext } from './android-controller-context';

function fail(message: string): never {
  throw new Error(message);
}

function assertEqual<T>(actual: T, expected: T, message: string): void {
  if (actual !== expected) {
    fail(`${message}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

function assertContains(haystack: string, needle: string, message: string): void {
  if (!haystack.includes(needle)) {
    fail(`${message}: "${haystack}" does not contain "${needle}"`);
  }
}

function lane(partial: Partial<LaneProgressEntry> & { id: string }): LaneProgressEntry {
  return {
    id: partial.id,
    status: partial.status ?? 'idle',
    ageMs: partial.ageMs ?? 1_000,
    ageLabel: partial.ageLabel ?? '1s',
    freshness: partial.freshness ?? 'fresh',
    idleStatus: partial.idleStatus ?? 'idle',
    needsPrompt: partial.needsPrompt ?? true,
    progressPct: partial.progressPct ?? null,
    recommendedNextPrompt: partial.recommendedNextPrompt ?? null,
    recommendedNextPromptTarget: partial.recommendedNextPromptTarget ?? partial.id,
    recommendedNextPromptSummary: partial.recommendedNextPromptSummary ?? null,
    taskSummary: partial.taskSummary ?? null,
  };
}

function laneSummary(lanes: LaneProgressEntry[]): LaneProgressSummary {
  return {
    source: 'mcp',
    snapshotFreshness: 'fresh',
    snapshotStaleReason: null,
    lanes,
    promptsRequired: lanes
      .filter((l) => l.needsPrompt)
      .map((l) => ({
        laneId: l.id,
        idleStatus: l.idleStatus,
        recommendedNextPromptTarget: l.recommendedNextPromptTarget,
        recommendedNextPromptText: l.recommendedNextPrompt,
        recommendedNextPromptSummary: l.recommendedNextPromptSummary,
        promptProgressPercent: l.progressPct == null ? ('unknown' as const) : l.progressPct,
      })),
  };
}

function context(partial: Partial<AndroidControllerContext['mcp']> & { freshness: AndroidControllerContext['mcp']['freshness'] }): AndroidControllerContext {
  return {
    schemaVersion: 1,
    mode: 'android_admin_controller',
    platform: 'android',
    generatedAt: '2026-05-10T00:00:00Z',
    mcp: {
      freshness: partial.freshness,
      lastWritebackAgeMs: partial.lastWritebackAgeMs ?? 0,
      staleReason: partial.staleReason ?? null,
    },
    lanes: [],
    nextPromptTarget: null,
    approvals: { humanApprovalCount: 0 },
    gates: { build: 'unknown', qa: 'unknown' },
    queues: { overnightCount: 0, auditCount: 0 },
    notifications: { categories: [] as never },
    auditRunner: {
      startAuditCommand: '',
      screenshotCommand: '',
      videoCommand: '',
      latestEvidencePath: null,
      simulatorOrMirrorEvidenceOnly: true,
      canClearInstalledDeviceGate: false,
    },
    healthConnect: {
      state: 'unknown',
      lastSyncAt: null,
      availableMetrics: 0,
      missingMetrics: [],
    },
    deepLinks: {
      adminDev: '/admin-dev',
      approvalQueue: '/admin-dev#approval-queue',
      latestEvidence: '/admin-dev#latest-evidence',
    },
    safety: {
      publicSafe: true,
      adminEntitlementRequired: true,
      includesSecrets: false,
      includesRawLogs: false,
      noReleaseActions: true,
      noInstalledBuildVerifiedClaim: true,
    },
  };
}

const NOW = new Date('2026-05-10T00:00:00Z').getTime();

// 1. All-lanes-idle fires once and suppresses per-lane idle.
{
  const decisions = decideControllerNotifications({
    context: context({ freshness: 'fresh' }),
    laneSummary: laneSummary([
      lane({ id: 'claude', idleStatus: 'idle' }),
      lane({ id: 'codex', idleStatus: 'idle' }),
      lane({ id: 'agent', idleStatus: 'idle' }),
    ]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: 'Samsung phone controller P0',
    recommendedNextAction: 'queue Codex prompt for safe bundle',
    nowMs: NOW,
  } satisfies DecisionInput);
  assertEqual(decisions.length, 1, 'all-lanes-idle: single decision');
  assertEqual(decisions[0].category, 'all_lanes_idle', 'all-lanes-idle category');
  assertContains(decisions[0].body, 'queue Codex prompt for safe bundle', 'all-lanes-idle body has next action');
  assertContains(decisions[0].body, 'Samsung phone controller P0', 'all-lanes-idle body has top priority');
  assertEqual(decisions[0].evidenceLabel, 'repo-only', 'all-lanes-idle evidence label is honest');
}

// 2. MCP stale ranks above per-lane decisions and is highest priority.
{
  const decisions = decideControllerNotifications({
    context: context({ freshness: 'stale', staleReason: 'writeback older than 90s' }),
    laneSummary: laneSummary([
      lane({ id: 'claude', idleStatus: 'idle' }),
      lane({ id: 'codex', idleStatus: 'blocked', recommendedNextPromptSummary: 'unblock supabase JWT' }),
      lane({ id: 'agent', idleStatus: 'working', needsPrompt: false }),
    ]),
    approvalsPending: 2,
    installedDeviceQaPending: true,
    topPriority: 'p',
    recommendedNextAction: 'n',
    nowMs: NOW,
  });
  const top = topControllerDecision(decisions);
  if (!top) fail('expected at least one decision');
  assertEqual(top.category, 'mcp_stale', 'mcp_stale ranks first');
  assertContains(top.body, 'writeback older than 90s', 'mcp_stale body carries reason');
}

// 3. Lane blocked fires per-lane with lane id and recommendation.
{
  const decisions = decideControllerNotifications({
    context: context({ freshness: 'fresh' }),
    laneSummary: laneSummary([
      lane({ id: 'codex', idleStatus: 'blocked', recommendedNextPromptSummary: 'rebase main' }),
      lane({ id: 'claude', idleStatus: 'working', needsPrompt: false }),
    ]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: null,
    nowMs: NOW,
  });
  const blocked = decisions.find((d) => d.category === 'lane_blocked');
  if (!blocked) fail('expected lane_blocked decision');
  assertEqual(blocked.laneId, 'codex', 'lane_blocked anchored to codex');
  assertContains(blocked.body, 'rebase main', 'lane_blocked body uses recommendation');
}

// 4. Approvals only fire when count > 0.
{
  const noApprovals = decideControllerNotifications({
    context: context({ freshness: 'fresh' }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: null,
    nowMs: NOW,
  });
  if (noApprovals.some((d) => d.category === 'approval_needed')) fail('approval_needed must not fire when 0 pending');

  const withApprovals = decideControllerNotifications({
    context: context({ freshness: 'fresh' }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 3,
    installedDeviceQaPending: false,
    topPriority: 'priority',
    recommendedNextAction: 'review queue',
    nowMs: NOW,
  });
  const a = withApprovals.find((d) => d.category === 'approval_needed');
  if (!a) fail('approval_needed should fire when count > 0');
  assertContains(a.title, '3', 'approval title carries count');
  assertContains(a.body, 'review queue', 'approval body carries recommended next action');
}

// 5. Per-lane idle fires only for primary lanes when not all idle.
{
  const decisions = decideControllerNotifications({
    context: context({ freshness: 'fresh' }),
    laneSummary: laneSummary([
      lane({ id: 'claude', idleStatus: 'idle' }),
      lane({ id: 'codex', idleStatus: 'working', needsPrompt: false }),
      lane({ id: 'bridge-watch', idleStatus: 'idle' }),
    ]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: 'queue claude',
    nowMs: NOW,
  });
  const idleClaude = decisions.find((d) => d.category === 'idle_lane' && d.laneId === 'claude');
  const idleBridge = decisions.find((d) => d.category === 'idle_lane' && d.laneId === 'bridge-watch');
  if (!idleClaude) fail('idle_lane should fire for claude');
  if (idleBridge) fail('idle_lane should NOT fire for non-primary automation loop lane');
}

// 6. Honest construction — no completion / build / release category exists.
{
  const decisions = decideControllerNotifications({
    context: context({ freshness: 'fresh' }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: null,
    nowMs: NOW,
  });
  for (const decision of decisions) {
    if (decision.category === ('release' as never)) fail('no release category should exist');
    if (decision.category === ('build_succeeded' as never)) fail('no build success category should exist');
    if (decision.evidenceLabel === 'live-now') fail('no decision should claim live-now without server evidence');
    if (decision.evidenceLabel === 'installed-build verified') fail('no decision should claim installed-build verified');
  }
}

// 7. controllerCategoryToNativeCategory collapses safely to existing channels.
{
  assertEqual(controllerCategoryToNativeCategory('mcp_stale'), 'mcp_stale', 'mcp_stale → mcp_stale');
  assertEqual(controllerCategoryToNativeCategory('lane_blocked'), 'build_blocked', 'lane_blocked → build_blocked');
  assertEqual(controllerCategoryToNativeCategory('installed_device_qa_needed'), 'build_blocked', 'qa → build_blocked');
  assertEqual(controllerCategoryToNativeCategory('approval_needed'), 'approval_needed', 'approval → approval');
  assertEqual(controllerCategoryToNativeCategory('all_lanes_idle'), 'idle_lane', 'all_lanes_idle → idle_lane');
  assertEqual(controllerCategoryToNativeCategory('idle_lane'), 'idle_lane', 'idle_lane → idle_lane');
}

// 8. dedupeKey is stable for the same input slice.
{
  const a = decideControllerNotifications({
    context: context({ freshness: 'stale', staleReason: 'r' }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: null,
    nowMs: NOW,
  });
  const b = decideControllerNotifications({
    context: context({ freshness: 'stale', staleReason: 'r' }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: null,
    nowMs: NOW + 30_000, // same 5-minute slice
  });
  assertEqual(a[0]?.dedupeKey, b[0]?.dedupeKey, 'dedupeKey stable inside slice');

  const c = decideControllerNotifications({
    context: context({ freshness: 'stale', staleReason: 'r' }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: null,
    recommendedNextAction: null,
    nowMs: NOW + 10 * 60_000, // next slice
  });
  if (a[0]?.dedupeKey === c[0]?.dedupeKey) fail('dedupeKey must change across slices');
}

// 9. Body length stays under cap even with long inputs.
{
  const longText = 'x'.repeat(2000);
  const decisions = decideControllerNotifications({
    context: context({ freshness: 'stale', staleReason: longText }),
    laneSummary: laneSummary([lane({ id: 'claude', idleStatus: 'working', needsPrompt: false })]),
    approvalsPending: 0,
    installedDeviceQaPending: false,
    topPriority: longText,
    recommendedNextAction: longText,
    nowMs: NOW,
  });
  for (const decision of decisions) {
    if (decision.body.length > 240) fail(`body too long: ${decision.body.length}`);
    if (decision.title.length > 60) fail(`title too long: ${decision.title.length}`);
  }
}

console.log('controller-notification-decisions: all assertions passed');
