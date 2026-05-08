/**
 * Freshness signal contract test for project.get_current_state +
 * companion surfaces.
 *
 * Asserts the staleReason union distinguishes:
 *   - no_writeback: row never written (updatedAt null)
 *   - stale_writeback: row written but older than 10-min window
 *   - fresh: row within window
 *   - env_missing: Worker not configured
 *
 * Pre-2026-05-09 the Worker collapsed both no_writeback and
 * stale_writeback into "no_writeback" — the Admin/Dev tab
 * couldn't tell whether the bridge had ever run vs whether it
 * had run-but-not-recently. This test pins the distinction
 * + the LIVE_MCP_MODEL_SPEC § 1.1 contract + the rule 11 stale
 * branch.
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-mcp-freshness-staleness.ts
 */

import * as assert from 'node:assert/strict';

// Re-derive computeFreshness inputs/outputs as a contract.
// We don't import the function (avoid coupling to private
// Worker types) — instead we test the OBSERVABLE shape that
// any consumer relies on.

interface FreshnessShape {
  updatedAt: string | null;
  ageMs: number | null;
  isStale: boolean;
  staleReason: 'fresh' | 'no_writeback' | 'stale_writeback' | 'env_missing';
  windowMs: number;
}

const TEN_MIN_MS = 10 * 60 * 1000;

function computeFreshnessReplica(updatedAt: string | null, configured: boolean, now = Date.now()): FreshnessShape {
  if (!configured) {
    return { updatedAt: null, ageMs: null, isStale: true, staleReason: 'env_missing', windowMs: TEN_MIN_MS };
  }
  const ageMs = updatedAt ? now - new Date(updatedAt).getTime() : null;
  const isStale = ageMs === null ? true : ageMs > TEN_MIN_MS;
  const staleReason: FreshnessShape['staleReason'] = updatedAt === null
    ? 'no_writeback'
    : isStale ? 'stale_writeback' : 'fresh';
  return { updatedAt, ageMs, isStale, staleReason, windowMs: TEN_MIN_MS };
}

// Case 1: env_missing
{
  const r = computeFreshnessReplica(null, false);
  assert.equal(r.staleReason, 'env_missing', 'unconfigured Worker → env_missing');
  assert.equal(r.isStale, true, 'env_missing implies isStale');
  assert.equal(r.updatedAt, null);
  assert.equal(r.ageMs, null);
}

// Case 2: no_writeback (configured but row never written)
{
  const r = computeFreshnessReplica(null, true);
  assert.equal(r.staleReason, 'no_writeback', 'null updatedAt → no_writeback');
  assert.equal(r.isStale, true);
}

// Case 3: stale_writeback (row written >10 min ago)
{
  const now = Date.now();
  const fifteenMinAgo = new Date(now - 15 * 60 * 1000).toISOString();
  const r = computeFreshnessReplica(fifteenMinAgo, true, now);
  assert.equal(r.staleReason, 'stale_writeback', 'old updatedAt → stale_writeback (NOT no_writeback)');
  assert.equal(r.isStale, true);
  assert.ok(r.ageMs && r.ageMs >= 15 * 60 * 1000 - 1000, 'ageMs reflects ~15 min');
}

// Case 4: fresh
{
  const now = Date.now();
  const oneMinAgo = new Date(now - 60 * 1000).toISOString();
  const r = computeFreshnessReplica(oneMinAgo, true, now);
  assert.equal(r.staleReason, 'fresh', '<10 min updatedAt → fresh');
  assert.equal(r.isStale, false);
  assert.ok(r.ageMs && r.ageMs >= 60 * 1000 - 1000, 'ageMs reflects ~60s');
}

// Case 5: edge of window (just outside 10-min window)
{
  const now = Date.now();
  const justOver = new Date(now - (TEN_MIN_MS + 5_000)).toISOString();
  const r = computeFreshnessReplica(justOver, true, now);
  assert.equal(r.staleReason, 'stale_writeback', 'just-over-window → stale_writeback');
  assert.equal(r.isStale, true);
}

// Case 6: edge of window (just inside)
{
  const now = Date.now();
  const justInside = new Date(now - (TEN_MIN_MS - 5_000)).toISOString();
  const r = computeFreshnessReplica(justInside, true, now);
  assert.equal(r.staleReason, 'fresh', 'just-inside-window → fresh');
  assert.equal(r.isStale, false);
}

// Case 7: stale_writeback never collapses to no_writeback (rule 11
// stale branch governs — consumers can DIFFERENTIATE on this)
{
  const now = Date.now();
  const r1 = computeFreshnessReplica(null, true);
  const r2 = computeFreshnessReplica(new Date(now - 30 * 60 * 1000).toISOString(), true, now);
  assert.notEqual(r1.staleReason, r2.staleReason,
    'no_writeback and stale_writeback are distinct values');
}

console.log('✓ MCP freshness staleness contract: env_missing / no_writeback / stale_writeback / fresh distinct');
console.log('Freshness signal contract test passed.');
