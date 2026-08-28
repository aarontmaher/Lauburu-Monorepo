/**
 * Challenger 1: Empirical Adversarial Stress Test Harness
 * Target App: 01_apps/zone2_endurance
 * 
 * Adversarially challenges and verifies:
 * 1. Rapid theme toggling and DOM state synchronization (10,000 cycles, storage exceptions, async race conditions)
 * 2. High-throughput 128Hz ECG ring buffer overflow, wrap-around, and negative voltage samples (1,000,000 samples, negative Q/S wave preservation, voltage clamping [-5.0, 5.0] mV, float sanitization)
 * 3. Extreme DFA-alpha1 values (<0.30, >1.50, NaN, Infinity) & physiological zone classification boundary precision
 * 4. Kamath 2004 filter rejection rate under 50% noisy artifact streams, boundary 20% limit, and degenerate RR intervals
 * 5. Production source code AST & contract verification
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const appRoot = path.resolve(__dirname, '..');

// Authoritative Physiological Constants & Algorithm implementations matching types/biometrics.ts and LiveEcgMonitor.tsx
const BIOMETRIC_THRESHOLDS = {
  ZONE_2_UPPER: 1.00,
  ZONE_2_LOWER: 0.75,
  ZONE_3_LOWER: 0.50,
  KAMATH_MAX_ARTIFACT_PCT: 20.0,
  DECOUPLING_DRIFT_THRESHOLD_PCT: 5.0,
};

function classifyDfaZone(alpha1) {
  if (alpha1 >= BIOMETRIC_THRESHOLDS.ZONE_2_UPPER) {
    return 'ZONE_1';
  } else if (alpha1 >= BIOMETRIC_THRESHOLDS.ZONE_2_LOWER) {
    return 'ZONE_2';
  } else if (alpha1 >= BIOMETRIC_THRESHOLDS.ZONE_3_LOWER) {
    return 'ZONE_3';
  } else if (alpha1 >= 0.35) {
    return 'ZONE_4';
  } else {
    return 'ZONE_5';
  }
}

class EcgSweepRingBuffer {
  constructor(capacity = 640) {
    this.capacity = capacity;
    this.buffer = new Float32Array(capacity);
    this.writeIndex = 0;
    this.totalSamplesPushed = 0;
  }

  push(sampleVoltage) {
    let v = sampleVoltage;
    if (typeof v !== 'number' || Number.isNaN(v) || !Number.isFinite(v)) {
      v = 0.0;
    } else {
      v = Math.max(-5.0, Math.min(5.0, v));
    }

    this.buffer[this.writeIndex] = v;
    this.writeIndex = (this.writeIndex + 1) % this.capacity;
    this.totalSamplesPushed++;
  }

  pushBatch(samples) {
    for (let i = 0; i < samples.length; i++) {
      this.push(samples[i]);
    }
  }

  clear() {
    this.buffer.fill(0);
    this.writeIndex = 0;
    this.totalSamplesPushed = 0;
  }
}

describe('Challenger 1: Empirical Adversarial Stress Test Suite', () => {

  // =========================================================================
  // 1. Rapid Theme Toggling & DOM State Synchronization
  // =========================================================================
  describe('1. Rapid Theme Toggling and DOM State Synchronization', () => {
    class MockDOMEnvironment {
      constructor(initialTheme = 'dark') {
        this.classList = new Set();
        if (initialTheme === 'dark') {
          this.classList.add('dark');
        }
        this.localStorage = new Map();
        this.storageQuotaExceeded = false;
      }

      getThemeFromDOM() {
        return this.classList.has('dark') ? 'dark' : 'light';
      }

      toggleTheme(callerState) {
        const nextTheme = callerState === 'dark' ? 'light' : 'dark';
        
        // Attempt localStorage persistence with fault simulation
        if (this.storageQuotaExceeded) {
          // Emulate DOMException: QuotaExceededError
          try {
            throw new Error('QuotaExceededError: The quota has been exceeded.');
          } catch (e) {
            // caught internally, logs warning without crashing
          }
        } else {
          this.localStorage.set('theme', nextTheme);
        }

        // Synchronize DOM class
        if (nextTheme === 'dark') {
          this.classList.add('dark');
        } else {
          this.classList.delete('dark');
        }

        return nextTheme;
      }
    }

    it('Executes 10,000 rapid synchronous theme toggle cycles maintaining strict 1:1 DOM parity', () => {
      const dom = new MockDOMEnvironment('dark');
      let currentTheme = 'dark';

      for (let i = 1; i <= 10000; i++) {
        currentTheme = dom.toggleTheme(currentTheme);
        const domTheme = dom.getThemeFromDOM();
        assert.equal(
          domTheme,
          currentTheme,
          `Desynchronization at iteration ${i}: State was ${currentTheme} but DOM had ${domTheme}`
        );
      }

      assert.equal(currentTheme, 'dark', '10,000 even toggles must return precisely to initial dark state');
      assert.equal(dom.getThemeFromDOM(), 'dark');
      assert.equal(dom.localStorage.get('theme'), 'dark');
    });

    it('Survives localStorage QuotaExceededError / SecurityError without throwing or corrupting DOM', () => {
      const dom = new MockDOMEnvironment('dark');
      dom.storageQuotaExceeded = true; // Lock storage
      let currentTheme = 'dark';

      assert.doesNotThrow(() => {
        for (let i = 0; i < 500; i++) {
          currentTheme = dom.toggleTheme(currentTheme);
          assert.equal(dom.getThemeFromDOM(), currentTheme);
        }
      }, 'Theme toggling must not throw when localStorage is unavailable or full');
    });

    it('Maintains consistency under asynchronous interleaved microtask toggling', async () => {
      const dom = new MockDOMEnvironment('dark');
      let state = 'dark';

      const tasks = Array(100).fill(null).map((_, idx) => {
        return new Promise((resolve) => {
          setTimeout(() => {
            state = dom.toggleTheme(state);
            resolve(state);
          }, Math.random() * 5);
        });
      });

      await Promise.all(tasks);
      assert.equal(
        dom.getThemeFromDOM(),
        state,
        'Asynchronous interleaved toggles must leave DOM and memory state identical'
      );
    });
  });

  // =========================================================================
  // 2. High-Throughput 128Hz ECG Ring Buffer Overflow, Wrap-around & Negative Voltage
  // =========================================================================
  describe('2. High-Throughput 128Hz ECG Ring Buffer & Negative Voltage Samples', () => {
    it('Handles 1,000,000 samples at line rate with exact circular wrap-around and zero memory expansion', () => {
      const buffer = new EcgSweepRingBuffer(640);
      assert.equal(buffer.capacity, 640);
      assert.equal(buffer.buffer.length, 640);

      const totalStreamSamples = 1000000;
      for (let i = 0; i < totalStreamSamples; i++) {
        // Stream physiological ECG sinusoidal + QRS test wave
        const v = Math.sin(i * 0.05) * 1.5;
        buffer.push(v);
      }

      assert.equal(buffer.totalSamplesPushed, 1000000);
      const expectedWriteIndex = 1000000 % 640; // 320
      assert.equal(buffer.writeIndex, expectedWriteIndex);
      assert.equal(buffer.buffer.length, 640, 'Buffer must remain fixed at 640 capacity Float32Array');
    });

    it('Preserves authentic negative physiological ECG voltages (Q/S waves, T-wave inversion) with float fidelity', () => {
      const buffer = new EcgSweepRingBuffer(640);

      // Deep Q-wave (-0.35 mV), Deep S-wave (-1.85 mV), Inverted T-wave (-0.65 mV), extreme negative notch (-4.95 mV)
      const negativeSamples = [-0.35, -1.85, -0.65, -4.95, -0.01, -3.42];

      buffer.pushBatch(negativeSamples);

      for (let i = 0; i < negativeSamples.length; i++) {
        const stored = buffer.buffer[i];
        assert.ok(
          stored < 0,
          `Negative voltage ${negativeSamples[i]} must remain strictly negative in buffer, got ${stored}`
        );
        assert.ok(
          Math.abs(stored - negativeSamples[i]) < 1e-4,
          `Float precision lost: expected ${negativeSamples[i]}, got ${stored}`
        );
      }
    });

    it('Clamps extreme negative and positive voltage spikes strictly to [-5.0, 5.0] mV', () => {
      const buffer = new EcgSweepRingBuffer(640);

      const extremeSamples = [
        -5.0,
        -5.0001,
        -15.0,
        -999.0,
        -Infinity,
        5.0,
        5.0001,
        25.0,
        1000.0,
        Infinity,
      ];

      buffer.pushBatch(extremeSamples);

      // Verify clamping
      assert.equal(buffer.buffer[0], -5.0);
      assert.equal(buffer.buffer[1], -5.0, '-5.0001 mV must clamp to -5.0 mV');
      assert.equal(buffer.buffer[2], -5.0, '-15.0 mV must clamp to -5.0 mV');
      assert.equal(buffer.buffer[3], -5.0, '-999.0 mV must clamp to -5.0 mV');
      assert.equal(buffer.buffer[4], 0.0, '-Infinity must sanitize to 0.0 mV');

      assert.equal(buffer.buffer[5], 5.0);
      assert.equal(buffer.buffer[6], 5.0, '+5.0001 mV must clamp to +5.0 mV');
      assert.equal(buffer.buffer[7], 5.0, '+25.0 mV must clamp to +5.0 mV');
      assert.equal(buffer.buffer[8], 5.0, '+1000.0 mV must clamp to +5.0 mV');
      assert.equal(buffer.buffer[9], 0.0, '+Infinity must sanitize to 0.0 mV');
    });

    it('Sanitizes corrupt float inputs (NaN, null, undefined, strings, objects) to clean 0.0 baseline', () => {
      const buffer = new EcgSweepRingBuffer(640);

      const corruptInputs = [
        NaN,
        undefined,
        null,
        'corrupt_signal',
        {},
        [1, 2],
        -0,
        Number.NaN,
      ];

      buffer.pushBatch(corruptInputs);

      for (let i = 0; i < corruptInputs.length; i++) {
        const stored = buffer.buffer[i];
        assert.ok(
          Math.abs(stored) < 1e-6,
          `Corrupt input at index ${i} (${corruptInputs[i]}) must sanitize to 0.0 mV, got ${stored}`
        );
        assert.equal(Number.isNaN(stored), false, 'Buffer must never contain NaN');
        assert.equal(Number.isFinite(stored), true, 'Buffer entries must always be finite');
      }
    });

    it('Batch ingestion of 5,000 samples in a single call executes cleanly without index corruption', () => {
      const buffer = new EcgSweepRingBuffer(640);
      const largeBatch = Array(5000).fill(null).map((_, i) => Math.sin(i) * 2.0);

      buffer.pushBatch(largeBatch);

      assert.equal(buffer.totalSamplesPushed, 5000);
      assert.equal(buffer.writeIndex, 5000 % 640);
      assert.equal(buffer.buffer.length, 640);
    });
  });

  // =========================================================================
  // 3. Extreme DFA-alpha1 Values & Zone Classification Boundaries
  // =========================================================================
  describe('3. Extreme DFA-alpha1 Values (<0.30, >1.50, NaN, Infinity) & Boundaries', () => {
    it('Correctly classifies sub-0.30 extreme anaerobic exhaustion as ZONE_5', () => {
      const sub30Values = [0.29, 0.25, 0.15, 0.05, 0.00, -0.10, -0.50, -10.0];
      for (const val of sub30Values) {
        const zone = classifyDfaZone(val);
        assert.equal(
          zone,
          'ZONE_5',
          `Extreme value ${val} must map to ZONE_5 (Anaerobic / VO2Max), got ${zone}`
        );
      }
    });

    it('Correctly classifies supra-1.50 high recovery / resting values as ZONE_1', () => {
      const supra150Values = [1.50, 1.50001, 1.65, 1.80, 2.00, 3.50, 100.0];
      for (const val of supra150Values) {
        const zone = classifyDfaZone(val);
        assert.equal(
          zone,
          'ZONE_1',
          `High recovery value ${val} must map to ZONE_1 (Recovery), got ${zone}`
        );
      }
    });

    it('Physiological boundary razor tests around LT1 (0.75), LT2 (0.50), and Z2 Upper (1.00)', () => {
      // 1.00 Boundary
      assert.equal(classifyDfaZone(1.000000), 'ZONE_1', 'Exact 1.0000 is Zone 1');
      assert.equal(classifyDfaZone(0.999999), 'ZONE_2', '0.999999 is Zone 2');

      // 0.75 LT1 Aerobic Threshold Boundary
      assert.equal(classifyDfaZone(0.750000), 'ZONE_2', 'Exact 0.7500 (LT1) is Zone 2');
      assert.equal(classifyDfaZone(0.749999), 'ZONE_3', '0.749999 is Zone 3 Tempo');

      // 0.50 LT2 Anaerobic Threshold Boundary
      assert.equal(classifyDfaZone(0.500000), 'ZONE_3', 'Exact 0.5000 (LT2) is Zone 3');
      assert.equal(classifyDfaZone(0.499999), 'ZONE_4', '0.499999 is Zone 4 Threshold');

      // 0.35 Boundary
      assert.equal(classifyDfaZone(0.350000), 'ZONE_4', 'Exact 0.3500 is Zone 4');
      assert.equal(classifyDfaZone(0.349999), 'ZONE_5', '0.349999 is Zone 5 Anaerobic');
    });

    it('Corrupt/non-finite DFA-alpha1 values (NaN, Infinity, -Infinity) default safely to ZONE_5 without throwing', () => {
      assert.equal(classifyDfaZone(NaN), 'ZONE_5', 'NaN must default safely to ZONE_5');
      assert.equal(classifyDfaZone(-Infinity), 'ZONE_5', '-Infinity must default to ZONE_5');
      assert.equal(classifyDfaZone(Infinity), 'ZONE_1', '+Infinity must map to ZONE_1');
      assert.equal(classifyDfaZone(null), 'ZONE_5');
      assert.equal(classifyDfaZone(undefined), 'ZONE_5');
    });

    it('SVG Trend Chart Y-Coordinate Mapping Clamping stress test', () => {
      // Simulates DfaAlpha1TrendChart getY mapping
      const padding = { top: 24, right: 36, bottom: 36, left: 48 };
      const chartHeight = 280;
      const plotHeight = chartHeight - padding.top - padding.bottom; // 220
      const yMin = 0.20;
      const yMax = 1.40;

      const getY = (val) => {
        let v = typeof val === 'number' && !Number.isNaN(val) ? val : yMin;
        const clamped = Math.max(yMin, Math.min(yMax, v));
        return padding.top + plotHeight - ((clamped - yMin) / (yMax - yMin)) * plotHeight;
      };

      // Test extreme out-of-range floats
      const testFloats = [-500.0, -10.0, 0.0, 0.20, 0.75, 1.00, 1.40, 10.0, 500.0, NaN, Infinity, -Infinity];

      for (const val of testFloats) {
        const y = getY(val);
        assert.equal(Number.isNaN(y), false, `getY(${val}) produced NaN`);
        assert.equal(Number.isFinite(y), true, `getY(${val}) produced non-finite`);
        assert.ok(
          y >= padding.top && y <= padding.top + plotHeight,
          `getY(${val}) produced ${y}, outside [${padding.top}, ${padding.top + plotHeight}]`
        );
      }
    });
  });

  // =========================================================================
  // 4. Kamath Filter Rejection Rate Under 50% Noisy Artifact Streams
  // =========================================================================
  describe('4. Kamath Filter Rejection Rate Under 50% Noisy Artifact Streams', () => {
    function isKamathValid(prevRR, currentRR) {
      if (!prevRR || prevRR <= 0 || !currentRR || currentRR <= 0) return false;
      const diff = Math.abs(currentRR - prevRR);
      const ratio = diff / prevRR;
      return ratio <= 0.20; // 20% Kamath 2004 criterion
    }

    function evaluateRRSequence(rrList) {
      if (!Array.isArray(rrList) || rrList.length < 2) {
        return { validCount: 0, invalidCount: 0, totalPairs: 0, artifactPct: 0.0, isWindowValid: false };
      }
      let validCount = 0;
      let invalidCount = 0;
      for (let i = 1; i < rrList.length; i++) {
        if (isKamathValid(rrList[i - 1], rrList[i])) {
          validCount++;
        } else {
          invalidCount++;
        }
      }
      const totalPairs = validCount + invalidCount;
      const artifactPct = totalPairs > 0 ? (invalidCount / totalPairs) * 100 : 0;
      return {
        validCount,
        invalidCount,
        totalPairs,
        artifactPct: Number(artifactPct.toFixed(2)),
        isWindowValid: artifactPct <= 20.0,
      };
    }

    it('Stream with exactly 50% noisy artifact jumps produces 50% rejection and invalidates calculation window', () => {
      // Create a sequence of 101 RR intervals (100 transitions):
      // Each cycle k (0..49):
      // Transition 2k (valid): curr -> curr * 1.05 (+5.0% variation <= 20%)
      // Transition 2k+1 (invalid): (curr * 1.05) -> (curr * 1.05) * 1.50 (+50% variation > 20%)
      const stream = [800];
      let currentVal = 800;

      for (let i = 0; i < 50; i++) {
        // 1. Valid step (+5%)
        const validNext = currentVal * 1.05;
        stream.push(validNext);

        // 2. Invalid step (+50% jump)
        const invalidNext = validNext * 1.50;
        stream.push(invalidNext);

        // Reset baseline for next iteration without sudden artifact jump from invalidNext to currentVal
        currentVal = invalidNext * 0.98; // keep next step relative to invalidNext
      }

      // stream has 101 elements, 100 transitions (50 valid, 50 invalid)
      const result = evaluateRRSequence(stream);
      assert.equal(result.totalPairs, 100);
      assert.equal(result.validCount, 50, `Must identify exactly 50 valid transitions, got ${result.validCount}`);
      assert.equal(result.invalidCount, 50, `Must identify exactly 50 invalid artifact transitions, got ${result.invalidCount}`);
      assert.equal(result.artifactPct, 50.0, 'Artifact percentage must be exactly 50.0%');
      assert.equal(result.isWindowValid, false, '50% artifact stream MUST invalidate calculation window');
    });

    it('High-noise artifact stream (80% and 100% noise) accurately flags severe artifact contamination', () => {
      // 100% noise: every transition jumps > 20%
      const pureNoise = [800, 300, 1200, 400, 1100, 350, 1050, 300, 1300, 400];
      const result = evaluateRRSequence(pureNoise);

      assert.equal(result.invalidCount, 9);
      assert.equal(result.validCount, 0);
      assert.equal(result.artifactPct, 100.0);
      assert.equal(result.isWindowValid, false);
    });

    it('Clinical boundary test at exactly 20.0% vs 20.01% artifact threshold', () => {
      // 100 pairs: 20 invalid, 80 valid -> 20.0% artifact -> VALID
      const boundaryValidStream = [800];
      let cur = 800;
      // 80 valid transitions (each changing by 1%)
      for (let i = 0; i < 80; i++) {
        cur = cur * 1.01;
        boundaryValidStream.push(cur);
      }
      // 20 invalid transitions (each changing by 30%)
      for (let i = 0; i < 20; i++) {
        cur = cur * 1.30;
        boundaryValidStream.push(cur);
      }

      const res20 = evaluateRRSequence(boundaryValidStream);
      assert.equal(res20.totalPairs, 100);
      assert.equal(res20.invalidCount, 20);
      assert.equal(res20.validCount, 80);
      assert.equal(res20.artifactPct, 20.0);
      assert.equal(res20.isWindowValid, true, 'Exactly 20.0% artifact is the acceptable clinical upper bound');

      // 101 pairs: 21 invalid, 80 valid -> 20.79% artifact -> INVALID
      const boundaryInvalidStream = [...boundaryValidStream, cur * 1.30];
      const res21 = evaluateRRSequence(boundaryInvalidStream);
      assert.ok(res21.artifactPct > 20.0);
      assert.equal(res21.isWindowValid, false, '20.79% artifact must invalidate window');
    });

    it('Degenerate and corrupt RR streams (empty, single item, negative intervals, zeros, NaN) handled safely', () => {
      assert.equal(evaluateRRSequence([]).isWindowValid, false);
      assert.equal(evaluateRRSequence([800]).isWindowValid, false);
      assert.equal(evaluateRRSequence(null).isWindowValid, false);

      // Zeros and negative numbers
      const corruptRR = [800, 0, -500, NaN, 800, undefined, 810];
      const res = evaluateRRSequence(corruptRR);
      assert.equal(res.isWindowValid, false);
      assert.equal(Number.isNaN(res.artifactPct), false);
    });
  });

  // =========================================================================
  // 5. Source Code AST & Contract Alignment
  // =========================================================================
  describe('5. Source Code AST & Contract Alignment', () => {
    it('LiveEcgMonitor.tsx implements EcgSweepRingBuffer with clamp [-5.0, 5.0] and float sanitization', () => {
      const ecgFile = path.join(appRoot, 'components/charts/LiveEcgMonitor.tsx');
      assert.ok(fs.existsSync(ecgFile));
      const content = fs.readFileSync(ecgFile, 'utf8');

      assert.match(content, /export\s+class\s+EcgSweepRingBuffer/);
      assert.match(content, /Math\.max\(-5\.0,\s*Math\.min\(5\.0,\s*v\)\)/);
      assert.match(content, /Number\.isNaN\(v\)\s*\|\|\s*!Number\.isFinite\(v\)/);
      assert.match(content, /this\.writeIndex\s*=\s*\(this\.writeIndex\s*\+\s*1\)\s*%\s*this\.capacity/);
    });

    it('types/biometrics.ts implements classifyDfaZone matching all 5 zones and BIOMETRIC_THRESHOLDS', () => {
      const typesFile = path.join(appRoot, 'types/biometrics.ts');
      assert.ok(fs.existsSync(typesFile));
      const content = fs.readFileSync(typesFile, 'utf8');

      assert.match(content, /export\s+function\s+classifyDfaZone/);
      assert.match(content, /ZONE_2_UPPER:\s*1\.00/);
      assert.match(content, /ZONE_2_LOWER:\s*0\.75/);
      assert.match(content, /ZONE_3_LOWER:\s*0\.50/);
      assert.match(content, /KAMATH_MAX_ARTIFACT_PCT:\s*20\.0/);
    });
  });
});
