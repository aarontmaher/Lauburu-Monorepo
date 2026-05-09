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

console.log('AppAthleteState native-health source contract test passed.');
