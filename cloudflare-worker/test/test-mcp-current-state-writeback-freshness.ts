/**
 * project.get_current_state writeback freshness contract.
 *
 * Locks the bridge -> Supabase -> current_state timestamp contract:
 * the newest successful bridge snapshot timestamp must be eligible
 * for freshness even when it arrives as `generatedAt`, and stale
 * cached working lanes must not keep reporting as working.
 */

import assert from 'node:assert/strict';
import {
  computeFreshness,
  effectiveAgentStatusForFreshness,
  latestIsoTimestamp,
} from '../src/mcp-v2';

const NOW = Date.parse('2026-05-09T07:00:00Z');

function expectGeneratedAtCanMakeCurrentStateFresh(): void {
  const updatedAt = latestIsoTimestamp([
    '2026-05-09T06:21:54Z',
    '2026-05-09T06:59:37Z',
    null,
    undefined,
  ]);
  assert.equal(updatedAt, '2026-05-09T06:59:37Z');

  const freshness = computeFreshness(updatedAt, true, NOW);
  assert.equal(freshness.staleReason, 'fresh');
  assert.equal(freshness.isStale, false);
  assert.equal(freshness.updatedAt, '2026-05-09T06:59:37Z');
}

function expectOldGeneratedAtIsStaleWritebackNotNoWriteback(): void {
  const updatedAt = latestIsoTimestamp([
    '2026-05-09T06:21:54Z',
  ]);
  const freshness = computeFreshness(updatedAt, true, NOW);
  assert.equal(freshness.updatedAt, '2026-05-09T06:21:54Z');
  assert.equal(freshness.isStale, true);
  assert.equal(
    freshness.staleReason,
    'stale_writeback',
    'old non-null writeback must not collapse to no_writeback',
  );
}

function expectStaleWorkingDowngrades(): void {
  const stale = computeFreshness('2026-05-09T06:21:54Z', true, NOW);
  const fresh = computeFreshness('2026-05-09T06:59:37Z', true, NOW);

  assert.equal(effectiveAgentStatusForFreshness('working', stale), 'idle');
  assert.equal(effectiveAgentStatusForFreshness('in_progress', stale), 'idle');
  assert.equal(effectiveAgentStatusForFreshness('working', fresh), 'working');
  assert.equal(effectiveAgentStatusForFreshness('blocked', stale), 'blocked');
  assert.equal(effectiveAgentStatusForFreshness('needs_review', stale), 'needs_review');
}

function main(): void {
  expectGeneratedAtCanMakeCurrentStateFresh();
  expectOldGeneratedAtIsStaleWritebackNotNoWriteback();
  expectStaleWorkingDowngrades();
  console.log('MCP current_state writeback freshness contract test passed.');
}

main();
