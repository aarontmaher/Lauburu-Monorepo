/**
 * Static contract for Android Health Connect / native hub stale truth.
 *
 * The mobile component imports React Native at module scope, so this
 * test locks the source-level contract without booting a native
 * runtime. The 48h threshold + helper now live in the shared
 * `services/native-health-freshness` module so the Manage Sources
 * sheet, the Coach AI evidence builder, and the home widget all
 * read from one definition. The panel must IMPORT the helper, not
 * redeclare it.
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const SOURCE = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/components/HealthActionsPanel.tsx'),
  'utf8',
);
const MAPPER = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/components/primitives/source-status-mapper.ts'),
  'utf8',
);
const FRESHNESS_HELPER = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/services/native-health-freshness.ts'),
  'utf8',
);

// Helper module is the canonical source of truth for the 48h threshold.
assert.ok(
  /export const NATIVE_HEALTH_STALE_HOURS = 48;/.test(FRESHNESS_HELPER),
  'native-health-freshness must export NATIVE_HEALTH_STALE_HOURS = 48',
);
assert.ok(
  /export const NATIVE_HEALTH_STALE_MS = NATIVE_HEALTH_STALE_HOURS \* 60 \* 60 \* 1000;/.test(FRESHNESS_HELPER),
  'native-health-freshness must derive NATIVE_HEALTH_STALE_MS from the hours constant',
);
assert.ok(
  /export function isNativeHealthSyncStale\(\s*lastSyncAt: string \| null \| undefined,/.test(FRESHNESS_HELPER),
  'native-health-freshness must export isNativeHealthSyncStale',
);
assert.ok(
  /export function hoursSinceNativeHealthSync\(/.test(FRESHNESS_HELPER),
  'native-health-freshness must export hoursSinceNativeHealthSync for Coach context',
);

// The panel must IMPORT the helper rather than redeclare the threshold.
assert.ok(
  /import \{[^}]*isNativeHealthSyncStale[^}]*\} from '..\/services\/native-health-freshness';/s.test(SOURCE),
  'HealthActionsPanel must import isNativeHealthSyncStale from native-health-freshness',
);
assert.ok(
  !/const NATIVE_HEALTH_STALE_MS\s*=\s*48 \* 60 \* 60 \* 1000;/.test(SOURCE),
  'HealthActionsPanel must NOT redeclare a local NATIVE_HEALTH_STALE_MS — drift territory',
);

// Surface contract — unchanged from babb98b: panel still uses
// nativeHealthSyncStale to render the right label first.
assert.ok(
  /nativeHealthSyncStale\s*\?\s*'Stale'\s*:\s*appleHealthConnected/s.test(SOURCE),
  'Manage Sources native row must show Stale before Connected when lastSyncAt is old',
);
assert.ok(
  /appleHealthConnected\s*\?\s*nativeHealthSyncStale\s*\?\s*'stale'\s*:\s*'connected'/s.test(SOURCE),
  'top HealthActionsPanel hub summary must say stale before connected',
);
assert.ok(
  /'Stale': 'stale'/.test(MAPPER),
  'SourceSheetRow mapper must convert Stale status to the canonical stale chip',
);

console.log('Health Connect / native hub stale truth contract test passed.');
