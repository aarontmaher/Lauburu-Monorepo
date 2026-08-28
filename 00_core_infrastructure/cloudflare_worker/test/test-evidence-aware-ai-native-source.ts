/**
 * Coach prompt native-health source contract.
 *
 * Static contract test because the module depends on mobile runtime
 * imports. Locks that Coach context names the platform-native broad
 * baseline source instead of hard-coding iOS copy on Android.
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const SOURCE = fs.readFileSync(
  path.join(ROOT, 'apps/mobile/src/services/evidence-aware-ai.ts'),
  'utf8',
);

assert.match(
  SOURCE,
  /const nativeHealthRole = aas \? aas\.source_roles\.native_health : null;/,
  'Coach context must read source_roles.native_health from AppAthleteState',
);

assert.match(
  SOURCE,
  /`\s+\$\{nativeHealthRole\.label\}: \$\{nativeHealthRole\.role\}/,
  'Coach source-role summary must label Apple Health vs Health Connect from native_health',
);

assert.match(
  SOURCE,
  /Role conventions: \$\{nativeHealthRole\.label\} = broad baseline \+ history;/,
  'Coach role convention text must use the native health label',
);

assert.ok(
  !/`  Apple Health: \$\{aas\.source_roles\.apple_health\.role\}/.test(SOURCE),
  'Coach source-role summary must not hard-code Apple Health for the native broad-baseline line',
);

// v21 truth-label expansion — when the native source is stale, the
// Coach context must SAY SO INLINE so the model doesn't reason over
// stale "covers today" claims as if they were live. The phrase
// "STALE (last sync ...)" is the literal contract the model reads.
assert.ok(
  /\$\{nativeHealthRole\.is_stale\s*\?\s*` · STALE \(last sync \$\{nativeHealthRole\.freshness_hours\}h ago, threshold \$\{nativeHealthRole\.stale_threshold_hours\}h\)`/.test(SOURCE),
  'Coach native-source line must surface STALE + freshness_hours + threshold when is_stale is true',
);
assert.ok(
  /:\s*nativeHealthRole\.freshness_hours\s*!=\s*null\s*\?\s*` · synced \$\{nativeHealthRole\.freshness_hours\}h ago`\s*:\s*''/.test(SOURCE),
  'Coach native-source line must show synced-Nh-ago when fresh, no badge when no sync recorded',
);

console.log('Evidence-aware AI native-health source contract test passed.');
