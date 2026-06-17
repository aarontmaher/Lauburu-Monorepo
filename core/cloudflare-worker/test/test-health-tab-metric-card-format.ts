/**
 * Health tab HRV → MetricCard migration contract test
 * (per docs/UI_PRIMITIVES_INTEGRATION_GUIDE.md § 3 step 2).
 *
 * Locks the rule that the call site at
 * `apps/mobile/app/(tabs)/health.tsx` pre-formats the value
 * string before passing it to MetricCard. The primitive itself
 * does no fallback formatting — missing values MUST render as
 * the literal string '—'.
 *
 * Repo-only QA. No EAS / TestFlight / Play / production release.
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('../..', import.meta.url).pathname);
const HEALTH = fs.readFileSync(path.join(ROOT, 'apps/mobile/app/(tabs)/health.tsx'), 'utf8');
const PRIMITIVE = fs.readFileSync(path.join(ROOT, 'apps/mobile/src/components/primitives/MetricCard.tsx'), 'utf8');

// 1. The call site imports the primitive.
assert.ok(
  HEALTH.includes("import { MetricCard } from '../../src/components/primitives/MetricCard'"),
  'health.tsx must import the MetricCard primitive (NOT relative path that bypasses the index)',
);

// 2. The HRV tile is wired to MetricCard (NOT MetricBox).
const hrvSlot = HEALTH.match(/<MetricCard[\s\S]*?label="HRV"[\s\S]*?\/>/);
assert.ok(hrvSlot, 'health.tsx must render <MetricCard label="HRV" .../>');

// 3. The value prop carries a pre-formatted ternary that produces
//    a string — either a number formatted to 1 decimal or the
//    literal '—'. This is the integration guide's anti-rule:
//    caller pre-formats; the card does no fallback.
assert.ok(
  /value=\{today\.hrv_ms != null \? `\$\{Math\.round\(today\.hrv_ms \* 10\) \/ 10\}` : '—'\}/.test(hrvSlot![0]),
  "MetricCard's value prop must be the pre-formatted ternary `today.hrv_ms != null ? `${Math.round(today.hrv_ms * 10) / 10}` : '—'`",
);

// 4. The unit prop stays 'ms'.
assert.ok(/unit="ms"/.test(hrvSlot![0]), "HRV MetricCard unit must remain 'ms'");

// 5. The card's source prop is intentionally absent — adding a
//    'live' chip without a freshness probe would over-claim.
//    Locking the omission here so a future "let me add a green
//    chip" tweak fails the test until the freshness probe lands.
assert.ok(!/sourceState=/.test(hrvSlot![0]), 'MetricCard sourceState MUST stay omitted until a freshness probe is wired');

// 6. The MetricCard primitive itself does NOT do conditional
//    fallback formatting (the card renders `value` verbatim).
//    Locking this in the primitive source keeps the contract
//    even if a future maintainer is tempted to add a fallback.
assert.ok(
  PRIMITIVE.includes('<Text style={styles.value} numberOfLines={1}>{value}</Text>'),
  'MetricCard must render `value` verbatim — no in-component fallback formatting',
);
assert.ok(
  !/value\s*\?\?/.test(PRIMITIVE) && !/value\s*\|\|/.test(PRIMITIVE),
  'MetricCard MUST NOT default `value` to a fallback string inside the primitive',
);

// 7. The other tiles (Resting HR, Sleep, Active Cal) stay on
//    legacy MetricBox per the integration guide's "ONE Health tab
//    visual change at a time" anti-rule. If a future commit
//    swaps another tile prematurely, this assertion fires.
const otherTilesPattern = /<MetricBox label="(Resting HR|Sleep|Active Cal)"/g;
const otherTiles = [...HEALTH.matchAll(otherTilesPattern)];
assert.equal(otherTiles.length, 3, 'Resting HR / Sleep / Active Cal MUST stay on legacy MetricBox until a separate migration commit lands');

console.log('Health tab HRV MetricCard migration contract test passed.');
