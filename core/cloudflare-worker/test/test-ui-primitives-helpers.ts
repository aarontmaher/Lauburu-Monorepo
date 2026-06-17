/**
 * UI primitives pure-helper contract.
 *
 * Locks the rules in
 * apps/mobile/src/components/primitives/_helpers.ts:
 *   - TRUTH_LABELS exposes the canonical six truth labels plus
 *     two UI-only states ('missing', 'stale').
 *   - mapTruthLabelToTone returns the right tone for every label.
 *   - mapConfidenceToTone covers the four canonical levels +
 *     unknown.
 *   - readinessBandFromScore: null/non-finite → 'provisional';
 *     67+ → 'high'; 34..66 → 'medium'; <34 → 'low'.
 *   - readinessBandColour is total over all bands.
 *
 * The .ts source compiles via tsx — no React Native imports here.
 */

// @ts-expect-error - .ts module imported into TS test
import {
  TRUTH_LABELS,
  TONE_COLOURS,
  mapTruthLabelToTone,
  mapConfidenceToTone,
  readinessBandFromScore,
  readinessBandColour,
} from '../../apps/mobile/src/components/primitives/_helpers';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

// ── TRUTH_LABELS catalogue ──────────────────────────────────────────

const expectedLabels = [
  'live',
  'synced from hub',
  'imported summary',
  'seed/provisional',
  'setup required',
  'planned',
  'missing',
  'stale',
];
assert(JSON.stringify([...TRUTH_LABELS]) === JSON.stringify(expectedLabels), 'TRUTH_LABELS matches the canonical eight');

// ── mapTruthLabelToTone ─────────────────────────────────────────────

assert(mapTruthLabelToTone('live') === 'fresh', 'live → fresh');
assert(mapTruthLabelToTone('synced from hub') === 'fresh', 'synced from hub → fresh');
assert(mapTruthLabelToTone('imported summary') === 'info', 'imported summary → info');
assert(mapTruthLabelToTone('seed/provisional') === 'provisional', 'seed/provisional → provisional');
assert(mapTruthLabelToTone('setup required') === 'warning', 'setup required → warning');
assert(mapTruthLabelToTone('planned') === 'neutral', 'planned → neutral');
assert(mapTruthLabelToTone('stale') === 'warning', 'stale → warning');
assert(mapTruthLabelToTone('missing') === 'neutral', 'missing → neutral');
assert(mapTruthLabelToTone(undefined) === 'neutral', 'undefined → neutral');
assert(mapTruthLabelToTone(null as any) === 'neutral', 'null → neutral');
assert(mapTruthLabelToTone('not-a-label' as any) === 'neutral', 'unknown → neutral');

// ── mapConfidenceToTone ─────────────────────────────────────────────

assert(mapConfidenceToTone('high') === 'fresh', 'high → fresh');
assert(mapConfidenceToTone('medium') === 'info', 'medium → info');
assert(mapConfidenceToTone('low') === 'warning', 'low → warning');
assert(mapConfidenceToTone('provisional') === 'provisional', 'provisional → provisional');
assert(mapConfidenceToTone('unknown') === 'neutral', 'unknown → neutral');
assert(mapConfidenceToTone(null) === 'neutral', 'null → neutral');
assert(mapConfidenceToTone(undefined) === 'neutral', 'undefined → neutral');

// ── readinessBandFromScore ──────────────────────────────────────────

assert(readinessBandFromScore(null) === 'provisional', 'null → provisional');
assert(readinessBandFromScore(undefined) === 'provisional', 'undefined → provisional');
assert(readinessBandFromScore(NaN) === 'provisional', 'NaN → provisional');
assert(readinessBandFromScore(Infinity) === 'provisional', 'Infinity → provisional');
assert(readinessBandFromScore(-1) === 'low', '-1 → low');
assert(readinessBandFromScore(0) === 'low', '0 → low');
assert(readinessBandFromScore(33) === 'low', '33 → low');
assert(readinessBandFromScore(34) === 'medium', '34 → medium (boundary)');
assert(readinessBandFromScore(50) === 'medium', '50 → medium');
assert(readinessBandFromScore(66) === 'medium', '66 → medium');
assert(readinessBandFromScore(67) === 'high', '67 → high (boundary)');
assert(readinessBandFromScore(85) === 'high', '85 → high');
assert(readinessBandFromScore(100) === 'high', '100 → high');
assert(readinessBandFromScore(120) === 'high', '120 → high (over-cap is still high; caller responsible for clamping)');

// ── readinessBandColour total over all bands ────────────────────────

const allBands = ['high', 'medium', 'low', 'provisional'] as const;
for (const band of allBands) {
  const colour = readinessBandColour(band);
  assert(typeof colour === 'string' && colour.length > 0, `${band} has a colour`);
  assert(colour.startsWith('#') || colour.startsWith('rgb'), `${band} colour is hex/rgb`);
}

// ── TONE_COLOURS map covers every tone ──────────────────────────────

const tones = ['fresh', 'warning', 'danger', 'neutral', 'info', 'provisional'] as const;
for (const tone of tones) {
  const palette = TONE_COLOURS[tone];
  assert(typeof palette?.fg === 'string' && palette.fg.length > 0, `tone ${tone} has fg`);
  assert(typeof palette?.bg === 'string' && palette.bg.length > 0, `tone ${tone} has bg`);
}

console.log('UI primitives helpers contract test passed.');
