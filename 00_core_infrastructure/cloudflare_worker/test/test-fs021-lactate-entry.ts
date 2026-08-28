/**
 * FS-021 Phase 1 — manual lactate entry validator contract test.
 *
 * Locks the safety floor from
 * `docs/FS021_HEALTH_INPUTS_EXPANSION_SPEC.md` § 1 and § Safety
 * rules: clinical / causal / advice language cannot enter the
 * data layer; numeric ranges are enforced; the
 * "training context only" disclaimer is preserved.
 *
 * Repo-only. No EAS / TestFlight / Play / production release.
 */

import assert from 'node:assert/strict';
import {
  LACTATE_CONTEXT_ONLY_DISCLAIMER,
  validateManualLactateEntry,
  type ManualLactateEntryInput,
} from '../../packages/shared/src/journal/lactate-entry';

function happy(overrides: Partial<ManualLactateEntryInput> = {}): ManualLactateEntryInput {
  return {
    userId: 'user-uuid-placeholder',
    dateTime: '2026-05-09T18:00:00.000Z',
    mmolPerL: 4.2,
    testProtocol: '4-step ramp on Wattbike',
    stageOrWorkload: 'Stage 3 — 200W',
    heartRateBpm: 158,
    rpe: 14,
    timingRelativeToTraining: 'mid_training',
    source: 'manual',
    confidence: 'medium',
    notes: 'Stage 3 on Wattbike at 200W; first capillary reading.',
    ...overrides,
  };
}

function expectHappyPath(): void {
  const result = validateManualLactateEntry(happy());
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.entry.contextOnlyDisclaimer, LACTATE_CONTEXT_ONLY_DISCLAIMER);
  assert.equal(result.warnings.length, 0, 'happy path emits no warnings');
}

function expectMmolRangeFloor(): void {
  const high = validateManualLactateEntry(happy({ mmolPerL: 35 }));
  assert.equal(high.ok, false);
  if (!high.ok) assert.equal(high.field, 'mmolPerL');

  const negative = validateManualLactateEntry(happy({ mmolPerL: -1 }));
  assert.equal(negative.ok, false);
  if (!negative.ok) assert.equal(negative.field, 'mmolPerL');

  const nan = validateManualLactateEntry(happy({ mmolPerL: Number.NaN }));
  assert.equal(nan.ok, false);
}

function expectClinicalLanguageBanned(): void {
  // Each banned phrase must hard-reject; the spec's safety floor
  // is non-negotiable for the data layer.
  const cases: Array<{ note: string; expectedReasonPattern: RegExp }> = [
    { note: 'Coach said this diagnoses overtraining.', expectedReasonPattern: /clinical/i },
    { note: 'My fatigue was caused by lactate buildup.', expectedReasonPattern: /causal/i },
    { note: 'You are recovered now — train hard tomorrow.', expectedReasonPattern: /readiness/i },
    { note: 'Skip training today based on this reading.', expectedReasonPattern: /training-prescription/i },
  ];
  for (const c of cases) {
    const result = validateManualLactateEntry(happy({ notes: c.note }));
    assert.equal(result.ok, false, `note ${JSON.stringify(c.note)} must be rejected`);
    if (!result.ok) {
      assert.equal(result.field, 'notes');
      assert.match(result.reason, c.expectedReasonPattern);
    }
  }
}

function expectEnumValidation(): void {
  const badTiming = validateManualLactateEntry(happy({ timingRelativeToTraining: 'morning' as ManualLactateEntryInput['timingRelativeToTraining'] }));
  assert.equal(badTiming.ok, false);

  const badSource = validateManualLactateEntry(happy({ source: 'ble_device' as ManualLactateEntryInput['source'] }));
  assert.equal(badSource.ok, false);
  if (!badSource.ok) {
    // Anti-rule: BLE / device source is research-only per spec
    // § 1 phase 3 — must NOT be accepted by the manual validator.
    assert.equal(badSource.field, 'source');
  }

  const badConfidence = validateManualLactateEntry(happy({ confidence: 'unknown' as ManualLactateEntryInput['confidence'] }));
  assert.equal(badConfidence.ok, false);
}

function expectUserIdNotDefaulted(): void {
  // Spec § Safety rules: user-scoped data — validator must NOT
  // default userId to a shared placeholder. null is allowed for
  // offline drafts; empty string is rejected.
  const blank = validateManualLactateEntry(happy({ userId: '' }));
  assert.equal(blank.ok, false);
  if (!blank.ok) assert.equal(blank.field, 'userId');

  const nullDraft = validateManualLactateEntry(happy({ userId: null }));
  assert.equal(nullDraft.ok, true, 'null userId is allowed for offline draft staging');
}

function expectSoftWarningsSurfaceCorrectly(): void {
  // No HR + no protocol + low confidence → 3 warnings.
  const result = validateManualLactateEntry(happy({
    heartRateBpm: null,
    testProtocol: null,
    stageOrWorkload: null,
    confidence: 'low',
  }));
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.warnings.length, 3);
  assert.ok(result.warnings.some((w) => /heartRateBpm missing/i.test(w)));
  assert.ok(result.warnings.some((w) => /protocol or stage/i.test(w)));
  assert.ok(result.warnings.some((w) => /User confidence is low/i.test(w)));
}

function expectNumericFieldRanges(): void {
  const badHr = validateManualLactateEntry(happy({ heartRateBpm: 300 }));
  assert.equal(badHr.ok, false);
  if (!badHr.ok) assert.equal(badHr.field, 'heartRateBpm');

  const fractionalHr = validateManualLactateEntry(happy({ heartRateBpm: 158.5 }));
  assert.equal(fractionalHr.ok, false, 'heartRateBpm must be an integer');

  const badRpe = validateManualLactateEntry(happy({ rpe: 25 }));
  assert.equal(badRpe.ok, false);
  if (!badRpe.ok) assert.equal(badRpe.field, 'rpe');
}

function expectStringCaps(): void {
  const longProtocol = validateManualLactateEntry(happy({ testProtocol: 'a'.repeat(201) }));
  assert.equal(longProtocol.ok, false);
  const longNote = validateManualLactateEntry(happy({ notes: 'a'.repeat(501) }));
  assert.equal(longNote.ok, false);
}

function main(): void {
  expectHappyPath();
  expectMmolRangeFloor();
  expectClinicalLanguageBanned();
  expectEnumValidation();
  expectUserIdNotDefaulted();
  expectSoftWarningsSurfaceCorrectly();
  expectNumericFieldRanges();
  expectStringCaps();
  console.log('FS-021 manual lactate entry validator passed (spec safety floor + numeric ranges + enum gating + user-scope contract).');
}

main();
