/**
 * Lock the legacy SourceSheetRow status string → canonical
 * TruthLabel mapping. This contract is consumed by
 * `apps/mobile/src/components/HealthActionsPanel.tsx` after the
 * Manage Sources sheet migrated to `SourceChip`. The chip only
 * renders one of the eight canonical TruthLabel strings — if a
 * future status string lands in HealthActionsPanel without an
 * explicit mapping it falls back to `'missing'` (the safe
 * never-overclaim default), but the test here pins the *expected*
 * mappings so silent regressions on the known set are caught.
 */

import {
  HC_DID_NOT_REGISTER_STATUS,
  SOURCE_SHEET_STATUS_TO_TRUTH_LABEL,
  mapSourceSheetStatusToTruthLabel,
} from '../../apps/mobile/src/components/primitives/source-status-mapper';
import { TRUTH_LABELS, type TruthLabel } from '../../apps/mobile/src/components/primitives/_helpers';

function assertEq<T>(actual: T, expected: T, label: string): void {
  if (actual !== expected) {
    throw new Error(`[FAIL] ${label}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`);
  }
}

function expectAll(): void {
  const expectations: Array<[string, TruthLabel]> = [
    // Apple Health / Health Connect
    ['Connected', 'live'],
    ['Connected — no data', 'seed/provisional'],
    ['Sync failed — retry', 'stale'],
    ['Permission needed', 'setup required'],
    ['Sync needed', 'setup required'],
    // Android Health Connect — app-not-listed-with-HC fallback.
    [HC_DID_NOT_REGISTER_STATUS, 'setup required'],
    // WHOOP Direct
    ['Awaiting cycle', 'live'],
    ['Partial', 'seed/provisional'],
    ['Reconnect required', 'setup required'],
    ['Setup required', 'setup required'],
    ['Not connected', 'missing'],
    ['Stale', 'stale'],
    ['Unknown', 'missing'],
  ];
  if (HC_DID_NOT_REGISTER_STATUS !== 'Health Connect did not register') {
    throw new Error(`[FAIL] HC_DID_NOT_REGISTER_STATUS drifted from the literal HealthActionsPanel writes; got ${JSON.stringify(HC_DID_NOT_REGISTER_STATUS)}`);
  }
  for (const [input, expected] of expectations) {
    assertEq(mapSourceSheetStatusToTruthLabel(input), expected, `mapSourceSheetStatusToTruthLabel(${JSON.stringify(input)})`);
  }
}

function expectFallback(): void {
  // Anti-rule: unknown phrasings MUST fall back to 'missing', not
  // 'live'. The chip should never claim connectivity for a string
  // it does not recognise.
  assertEq(mapSourceSheetStatusToTruthLabel('Greenlit'), 'missing', 'unknown string falls back to missing');
  assertEq(mapSourceSheetStatusToTruthLabel(''), 'missing', 'empty string falls back to missing');
  assertEq(mapSourceSheetStatusToTruthLabel('connected'), 'missing', 'lowercase variant is not silently equated');
}

function expectAllOutputsAreCanonical(): void {
  const allowed: ReadonlySet<string> = new Set<string>(TRUTH_LABELS);
  for (const [input, label] of Object.entries(SOURCE_SHEET_STATUS_TO_TRUTH_LABEL)) {
    if (!allowed.has(label)) {
      throw new Error(`[FAIL] mapping for ${JSON.stringify(input)} produced non-canonical label ${JSON.stringify(label)}`);
    }
  }
}

function main(): void {
  expectAll();
  expectFallback();
  expectAllOutputsAreCanonical();
  console.log('test-source-sheet-status-mapper OK');
}

main();
