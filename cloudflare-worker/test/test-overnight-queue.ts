/**
 * Overnight Prompt Queue contract test. Locks:
 *
 * - Schema validation rejects malformed rows.
 * - Idle-lane recommendation picks the highest-priority candidate
 *   for the lane and respects FIFO within the same priority band.
 * - P0 / P1 blockers ALWAYS win — `recommendOvernightTaskForLane`
 *   returns null when either is pending.
 * - Stale tasks (updated_at older than threshold) surface
 *   `stale: true` in the admin view.
 * - Public summary never includes prompt body / dependency content.
 */

import assert from 'node:assert/strict';
import {
  DEFAULT_STALE_THRESHOLD_HOURS,
  buildPublicOvernightQueueSummary,
  computeStaleAgeHours,
  pickRecommendedTask,
  recommendOvernightTaskForLane,
  redactOvernightRowForAdmin,
  validateOvernightRow,
  type OvernightQueueRow,
} from '../src/overnight-queue';

const NOW = Date.parse('2026-05-09T12:00:00Z');

function isoAgo(ms: number): string {
  return new Date(NOW - ms).toISOString();
}

function makeRow(overrides: Partial<OvernightQueueRow> = {}): OvernightQueueRow {
  return {
    id: '11111111-1111-4111-a111-111111111111',
    title: 'Refresh stale FS-XXX backlog candidates',
    lane_owner: 'codex',
    estimated_unattended_runtime_minutes: 90,
    requires_human_interaction: false,
    safe_overnight: true,
    dependencies: [],
    interrupt_priority: 'overnight_only',
    repo_only_relevance: true,
    preview_only_relevance: false,
    installed_build_verified_relevance: false,
    suggested_execution_window: 'weeknight_us_pt',
    progress_pct: 0,
    outcome_summary: null,
    created_at: isoAgo(48 * 3_600_000),
    updated_at: isoAgo(2 * 3_600_000),
    started_at: null,
    completed_at: null,
    ...overrides,
  };
}

function expectSchemaValidation(): void {
  // Happy path.
  const ok = validateOvernightRow(makeRow());
  assert.equal(ok.ok, true, 'happy-path row must validate');

  // Bad uuid.
  const badId = validateOvernightRow(makeRow({ id: 'not-a-uuid' as OvernightQueueRow['id'] }));
  assert.equal(badId.ok, false);
  if (!badId.ok) assert.equal(badId.field, 'id');

  // Bad lane_owner.
  const badOwner = validateOvernightRow(makeRow({ lane_owner: 'human' as unknown as OvernightQueueRow['lane_owner'] }));
  assert.equal(badOwner.ok, false);
  if (!badOwner.ok) assert.equal(badOwner.field, 'lane_owner');

  // Out-of-range progress.
  const badProgress = validateOvernightRow(makeRow({ progress_pct: 150 }));
  assert.equal(badProgress.ok, false);
  if (!badProgress.ok) assert.equal(badProgress.field, 'progress_pct');

  // Title too long.
  const badTitle = validateOvernightRow(makeRow({ title: 'a'.repeat(141) }));
  assert.equal(badTitle.ok, false);
  if (!badTitle.ok) assert.equal(badTitle.field, 'title');

  // Bad ISO timestamp.
  const badIso = validateOvernightRow(makeRow({ updated_at: 'yesterday' as OvernightQueueRow['updated_at'] }));
  assert.equal(badIso.ok, false);
  if (!badIso.ok) assert.equal(badIso.field, 'updated_at');
}

function expectIdleLaneRoutingPicksOldestSamePriority(): void {
  // Two p2 codex tasks, the older one should be picked.
  const older = makeRow({
    id: '22222222-2222-4222-a222-222222222222',
    interrupt_priority: 'p2',
    created_at: isoAgo(72 * 3_600_000),
  });
  const newer = makeRow({
    id: '33333333-3333-4333-a333-333333333333',
    interrupt_priority: 'p2',
    created_at: isoAgo(24 * 3_600_000),
  });
  const lower = makeRow({
    id: '44444444-4444-4444-a444-444444444444',
    interrupt_priority: 'p3',
    created_at: isoAgo(96 * 3_600_000),
  });
  const result = pickRecommendedTask([newer, lower, older], 'codex', [], NOW);
  assert.equal(result?.id, older.id, 'older p2 task wins over newer p2 and a higher-id p3 task');
}

function expectP0WinsOverOvernight(): void {
  const overnightCandidate = makeRow({ interrupt_priority: 'p2' });
  const recommended = recommendOvernightTaskForLane({
    laneOwner: 'codex',
    rows: [overnightCandidate],
    completedDependencyIds: [],
    pendingP0Count: 1,
    pendingP1Count: 0,
    nowMs: NOW,
  });
  assert.equal(recommended, null, 'P0 blocker MUST suppress overnight recommendation');

  const recommendedWithP1 = recommendOvernightTaskForLane({
    laneOwner: 'codex',
    rows: [overnightCandidate],
    completedDependencyIds: [],
    pendingP0Count: 0,
    pendingP1Count: 1,
    nowMs: NOW,
  });
  assert.equal(recommendedWithP1, null, 'P1 blocker MUST also suppress overnight recommendation');

  const recommendedClean = recommendOvernightTaskForLane({
    laneOwner: 'codex',
    rows: [overnightCandidate],
    completedDependencyIds: [],
    pendingP0Count: 0,
    pendingP1Count: 0,
    nowMs: NOW,
  });
  assert.equal(recommendedClean?.id, overnightCandidate.id, 'no blockers → recommendation surfaces');
}

function expectDependenciesGate(): void {
  // Same priority band so the older `created_at` decides — once
  // the dependency clears.
  const blocked = makeRow({
    id: '55555555-5555-4555-a555-555555555555',
    dependencies: ['action-ledger-row-1'],
    interrupt_priority: 'p3',
    created_at: isoAgo(48 * 3_600_000),
  });
  const free = makeRow({
    id: '66666666-6666-4666-a666-666666666666',
    interrupt_priority: 'p3',
    created_at: isoAgo(12 * 3_600_000),
  });
  const result = pickRecommendedTask([blocked, free], 'codex', [], NOW);
  assert.equal(result?.id, free.id, 'unsatisfied dependency must skip the candidate');
  const cleared = pickRecommendedTask([blocked, free], 'codex', ['action-ledger-row-1'], NOW);
  assert.equal(cleared?.id, blocked.id, 'completed dependency unblocks the candidate; same-priority older created_at wins');
}

function expectInFlightTasksAreNotRerecommended(): void {
  const inFlight = makeRow({
    id: '77777777-7777-4777-a777-777777777777',
    started_at: isoAgo(30 * 60_000),
    interrupt_priority: 'p2',
  });
  const fresh = makeRow({
    id: '88888888-8888-4888-a888-888888888888',
    interrupt_priority: 'p3',
  });
  const result = pickRecommendedTask([inFlight, fresh], 'codex', [], NOW);
  assert.equal(result?.id, fresh.id, 'in-flight tasks (started_at != null && completed_at == null) must not be re-recommended');
}

function expectStaleAgeFlagging(): void {
  const stale = makeRow({
    id: '99999999-9999-4999-a999-999999999999',
    updated_at: isoAgo((DEFAULT_STALE_THRESHOLD_HOURS + 24) * 3_600_000),
  });
  const fresh = makeRow({
    id: 'aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa',
    updated_at: isoAgo(2 * 3_600_000),
  });
  assert.equal(computeStaleAgeHours(stale.updated_at, NOW), DEFAULT_STALE_THRESHOLD_HOURS + 24);
  assert.equal(computeStaleAgeHours(fresh.updated_at, NOW), 2);
  const adminStale = redactOvernightRowForAdmin(stale, DEFAULT_STALE_THRESHOLD_HOURS, NOW);
  assert.equal(adminStale.stale, true, 'rows older than the threshold must surface stale=true');
  const adminFresh = redactOvernightRowForAdmin(fresh, DEFAULT_STALE_THRESHOLD_HOURS, NOW);
  assert.equal(adminFresh.stale, false);
}

function expectAdminRedactionDropsDepsContent(): void {
  const row = makeRow({
    dependencies: ['secret-action-1', 'secret-action-2', 'secret-action-3'],
    outcome_summary: 'a'.repeat(500),
  });
  const admin = redactOvernightRowForAdmin(row);
  assert.equal(admin.dependency_count, 3, 'redacted view exposes count only');
  assert.equal('dependencies' in admin, false, 'redacted view MUST NOT carry the raw dependency ids');
  assert.equal(admin.outcome_summary?.length, 140, 'outcome_summary truncated to ≤140 chars on admin redaction');
}

function expectPublicSummaryIsCountOnly(): void {
  const rows: OvernightQueueRow[] = [
    makeRow({ id: 'bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb', interrupt_priority: 'p2', created_at: isoAgo(48 * 3_600_000) }),
    makeRow({ id: 'cccccccc-cccc-4ccc-cccc-cccccccccccc', interrupt_priority: 'p3', updated_at: isoAgo((DEFAULT_STALE_THRESHOLD_HOURS + 1) * 3_600_000) }),
  ];
  const summary = buildPublicOvernightQueueSummary(rows, DEFAULT_STALE_THRESHOLD_HOURS, NOW);
  assert.equal(summary.count, 2);
  assert.equal(summary.recommendedTaskId, 'bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb');
  assert.equal(summary.safeToRunUnattended, true);
  assert.equal(summary.hasStaleEntries, true);
  // Anti-rule: no row content leaks. The summary type itself
  // does not declare a payload field — assert by structural
  // inspection of the runtime keys.
  assert.deepEqual(
    Object.keys(summary).sort(),
    ['count', 'hasStaleEntries', 'recommendedTaskId', 'safeToRunUnattended'],
    'public summary MUST NOT leak title / lane_owner / dependencies',
  );
}

function expectEmptyQueueIsSafe(): void {
  const summary = buildPublicOvernightQueueSummary([], DEFAULT_STALE_THRESHOLD_HOURS, NOW);
  assert.equal(summary.count, 0);
  assert.equal(summary.recommendedTaskId, null);
  assert.equal(summary.safeToRunUnattended, false);
  assert.equal(summary.hasStaleEntries, false);
}

function main(): void {
  expectSchemaValidation();
  expectIdleLaneRoutingPicksOldestSamePriority();
  expectP0WinsOverOvernight();
  expectDependenciesGate();
  expectInFlightTasksAreNotRerecommended();
  expectStaleAgeFlagging();
  expectAdminRedactionDropsDepsContent();
  expectPublicSummaryIsCountOnly();
  expectEmptyQueueIsSafe();
  console.log('Overnight Prompt Queue contract test passed (schema / routing / P0 override / dependencies / stale / redaction / public summary).');
}

main();
