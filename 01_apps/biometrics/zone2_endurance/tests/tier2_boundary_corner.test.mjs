/**
 * Tier 2: Boundary & Corner Cases Test Suite
 * 
 * Verifies:
 * 1. Extreme Biometric Ranges (DFA-alpha1 boundaries, high/low HR, zero values)
 * 2. Clinical Kamath 2004 20% Artifact Filter Rejection & Acceptance
 * 3. Lead Status Transitions & Zero-Mock Disconnection Resilience
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('Tier 2: Boundary & Corner Cases — Biometrics & Hardware Signals', () => {

  describe('2.1 Extreme DFA-alpha1 Physiological Ranges', () => {
    function classifyDfaZone(alpha1) {
      if (alpha1 >= 1.00) return 'ZONE_1';
      if (alpha1 >= 0.75) return 'ZONE_2';
      if (alpha1 >= 0.50) return 'ZONE_3';
      if (alpha1 >= 0.35) return 'ZONE_4';
      return 'ZONE_5';
    }

    it('Exact LT1 Aerobic Threshold boundary (alpha1 = 0.750) maps to ZONE_2', () => {
      assert.equal(classifyDfaZone(0.750), 'ZONE_2');
      assert.equal(classifyDfaZone(0.750001), 'ZONE_2');
      assert.equal(classifyDfaZone(0.749999), 'ZONE_3', 'Just below LT1 must cross into Zone 3 Tempo');
    });

    it('Exact LT2 Anaerobic Threshold boundary (alpha1 = 0.500) maps to ZONE_3', () => {
      assert.equal(classifyDfaZone(0.500), 'ZONE_3');
      assert.equal(classifyDfaZone(0.500001), 'ZONE_3');
      assert.equal(classifyDfaZone(0.499999), 'ZONE_4', 'Just below LT2 must cross into Zone 4 Threshold');
    });

    it('Upper Zone 2 boundary (alpha1 = 1.000) maps to ZONE_1 (Recovery)', () => {
      assert.equal(classifyDfaZone(1.000), 'ZONE_1');
      assert.equal(classifyDfaZone(0.999), 'ZONE_2', 'Just below 1.000 is top of Zone 2 Aerobic Corridor');
    });

    it('Extreme high resting DFA-alpha1 (alpha1 = 1.50) remains in ZONE_1', () => {
      assert.equal(classifyDfaZone(1.50), 'ZONE_1');
      assert.equal(classifyDfaZone(1.80), 'ZONE_1');
    });

    it('Extreme low anaerobic exhaustion DFA-alpha1 (alpha1 = 0.20) maps to ZONE_5', () => {
      assert.equal(classifyDfaZone(0.20), 'ZONE_5');
      assert.equal(classifyDfaZone(0.00), 'ZONE_5');
      assert.equal(classifyDfaZone(-0.10), 'ZONE_5');
    });
  });

  describe('2.2 Kamath 2004 20% Clinical RR Artifact Filter', () => {
    /**
     * Implements Kamath 2004 clinical filter:
     * |RR[i] - RR[i-1]| / RR[i-1] <= 0.20
     */
    function isKamathValid(prevRR, currentRR) {
      if (!prevRR || prevRR <= 0 || !currentRR || currentRR <= 0) return false;
      const diff = Math.abs(currentRR - prevRR);
      const ratio = diff / prevRR;
      return ratio <= 0.20;
    }

    function evaluateRRSequence(rrList) {
      if (!rrList || rrList.length < 2) return { validCount: 0, invalidCount: 0, artifactPct: 0 };
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
      return { validCount, invalidCount, artifactPct, isWindowValid: artifactPct <= 20.0 };
    }

    it('Normal sinus arrhythmia (RR variation <= 20%) is accepted as valid', () => {
      // 800ms -> 840ms (5% change)
      assert.equal(isKamathValid(800, 840), true);
      // 800ms -> 760ms (5% change)
      assert.equal(isKamathValid(800, 760), true);
      // 800ms -> 960ms (exactly 20.0% change)
      assert.equal(isKamathValid(800, 960), true);
      // 800ms -> 640ms (exactly 20.0% change)
      assert.equal(isKamathValid(800, 640), true);
    });

    it('Ectopic beats, PVCs, and noise spikes (> 20% jump) are rejected', () => {
      // 800ms -> 961ms (20.125% jump) -> rejected
      assert.equal(isKamathValid(800, 961), false);
      // 800ms -> 450ms (Premature Ventricular Contraction - 43.75% drop) -> rejected
      assert.equal(isKamathValid(800, 450), false);
      // 450ms -> 1100ms (Compensatory pause - 144% jump) -> rejected
      assert.equal(isKamathValid(450, 1100), false);
    });

    it('High-artifact window (> 20% total rejected beats) flags window as invalid', () => {
      // 10 intervals with 4 ectopic spikes (40% artifact rate)
      const noisySequence = [800, 810, 420, 1050, 820, 830, 400, 1120, 810, 825];
      const result = evaluateRRSequence(noisySequence);
      
      assert.ok(result.invalidCount >= 4, 'Must identify at least 4 invalid jumps');
      assert.ok(result.artifactPct > 20.0, 'Artifact percentage must exceed 20%');
      assert.equal(result.isWindowValid, false, 'Window must be flagged as invalid for DFA calculation');
    });

    it('Clean aerobic base window (<= 20% artifact rate) flags window as valid', () => {
      // 10 intervals with smooth endurance rhythm (0% artifact rate)
      const cleanSequence = [750, 755, 748, 752, 760, 758, 754, 750, 753, 756];
      const result = evaluateRRSequence(cleanSequence);
      
      assert.equal(result.invalidCount, 0);
      assert.equal(result.artifactPct, 0.0);
      assert.equal(result.isWindowValid, true);
    });
  });

  describe('2.3 Lead Status & Zero-Mock Sensor Disconnection States', () => {
    const leadStatuses = ['CONNECTED', 'DISCONNECTED', 'NOISY', 'POOR_CONTACT', 'OFF_BODY'];

    function sanitizeBiometricDisplay(summary, leadStatus) {
      if (leadStatus === 'DISCONNECTED' || leadStatus === 'OFF_BODY') {
        return {
          heartRateDisplay: '--',
          dfaAlpha1Display: '--',
          statusBanner: 'Sensor Disconnected / Off Body',
          isLive: false,
        };
      }
      if (leadStatus === 'NOISY' || leadStatus === 'POOR_CONTACT') {
        return {
          heartRateDisplay: summary.heartRate > 0 ? String(summary.heartRate) : '--',
          dfaAlpha1Display: summary.currentDfaAlpha1 > 0 ? summary.currentDfaAlpha1.toFixed(2) : '--',
          statusBanner: 'Noisy Contact / Adjust Electrode',
          isLive: true,
        };
      }
      return {
        heartRateDisplay: String(summary.heartRate),
        dfaAlpha1Display: summary.currentDfaAlpha1.toFixed(2),
        statusBanner: 'Signal Optimal',
        isLive: true,
      };
    }

    it('All 5 standard lead statuses are handled deterministically', () => {
      for (const status of leadStatuses) {
        const dummySummary = { heartRate: 142, currentDfaAlpha1: 0.84 };
        const result = sanitizeBiometricDisplay(dummySummary, status);
        assert.ok(result.statusBanner.length > 0, `Status banner must exist for ${status}`);
      }
    });

    it('When sensor is DISCONNECTED or OFF_BODY, UI renders clean uninitialized indicators (zero-mock)', () => {
      const summary = { heartRate: 142, currentDfaAlpha1: 0.84 };
      const disconnectedResult = sanitizeBiometricDisplay(summary, 'DISCONNECTED');
      
      assert.equal(disconnectedResult.heartRateDisplay, '--', 'Must NOT display fake heart rate when disconnected');
      assert.equal(disconnectedResult.dfaAlpha1Display, '--', 'Must NOT display fake DFA-a1 when disconnected');
      assert.equal(disconnectedResult.isLive, false);

      const offBodyResult = sanitizeBiometricDisplay(summary, 'OFF_BODY');
      assert.equal(offBodyResult.heartRateDisplay, '--');
      assert.equal(offBodyResult.dfaAlpha1Display, '--');
      assert.equal(offBodyResult.isLive, false);
    });

    it('When sensor is CONNECTED with optimal contact, UI renders authentic live metrics', () => {
      const summary = { heartRate: 138, currentDfaAlpha1: 0.88 };
      const connectedResult = sanitizeBiometricDisplay(summary, 'CONNECTED');

      assert.equal(connectedResult.heartRateDisplay, '138');
      assert.equal(connectedResult.dfaAlpha1Display, '0.88');
      assert.equal(connectedResult.statusBanner, 'Signal Optimal');
      assert.equal(connectedResult.isLive, true);
    });
  });
});
