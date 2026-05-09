/**
 * Static contract for Android Health Connect / native hub stale truth.
 *
 * The mobile component imports React Native at module scope, so this
 * test locks the source-level contract without booting a native runtime.
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

assert.ok(
  SOURCE.includes('const NATIVE_HEALTH_STALE_MS = 48 * 60 * 60 * 1000;'),
  'native health stale threshold must be explicit at 48h',
);
assert.ok(
  /function isNativeHealthSyncStale\(lastSyncAt: string \| null, nowMs = Date\.now\(\)\): boolean/.test(SOURCE),
  'HealthActionsPanel must derive stale state from lastSyncAt',
);
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
