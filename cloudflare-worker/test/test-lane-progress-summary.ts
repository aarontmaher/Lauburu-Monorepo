/**
 * Lock the lane-progress summariser contract used by the
 * Admin/Dev lane chips strip. Covers the four prompt-required
 * states (fresh, stale, unavailable, unknown-progress) plus
 * the anti-rule cases (snapshot stale wins over per-lane fresh,
 * out-of-range progress sanitised to null, blank
 * recommendedNextPrompt sanitised to null).
 */

import assert from 'node:assert/strict';
import {
  LANE_FRESH_WINDOW_MS,
  sanitiseProgressPct,
  summariseLaneProgress,
} from '../../apps/mobile/src/services/lane-progress-summary';

const NOW = Date.parse('2026-05-09T12:00:00Z');

function isoAgo(ms: number): string {
  return new Date(NOW - ms).toISOString();
}

function expectFreshSnapshot(): void {
  const summary = summariseLaneProgress(
    {
      source: 'supabase',
      freshness: { isStale: false, updatedAt: isoAgo(15_000) },
      agents: [
        {
          id: 'claude',
          status: 'in_progress',
          taskSummary: 'CODEX-LANE-PROGRESS-BAR-01',
          lastSeenAt: isoAgo(5_000),
          updatedAt: isoAgo(8_000),
          progressPct: 42,
          recommendedNextPrompt: 'CODEX-NEXT-LANE-WORK-01',
        },
        {
          id: 'codex',
          status: 'idle',
          lastSeenAt: isoAgo(20_000),
          progressPct: null,
        },
      ],
    },
    NOW,
  );
  assert.equal(summary.source, 'mcp');
  assert.equal(summary.snapshotFreshness, 'fresh');
  assert.equal(summary.snapshotStaleReason, null);
  assert.equal(summary.lanes.length, 2);

  const claude = summary.lanes[0];
  assert.equal(claude.id, 'claude');
  assert.equal(claude.status, 'in_progress');
  assert.equal(claude.freshness, 'fresh');
  assert.equal(claude.progressPct, 42);
  assert.equal(claude.recommendedNextPrompt, 'CODEX-NEXT-LANE-WORK-01');
  assert.equal(claude.taskSummary, 'CODEX-LANE-PROGRESS-BAR-01');
  assert.equal(claude.ageLabel, '5s');

  const codex = summary.lanes[1];
  assert.equal(codex.freshness, 'fresh');
  assert.equal(codex.progressPct, null, 'unknown-progress lane must surface as null');
  assert.equal(codex.recommendedNextPrompt, null);
}

function expectStaleSnapshotWinsOverFreshLane(): void {
  // Anti-rule: a stale snapshot (worker writeback drift) overrides
  // any per-lane "fresh" reading. The lane lastSeenAt is recent
  // but the snapshot itself is stale, so all lanes render stale.
  const summary = summariseLaneProgress(
    {
      freshness: { isStale: true, staleReason: 'no_writeback', updatedAt: isoAgo(3_700_000) },
      agents: [
        { id: 'claude', status: 'IN_PROGRESS', lastSeenAt: isoAgo(2_000), progressPct: 60 },
      ],
    },
    NOW,
  );
  assert.equal(summary.source, 'mcp');
  assert.equal(summary.snapshotFreshness, 'stale');
  assert.equal(summary.snapshotStaleReason, 'no_writeback');
  assert.equal(summary.lanes[0].freshness, 'stale');
  assert.equal(summary.lanes[0].status, 'in_progress', 'status must be lower-cased for the UI');
  assert.equal(summary.lanes[0].progressPct, 60, 'progress is preserved even when stale');
}

function expectStaleByAge(): void {
  // Per-lane stale: lastSeenAt older than LANE_FRESH_WINDOW_MS.
  const summary = summariseLaneProgress(
    {
      freshness: { isStale: false, updatedAt: isoAgo(30_000) },
      agents: [
        { id: 'agent', status: 'idle', lastSeenAt: isoAgo(LANE_FRESH_WINDOW_MS + 30_000) },
      ],
    },
    NOW,
  );
  assert.equal(summary.snapshotFreshness, 'fresh');
  assert.equal(summary.lanes[0].freshness, 'stale');
}

function expectUnavailable(): void {
  for (const input of [null, undefined, {}, { agents: [] }]) {
    const summary = summariseLaneProgress(input as Parameters<typeof summariseLaneProgress>[0], NOW);
    assert.equal(summary.source, 'unavailable', `${JSON.stringify(input)} must be unavailable`);
    assert.equal(summary.lanes.length, 0);
    assert.equal(summary.snapshotFreshness, 'unknown');
  }
}

function expectUnknownProgress(): void {
  // Unknown-progress: missing field, undefined, NaN, +Infinity,
  // negative, > 100, non-number — all sanitise to null so the UI
  // renders "unknown" rather than 0%.
  for (const value of [undefined, null, NaN, Infinity, -Infinity, -1, 101, 1_000, '50' as unknown as number, true as unknown as number]) {
    assert.equal(sanitiseProgressPct(value), null, `progress ${JSON.stringify(value)} must sanitise to null`);
  }
  // 0 is a legitimate value (lane started but no progress recorded yet).
  assert.equal(sanitiseProgressPct(0), 0);
  assert.equal(sanitiseProgressPct(100), 100);
  assert.equal(sanitiseProgressPct(33.3), 33, 'fractional progress rounds to integer');
}

function expectUnknownAge(): void {
  // No lastSeenAt and no updatedAt → ageMs = null → freshness = 'unknown'
  const summary = summariseLaneProgress(
    {
      freshness: { isStale: false },
      agents: [
        { id: 'codex', status: 'idle' },
      ],
    },
    NOW,
  );
  assert.equal(summary.lanes[0].ageMs, null);
  assert.equal(summary.lanes[0].ageLabel, '—');
  assert.equal(summary.lanes[0].freshness, 'unknown');
}

function expectBlankRecommendationCoercedToNull(): void {
  const summary = summariseLaneProgress(
    {
      freshness: { isStale: false },
      agents: [
        { id: 'claude', status: 'idle', lastSeenAt: isoAgo(2_000), recommendedNextPrompt: '   ' },
        { id: 'codex', status: 'idle', lastSeenAt: isoAgo(2_000), recommendedNextPrompt: 'PROMPT-X' },
      ],
    },
    NOW,
  );
  assert.equal(summary.lanes[0].recommendedNextPrompt, null);
  assert.equal(summary.lanes[1].recommendedNextPrompt, 'PROMPT-X');
}

function main(): void {
  expectFreshSnapshot();
  expectStaleSnapshotWinsOverFreshLane();
  expectStaleByAge();
  expectUnavailable();
  expectUnknownProgress();
  expectUnknownAge();
  expectBlankRecommendationCoercedToNull();
  console.log('lane-progress summariser contract test passed (fresh / stale / unavailable / unknown-progress + anti-rule sanitisation).');
}

main();
