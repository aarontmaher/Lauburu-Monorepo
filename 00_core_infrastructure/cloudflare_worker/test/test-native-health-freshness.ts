/**
 * Behaviour contract for services/native-health-freshness.
 *
 * The helper has zero React-Native dependencies, so unlike the
 * AppAthleteState / HealthActionsPanel contracts (which can only
 * be source-asserted because their modules import RN at top
 * level), we can actually exercise the function with a fake clock
 * and pin the 48h boundary numerically. That means the threshold
 * change can never silently drift past 48h without this test
 * failing.
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-native-health-freshness.ts
 */

import assert from 'node:assert/strict';
// @ts-expect-error — helper is .ts under apps/mobile, resolved at runtime by tsx.
import {
  NATIVE_HEALTH_STALE_HOURS,
  NATIVE_HEALTH_STALE_MS,
  hoursSinceNativeHealthSync,
  isNativeHealthSyncStale,
} from '../../apps/mobile/src/services/native-health-freshness';

assert.equal(NATIVE_HEALTH_STALE_HOURS, 48, 'threshold must be 48h');
assert.equal(NATIVE_HEALTH_STALE_MS, 48 * 60 * 60 * 1000, 'ms threshold derived from hours');

// "no record" cases must be neither stale nor null-freshness.
assert.equal(isNativeHealthSyncStale(null), false, 'no lastSyncAt → not stale');
assert.equal(isNativeHealthSyncStale(undefined), false, 'undefined lastSyncAt → not stale');
assert.equal(hoursSinceNativeHealthSync(null), null, 'no lastSyncAt → null hours');
assert.equal(hoursSinceNativeHealthSync(undefined), null, 'undefined lastSyncAt → null hours');

// Bad-string cases mustn't crash.
assert.equal(isNativeHealthSyncStale('not-a-date'), false, 'unparseable lastSyncAt → not stale');
assert.equal(hoursSinceNativeHealthSync('not-a-date'), null, 'unparseable → null hours');

const NOW = Date.parse('2026-05-10T08:00:00Z');

const fresh = new Date(NOW - 60 * 60 * 1000).toISOString(); // 1h ago
assert.equal(isNativeHealthSyncStale(fresh, NOW), false, '1h ago is fresh');
assert.equal(hoursSinceNativeHealthSync(fresh, NOW), 1, '1h ago → 1.0 hours');

const justBeforeBoundary = new Date(NOW - (48 * 60 * 60 * 1000 - 1)).toISOString();
assert.equal(isNativeHealthSyncStale(justBeforeBoundary, NOW), false, 'just under 48h is fresh');

const exactlyBoundary = new Date(NOW - 48 * 60 * 60 * 1000).toISOString();
assert.equal(isNativeHealthSyncStale(exactlyBoundary, NOW), false, 'exactly 48h is not yet stale');

const justAfterBoundary = new Date(NOW - (48 * 60 * 60 * 1000 + 1)).toISOString();
assert.equal(isNativeHealthSyncStale(justAfterBoundary, NOW), true, 'just over 48h is stale');

const veryStale = new Date(NOW - 10 * 24 * 60 * 60 * 1000).toISOString(); // 10 days
assert.equal(isNativeHealthSyncStale(veryStale, NOW), true, '10d ago is stale');
assert.equal(hoursSinceNativeHealthSync(veryStale, NOW), 240, '10d → 240 hours');

// Future-dated lastSyncAt (clock skew on the device) must clamp to 0
// hours, not negative — the Coach AI context formats the number with
// no defensive shielding.
const future = new Date(NOW + 60 * 60 * 1000).toISOString();
assert.equal(hoursSinceNativeHealthSync(future, NOW), 0, 'future lastSyncAt clamps to 0h');
assert.equal(isNativeHealthSyncStale(future, NOW), false, 'future is not stale');

console.log('native-health-freshness helper contract test passed.');
