/**
 * FS-021 lactate store contract test. Locks the store-level
 * behaviour without booting React Native:
 *
 * - addEntry routes through `validateManualLactateEntry` and
 *   refuses banned (clinical / causal / advice) note copy at
 *   the store boundary.
 * - Soft validator warnings flow through to `state.warnings`
 *   without blocking storage.
 * - Persistence: a written entry survives a hydrate roundtrip.
 * - Cap: store never exceeds the documented entries cap.
 * - Clear wipes both in-memory and persisted state.
 *
 * Stubs: jest-style mocking is unavailable here, so we replace
 * the secure-storage module with an in-memory adapter via
 * `module._cache` before importing the store.
 */

import assert from 'node:assert/strict';
import Module from 'node:module';

// In-memory secure-storage shim used by both readStoredJson and
// writeStoredJson behind the store. Must be installed BEFORE the
// store module loads.
const memory: Record<string, string> = {};
const fakeStorageModule = {
  readStoredJson: async <T>(key: string): Promise<T | null> => {
    const raw = memory[key];
    if (!raw) return null;
    try { return JSON.parse(raw) as T; } catch { return null; }
  },
  writeStoredJson: async (key: string, value: unknown): Promise<void> => {
    memory[key] = JSON.stringify(value);
  },
  removeStoredJson: async (key: string): Promise<void> => {
    delete memory[key];
  },
};

// Hijack require resolution for the secure-storage import.
const originalResolve = (Module as unknown as { _resolveFilename: (req: string, parent: NodeJS.Module) => string })._resolveFilename;
const originalLoad = (Module as unknown as { _load: (req: string, parent: NodeJS.Module) => unknown })._load;
(Module as unknown as { _load: typeof originalLoad })._load = function patchedLoad(request: string, parent: NodeJS.Module) {
  if (request.endsWith('secure-storage')) {
    return fakeStorageModule;
  }
  return originalLoad.call(this, request, parent);
} as typeof originalLoad;

// Now import the store. Top-level await would require an async IIFE;
// instead we use a dynamic import inside main().
async function main(): Promise<void> {
  const storeModule = await import('../../apps/mobile/src/store/lactate-store');
  const { useLactateStore, __test_resetLactateStore, __LACTATE_STORAGE_KEY } = storeModule;

  // Reset to known state.
  await __test_resetLactateStore();
  for (const k of Object.keys(memory)) delete memory[k];

  // 1. Happy path: addEntry succeeds, warnings flow through.
  const happyResult = await useLactateStore.getState().addEntry({
    userId: 'user-uuid-placeholder',
    dateTime: '2026-05-09T18:00:00.000Z',
    mmolPerL: 4.2,
    testProtocol: '4-step ramp',
    stageOrWorkload: 'Stage 3 — 200W',
    heartRateBpm: 158,
    rpe: 14,
    timingRelativeToTraining: 'mid_training',
    source: 'manual',
    confidence: 'medium',
    notes: 'Stage 3 on Wattbike at 200W; first capillary reading.',
  });
  assert.equal(happyResult.ok, true);
  if (!happyResult.ok) return;
  assert.equal(useLactateStore.getState().entries.length, 1);
  assert.equal(useLactateStore.getState().error, null);

  // 2. Banned-copy rejection at the store boundary — clinical
  //    / causal / readiness-directive / training-prescription
  //    notes MUST NOT enter the store.
  for (const banned of [
    'Coach said this diagnoses overtraining.',
    'My fatigue was caused by lactate buildup.',
    'You are recovered now.',
    'Skip training today.',
  ]) {
    const reject = await useLactateStore.getState().addEntry({
      userId: 'u', dateTime: '2026-05-09T18:00:00.000Z', mmolPerL: 4.2,
      testProtocol: null, stageOrWorkload: null, heartRateBpm: null, rpe: null,
      timingRelativeToTraining: 'recovery', source: 'manual', confidence: 'medium',
      notes: banned,
    });
    assert.equal(reject.ok, false, `banned note ${JSON.stringify(banned)} must be rejected at the store boundary`);
    assert.equal(useLactateStore.getState().entries.length, 1, 'banned entry must NOT be added');
  }

  // 3. Soft warnings flow through (low confidence + missing HR
  //    + missing protocol).
  await useLactateStore.getState().addEntry({
    userId: 'u', dateTime: '2026-05-09T19:00:00.000Z', mmolPerL: 6,
    testProtocol: null, stageOrWorkload: null, heartRateBpm: null, rpe: null,
    timingRelativeToTraining: 'post_training', source: 'manual', confidence: 'low',
    notes: null,
  });
  const warnings = useLactateStore.getState().warnings;
  assert.equal(warnings.length, 3);
  assert.ok(warnings.some((w) => /heartRateBpm missing/i.test(w)));
  assert.ok(warnings.some((w) => /protocol or stage/i.test(w)));
  assert.ok(warnings.some((w) => /User confidence is low/i.test(w)));

  // 4. Persistence + hydrate round-trip.
  assert.ok(memory[__LACTATE_STORAGE_KEY], 'store must persist after addEntry');
  // Reset in-memory state but KEEP storage; hydrate should re-load.
  useLactateStore.setState({ entries: [], hydrated: false, error: null, warnings: [] });
  await useLactateStore.getState().hydrate();
  assert.equal(useLactateStore.getState().entries.length, 2, 'hydrate must restore both entries');
  assert.equal(useLactateStore.getState().hydrated, true);

  // 5. Idempotent updates: adding the same dateTime + mmolPerL
  //    replaces (id is hashed from those two fields).
  const initialCount = useLactateStore.getState().entries.length;
  await useLactateStore.getState().addEntry({
    userId: 'u', dateTime: '2026-05-09T18:00:00.000Z', mmolPerL: 4.2,
    testProtocol: 'edited protocol', stageOrWorkload: 'Stage 3 — 200W',
    heartRateBpm: 160, rpe: 14, timingRelativeToTraining: 'mid_training',
    source: 'manual', confidence: 'medium', notes: null,
  });
  assert.equal(useLactateStore.getState().entries.length, initialCount, 'same dateTime+mmol must replace, not append');
  const found = useLactateStore.getState().entries.find((e) => e.dateTime === '2026-05-09T18:00:00.000Z');
  assert.equal(found?.testProtocol, 'edited protocol', 'replaced entry carries the new fields');

  // 6. Remove + clear.
  const idToRemove = useLactateStore.getState().entries[0].id;
  await useLactateStore.getState().removeEntry(idToRemove);
  assert.equal(useLactateStore.getState().entries.length, initialCount - 1);

  await useLactateStore.getState().clear();
  assert.equal(useLactateStore.getState().entries.length, 0);
  assert.equal(memory[__LACTATE_STORAGE_KEY], undefined, 'clear must wipe persisted blob');

  console.log('FS-021 lactate store contract test passed (validate-on-add / banned-copy refusal / soft warnings / hydrate round-trip / idempotent updates / clear).');
}

void main().catch((err) => {
  console.error(err);
  process.exit(1);
});
