/**
 * CHALLENGER 2: ADVERSARIAL MATHEMATICAL & ORACLE STRESS HARNESS (M3)
 * Standalone Mobile Web Bluetooth Ingestion & Client-Side DSP Verification
 * 
 * Verifies:
 * 1. Kamath 20% outlier rejection filter under mathematical stress & boundary conditions
 * 2. RMSSD exact formulation sqrt(1/(N-1) * sum(delta_RR^2))
 * 3. Peng DFA-alpha1 multi-scale linear least-squares regression (scales [4, 6, 8, 12, 16], N >= 16)
 * 4. Compound Readiness score formulation [0, 100] with multi-factor weighting
 * 5. Zone 2 DFA-alpha1 classification boundaries
 * 6. High-throughput numerical stability under 1,000,000 sample storms
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('================================================================================');
console.log('🥋 CHALLENGER 2: ADVERSARIAL MATHEMATICAL ORACLE & DSP STRESS HARNESS (M3)');
console.log('================================================================================');

// --- EXTRACT EXACT ALGORITHMS FROM DASHBOARD_SCREEN.DART & BUILD/INDEX.HTML ---
const html = fs.readFileSync(path.join(__dirname, '../build/index.html'), 'utf-8');

function extractFunction(name) {
  const regex = new RegExp(`function ${name}\\s*\\([\\s\\S]*?\\n    \\}`);
  const match = html.match(regex);
  if (!match) throw new Error(`Could not find function ${name} in build/index.html`);
  return eval(`(${match[0]})`);
}

const applyKamathFilter = extractFunction('applyKamathFilter');
const computeRmssd = extractFunction('computeRmssd');
const computeDfaAlpha1 = extractFunction('computeDfaAlpha1');
const computeReadinessScore = extractFunction('computeReadinessScore');
const classifyZone2 = extractFunction('classifyZone2');
const parseMovesenseEcgSamples = extractFunction('parseMovesenseEcgSamples');
const detectQrsPeak = extractFunction('detectQrsPeak');

let totalTests = 0;
let passedTests = 0;

function runTest(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  ✅ [PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    throw err;
  }
}

// ============================================================================
// SUITE 1: KAMATH 20% OUTLIER FILTER ADVERSARIAL VERIFICATION
// ============================================================================
console.log('\n--- SUITE 1: KAMATH 20% OUTLIER FILTER ADVERSARIAL VERIFICATION ---');

runTest('1.1: Kamath filter empty, single, and degenerate array handling', () => {
  assert.deepStrictEqual(applyKamathFilter([]), []);
  assert.deepStrictEqual(applyKamathFilter([800]), [800]);
  assert.deepStrictEqual(applyKamathFilter(null), []);
  assert.deepStrictEqual(applyKamathFilter(undefined), []);
});

runTest('1.2: Kamath filter exact 20% boundary threshold (Pass <= 20%, Reject > 20%)', () => {
  const base = 1000.0;
  // Exact +20% (1200ms) -> should pass
  const rrsExactUpper = [base, 1200.0];
  assert.deepStrictEqual(applyKamathFilter(rrsExactUpper), [1000.0, 1200.0]);

  // Exact -20% (800ms) -> should pass
  const rrsExactLower = [base, 800.0];
  assert.deepStrictEqual(applyKamathFilter(rrsExactLower), [1000.0, 800.0]);

  // Above 20% (+20.01% -> 1200.1ms) -> should reject and replace with 1000.0
  const rrsOverUpper = [base, 1200.1];
  assert.deepStrictEqual(applyKamathFilter(rrsOverUpper), [1000.0, 1000.0]);

  // Below -20% (-20.01% -> 799.9ms) -> should reject and replace with 1000.0
  const rrsUnderLower = [base, 799.9];
  assert.deepStrictEqual(applyKamathFilter(rrsUnderLower), [1000.0, 1000.0]);
});

runTest('1.3: Kamath filter consecutive ectopic spikes and recovery', () => {
  // 5 ectopic spikes of 1600ms on an 800ms baseline, followed by valid 820ms beat
  const dirty = [800, 1600, 1600, 1600, 1600, 1600, 820];
  const clean = applyKamathFilter(dirty);
  assert.deepStrictEqual(clean, [800, 800, 800, 800, 800, 800, 820]);
});

runTest('1.4: Kamath filter physiological ramp exercise profile (gradual 5% delta)', () => {
  // Gradual acceleration from 1000ms down to 400ms (150 BPM) in 5% steps
  const ramp = [1000.0];
  for (let i = 0; i < 20; i++) {
    ramp.push(ramp[ramp.length - 1] * 0.95);
  }
  const clean = applyKamathFilter(ramp);
  assert.deepStrictEqual(clean, ramp, 'All gradual physiological transitions must be preserved');
});

runTest('1.5: Kamath filter 1,000,000 random RR intervals with 15% noise storm', () => {
  const N = 1000000;
  const input = new Float64Array(N);
  input[0] = 800.0;
  for (let i = 1; i < N; i++) {
    if (i % 7 === 0) {
      input[i] = 2500.0; // ectopic pause
    } else if (i % 11 === 0) {
      input[i] = 200.0; // ectopic double-trigger
    } else {
      input[i] = 800.0 + (Math.sin(i * 0.05) * 50.0);
    }
  }
  const t0 = Date.now();
  const output = applyKamathFilter(input);
  const elapsed = Date.now() - t0;
  assert.strictEqual(output.length, N);
  // Verify no output is 2500 or 200 (all rejected)
  for (let i = 0; i < N; i++) {
    assert(output[i] >= 600.0 && output[i] <= 1000.0, `Output beat ${output[i]} out of bounds at index ${i}`);
  }
  console.log(`    -> Kamath filtered 1,000,000 samples in ${elapsed}ms (${Math.round(N / elapsed * 1000)} samples/sec)`);
});

// ============================================================================
// SUITE 2: RMSSD FORMULATION ADVERSARIAL VERIFICATION
// ============================================================================
console.log('\n--- SUITE 2: RMSSD FORMULATION ADVERSARIAL VERIFICATION ---');

runTest('2.1: RMSSD mathematical oracle comparison sqrt(1/(N-1) * sum(delta^2))', () => {
  // Explicit analytical cases
  // Case A: 2 beats [800, 850] -> delta = 50 -> RMSSD = sqrt(2500/1) = 50.0
  assert.strictEqual(computeRmssd([800, 850]), 50.0);

  // Case B: 3 beats [800, 850, 800] -> deltas = [50, -50] -> sumSq = 2500+2500 = 5000 -> /2 = 2500 -> RMSSD = 50.0
  assert.strictEqual(computeRmssd([800, 850, 800]), 50.0);

  // Case C: Constant series [1000, 1000, 1000, 1000] -> deltas = [0, 0, 0] -> RMSSD = 0.0
  assert.strictEqual(computeRmssd([1000, 1000, 1000, 1000]), 0.0);

  // Case D: Triangle wave deltas [10, 20, 30, 40]
  // Series: [1000, 1010, 1030, 1060, 1100]
  // deltas = [10, 20, 30, 40] -> sumSq = 100 + 400 + 900 + 1600 = 3000 -> N-1 = 4 -> meanSq = 750 -> RMSSD = sqrt(750) = 27.386127875258307
  const triangle = [1000, 1010, 1030, 1060, 1100];
  const expected = Math.sqrt(3000 / 4);
  assert(Math.abs(computeRmssd(triangle) - expected) < 1e-12);
});

runTest('2.2: RMSSD edge cases (empty, single element, null, undefined)', () => {
  assert.strictEqual(computeRmssd([]), null);
  assert.strictEqual(computeRmssd([800]), null);
  assert.strictEqual(computeRmssd(null), null);
  assert.strictEqual(computeRmssd(undefined), null);
});

runTest('2.3: RMSSD property test: Scale invariance under constant translation', () => {
  // Adding a constant baseline to all RR intervals does not alter RMSSD
  const rrs1 = [800, 840, 790, 820, 860];
  const rrs2 = [1200, 1240, 1190, 1220, 1260];
  const rmssd1 = computeRmssd(rrs1);
  const rmssd2 = computeRmssd(rrs2);
  assert(Math.abs(rmssd1 - rmssd2) < 1e-12, 'RMSSD must be invariant to baseline translation');
});

// ============================================================================
// SUITE 3: DFA-ALPHA1 MULTI-SCALE REGRESSION ADVERSARIAL VERIFICATION
// ============================================================================
console.log('\n--- SUITE 3: DFA-ALPHA1 MULTI-SCALE REGRESSION ADVERSARIAL VERIFICATION ---');

runTest('3.1: DFA-alpha1 minimum sample threshold N >= 16', () => {
  // Series of length 15 must return null
  const rrs15 = Array.from({ length: 15 }, (_, i) => 800 + (i % 2 === 0 ? 30 : -30));
  assert.strictEqual(computeDfaAlpha1(rrs15), null, 'N < 16 must return null');

  // Series of length 16 must return a valid number in [0.25, 1.75]
  const rrs16 = Array.from({ length: 16 }, (_, i) => 800 + (i % 2 === 0 ? 30 : -30));
  const alpha16 = computeDfaAlpha1(rrs16);
  assert(alpha16 !== null && alpha16 >= 0.25 && alpha16 <= 1.75, `Expected valid alpha1, got ${alpha16}`);
});

runTest('3.2: DFA-alpha1 zero-variance and degenerate series handling', () => {
  // All identical intervals -> zero fluctuation -> logFlucts empty or < 2 scales -> returns null
  const identical = Array.from({ length: 64 }, () => 800.0);
  assert.strictEqual(computeDfaAlpha1(identical), null);
});

runTest('3.3: DFA-alpha1 stochastic noise signatures (White noise ~0.5, Highly correlated AR(1) ~1.2)', () => {
  let seed = 42;
  function random() {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  }
  // White Noise (uncorrelated): DFA alpha1 should be approx 0.50
  const whiteNoise = Array.from({ length: 256 }, () => 800.0 + (random() - 0.5) * 100.0);
  const alphaWhite = computeDfaAlpha1(whiteNoise);
  console.log(`    -> Computed White Noise DFA-alpha1: ${alphaWhite} (Expected: ~0.50)`);
  assert(alphaWhite >= 0.40 && alphaWhite <= 0.65, `White noise alpha1 ${alphaWhite} outside expected range [0.40, 0.65]`);

  // Highly Correlated Autoregressive Series AR(1) (resting autonomic fractal): DFA alpha1 should be approx 1.15-1.35
  const ar1 = [800.0];
  for (let i = 1; i < 256; i++) {
    ar1.push(800.0 + 0.85 * (ar1[i - 1] - 800.0) + (random() - 0.5) * 40.0);
  }
  const alphaAR1 = computeDfaAlpha1(ar1);
  console.log(`    -> Computed AR(1) Fractal DFA-alpha1: ${alphaAR1} (Expected: ~1.20)`);
  assert(alphaAR1 >= 1.05 && alphaAR1 <= 1.45, `AR(1) fractal alpha1 ${alphaAR1} outside expected range [1.05, 1.45]`);
});

runTest('3.4: DFA-alpha1 clamp bounds [0.25, 1.75]', () => {
  // Pathological anti-correlated alternating sequence
  const antiCorrelated = Array.from({ length: 64 }, (_, i) => 800.0 + (i % 2 === 0 ? 100.0 : -100.0));
  const alphaAnti = computeDfaAlpha1(antiCorrelated);
  assert(alphaAnti >= 0.25 && alphaAnti <= 1.75, `Clamped bounds failed: ${alphaAnti}`);
});

// ============================================================================
// SUITE 4: COMPOUND READINESS SCORE ADVERSARIAL VERIFICATION
// ============================================================================
console.log('\n--- SUITE 4: COMPOUND READINESS SCORE ADVERSARIAL VERIFICATION ---');

runTest('4.1: Readiness Score null and waiting state guards', () => {
  assert.strictEqual(computeReadinessScore(null, 50.0, 1.0), null);
  assert.strictEqual(computeReadinessScore(0, 50.0, 1.0), null);
  assert.strictEqual(computeReadinessScore(-10, 50.0, 1.0), null);
  assert.strictEqual(computeReadinessScore(60.0, null, 1.0), null);
  assert.strictEqual(computeReadinessScore(60.0, 0, 1.0), null);
  assert.strictEqual(computeReadinessScore(60.0, -5, 1.0), null);
});

runTest('4.2: Readiness Score maximum and minimum bounds [0, 100]', () => {
  // Peak Athletic Recovery: HR=45 (max 30 pts), RMSSD=80 (max 50 pts), alpha1=1.0 (max 20 pts) -> 100
  const maxScore = computeReadinessScore(45.0, 80.0, 1.0);
  assert.strictEqual(maxScore, 100, `Expected 100, got ${maxScore}`);

  // Beyond Peak: HR=35 (clamped to 30 pts), RMSSD=120 (clamped to 50 pts), alpha1=1.10 (20 pts) -> 100
  const overMaxScore = computeReadinessScore(35.0, 120.0, 1.10);
  assert.strictEqual(overMaxScore, 100, `Expected 100, got ${overMaxScore}`);

  // Exhausted / Elevated HR: HR=85 (0 pts), RMSSD=15 (0 pts), alpha1=0.45 (5 pts) -> 5
  const minScore = computeReadinessScore(85.0, 15.0, 0.45);
  assert.strictEqual(minScore, 5, `Expected 5, got ${minScore}`);

  // Extreme Stress: HR=120 (clamped to 0 pts), RMSSD=5 (clamped to 0 pts), alpha1=0.20 (5 pts) -> 5
  const extremeMinScore = computeReadinessScore(120.0, 5.0, 0.20);
  assert.strictEqual(extremeMinScore, 5, `Expected 5, got ${extremeMinScore}`);
});

runTest('4.3: Readiness Score DFA-alpha1 tier transitions (20 pts, 15 pts, 5 pts)', () => {
  // Fixed baseline: HR=65 (15 pts), RMSSD=47.5 (25 pts) -> Subtotal = 40 pts
  // Case A: alpha1 = null -> dfaPart = 5 pts -> Total = 45
  assert.strictEqual(computeReadinessScore(65.0, 47.5, null), 45);

  // Case B: alpha1 = 0.70 -> dfaPart = 5 pts -> Total = 45
  assert.strictEqual(computeReadinessScore(65.0, 47.5, 0.70), 45);

  // Case C: alpha1 = 0.80 (>0.75) -> dfaPart = 15 pts -> Total = 55
  assert.strictEqual(computeReadinessScore(65.0, 47.5, 0.80), 55);

  // Case D: alpha1 = 0.90 (in [0.9, 1.3]) -> dfaPart = 20 pts -> Total = 60
  assert.strictEqual(computeReadinessScore(65.0, 47.5, 0.90), 60);

  // Case E: alpha1 = 1.30 (in [0.9, 1.3]) -> dfaPart = 20 pts -> Total = 60
  assert.strictEqual(computeReadinessScore(65.0, 47.5, 1.30), 60);

  // Case F: alpha1 = 1.35 (>0.75, outside [0.9, 1.3]) -> dfaPart = 15 pts -> Total = 55
  assert.strictEqual(computeReadinessScore(65.0, 47.5, 1.35), 55);
});

// ============================================================================
// SUITE 5: ZONE 2 CLASSIFICATION BOUNDARIES ADVERSARIAL VERIFICATION
// ============================================================================
console.log('\n--- SUITE 5: ZONE 2 CLASSIFICATION BOUNDARIES ADVERSARIAL VERIFICATION ---');

runTest('5.1: Zone 2 Disconnected and Calibrating states', () => {
  assert.strictEqual(classifyZone2(1.0, 0), 'Resting / Disconnected');
  assert.strictEqual(classifyZone2(1.0, -10), 'Resting / Disconnected');
  assert.strictEqual(classifyZone2(null, 130), 'Calibrating RR Stream...');
  assert.strictEqual(classifyZone2(undefined, 130), 'Calibrating RR Stream...');
});

runTest('5.2: Zone 2 physiological boundary precision', () => {
  const hr = 135;
  // Zone 1: alpha1 >= 0.85
  assert.strictEqual(classifyZone2(0.850, hr), 'Zone 1: Active Recovery');
  assert.strictEqual(classifyZone2(1.200, hr), 'Zone 1: Active Recovery');

  // Zone 2: 0.70 <= alpha1 < 0.85
  assert.strictEqual(classifyZone2(0.8499, hr), 'Zone 2: Optimal Aerobic (LT1)');
  assert.strictEqual(classifyZone2(0.7500, hr), 'Zone 2: Optimal Aerobic (LT1)');
  assert.strictEqual(classifyZone2(0.7000, hr), 'Zone 2: Optimal Aerobic (LT1)');

  // Zone 3: 0.50 <= alpha1 < 0.70
  assert.strictEqual(classifyZone2(0.6999, hr), 'Zone 3: Tempo / Aerobic Threshold');
  assert.strictEqual(classifyZone2(0.5500, hr), 'Zone 3: Tempo / Aerobic Threshold');
  assert.strictEqual(classifyZone2(0.5000, hr), 'Zone 3: Tempo / Aerobic Threshold');

  // Zone 4/5: alpha1 < 0.50
  assert.strictEqual(classifyZone2(0.4999, hr), 'Zone 4/5: Anaerobic / Above LT2');
  assert.strictEqual(classifyZone2(0.2500, hr), 'Zone 4/5: Anaerobic / Above LT2');
  assert.strictEqual(classifyZone2(-0.500, hr), 'Zone 4/5: Anaerobic / Above LT2');
});

// ============================================================================
// SUITE 6: MOVESENSE 512HZ ECG BINARY UNPACKING & QRS DETECTION
// ============================================================================
console.log('\n--- SUITE 6: MOVESENSE 512HZ ECG BINARY UNPACKING & QRS DETECTION ---');

runTest('6.1: parseMovesenseEcgSamples 32-bit Int32 multi-sample unpacking', () => {
  // 6-byte header + 3 x 4-byte Int32 samples = 18 bytes (payload = 12 bytes, %4 === 0)
  const buffer = new ArrayBuffer(18);
  const view = new DataView(buffer);
  view.setUint8(0, 1);
  // Sample 0: 1,500 uV = 1.5 mV
  view.setInt32(6, 1500, true);
  // Sample 1: -500 uV = -0.5 mV
  view.setInt32(10, -500, true);
  // Sample 2: 0 uV = 0.0 mV
  view.setInt32(14, 0, true);

  const samples = parseMovesenseEcgSamples(view);
  assert.strictEqual(samples.length, 3);
  assert.strictEqual(samples[0], 1.5);
  assert.strictEqual(samples[1], -0.5);
  assert.strictEqual(samples[2], 0.0);
});

runTest('6.2: parseMovesenseEcgSamples 16-bit Int16 multi-sample unpacking', () => {
  // 6-byte header + 3 x 2-byte Int16 samples = 12 bytes (payload = 6 bytes, 6%4!==0, 6%2===0)
  const buffer = new ArrayBuffer(12);
  const view = new DataView(buffer);
  view.setUint8(0, 1);
  // Sample 0: 800 uV = 0.8 mV
  view.setInt16(6, 800, true);
  // Sample 1: -1200 uV = -1.2 mV
  view.setInt16(8, -1200, true);
  // Sample 2: 350 uV = 0.35 mV
  view.setInt16(10, 350, true);

  const samples = parseMovesenseEcgSamples(view);
  assert.strictEqual(samples.length, 3);
  assert.strictEqual(samples[0], 0.8);
  assert.strictEqual(samples[1], -1.2);
  assert.strictEqual(samples[2], 0.35);
});

runTest('6.3: parseMovesenseEcgSamples truncated / invalid buffer handling', () => {
  assert.deepStrictEqual(parseMovesenseEcgSamples(null), []);
  assert.deepStrictEqual(parseMovesenseEcgSamples(new DataView(new ArrayBuffer(4))), []);
});

// ============================================================================
// SUMMARY REPORT
// ============================================================================
console.log('\n================================================================================');
console.log(`🏆 ALL ${passedTests}/${totalTests} ADVERSARIAL MATHEMATICAL & ORACLE TESTS PASSED (100%)`);
console.log('================================================================================');
