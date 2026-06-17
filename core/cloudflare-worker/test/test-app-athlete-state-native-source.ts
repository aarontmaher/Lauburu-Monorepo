/**
 * AppAthleteState native-health source contract.
 *
 * Static contract test because the module imports React Native
 * Platform at top level. Locks the Android/iOS sync payload shape
 * without booting a native runtime.
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const SOURCE = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/services/app-athlete-state.ts'),
  'utf8',
);

assert.ok(
  /const NATIVE_HEALTH_SOURCE = Platform\.OS === 'ios' \? 'apple_health' : 'health_connect';/.test(SOURCE),
  'AppAthleteState must derive a platform-native source id for iOS vs Android',
);

assert.ok(
  /native_health:\s*\{\s*source: 'apple_health' \| 'health_connect';\s*label: 'Apple Health' \| 'Health Connect';/s.test(SOURCE),
  'AppAthleteState interface must expose source_roles.native_health with platform source + label',
);

assert.ok(
  /freshness_hours:\s*\{[\s\S]*apple_health: fAH,[\s\S]*native_health: fAH,/m.test(SOURCE),
  'data_quality.freshness_hours must include native_health alongside legacy apple_health',
);

assert.ok(
  /source_roles:\s*\{[\s\S]*native_health:\s*\{[\s\S]*source: NATIVE_HEALTH_SOURCE,[\s\S]*label: NATIVE_HEALTH_LABEL,[\s\S]*role: appleHealthHasData \? 'broad_baseline' : 'not_connected'/m.test(SOURCE),
  'source_roles.native_health must be populated from the same sync evidence as the legacy broad-baseline field',
);

assert.ok(
  /primary_live_source: appleHealthHasData\s*\?\s*NATIVE_HEALTH_SOURCE\s*:\s*'none'/m.test(SOURCE),
  'primary_live_source must reuse the platform-native source id',
);

// v21 truth-label expansion — the Coach AI evidence builder needs
// freshness + is_stale on the native_health role so it can hedge
// "covers today" claims when the source is silent. These come from
// the shared services/native-health-freshness module so the Manage
// Sources sheet and the Coach context can never disagree.
assert.ok(
  /from '\.\/native-health-freshness'/.test(SOURCE),
  'app-athlete-state must import the shared native-health freshness helpers',
);
assert.ok(
  /freshness_hours:\s*number \| null;/.test(SOURCE)
    && /is_stale:\s*boolean;/.test(SOURCE)
    && /stale_threshold_hours:\s*number;/.test(SOURCE),
  'source_roles.native_health must expose freshness_hours, is_stale, stale_threshold_hours',
);
assert.ok(
  /freshness_hours: hoursSinceNativeHealthSync\(healthLastSyncAt\)/.test(SOURCE),
  'native_health.freshness_hours must come from hoursSinceNativeHealthSync(healthLastSyncAt)',
);
assert.ok(
  /is_stale: isNativeHealthSyncStale\(healthLastSyncAt\)/.test(SOURCE),
  'native_health.is_stale must come from isNativeHealthSyncStale(healthLastSyncAt)',
);
assert.ok(
  /stale_threshold_hours: NATIVE_HEALTH_STALE_HOURS/.test(SOURCE),
  'native_health.stale_threshold_hours must come from the shared constant',
);

console.log('AppAthleteState native-health source contract test passed.');
