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

console.log('Evidence-aware AI native-health source contract test passed.');
