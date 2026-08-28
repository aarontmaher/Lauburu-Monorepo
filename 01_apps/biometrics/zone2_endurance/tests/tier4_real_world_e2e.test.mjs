/**
 * Tier 4: Real-World Application Scenarios Test Suite
 * 
 * Verifies:
 * 1. Full 60-Minute Zone 2 Endurance Session Simulation (Streaming RR, dynamic DFA-a1 transitions)
 * 2. Aerobic Decoupling (Pw:HR Drift %) Split-Half Durability Computation
 * 3. 128Hz Oscilloscope Canvas Sweep Circular Ring Buffer (640 Samples, 25 mm/s)
 */

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('Tier 4: Real-World Application Scenarios — Endurance Session Simulation', () => {

  describe('4.1 Full 60-Minute Multi-Phase Zone 2 Workout Simulation', () => {
    function classifyDfaZone(alpha1) {
      if (alpha1 >= 1.00) return 'ZONE_1';
      if (alpha1 >= 0.75) return 'ZONE_2';
      if (alpha1 >= 0.50) return 'ZONE_3';
      if (alpha1 >= 0.35) return 'ZONE_4';
      return 'ZONE_5';
    }

    it('Simulates complete 60-min physiological progression and accumulates Time-in-Zone', () => {
      // 60 minutes session, 1 sample per minute
      const sessionTimeline = [];

      // Phase 1: Warmup (Minutes 1-10) -> Zone 1 Recovery
      for (let m = 1; m <= 10; m++) {
        sessionTimeline.push({ minute: m, hr: 110 + m, dfaAlpha1: 1.15 - (m * 0.012), power: 130 + (m * 2) });
      }

      // Phase 2: Steady State Aerobic Base (Minutes 11-40, 30 min) -> Zone 2 [0.75 - 1.00]
      for (let m = 11; m <= 40; m++) {
        sessionTimeline.push({ minute: m, hr: 138 + (m % 4), dfaAlpha1: 0.88 - ((m - 10) * 0.003), power: 180 });
      }

      // Phase 3: Tempo Hill Surge (Minutes 41-48, 8 min) -> Zone 3 Tempo (DFA-a1 < 0.75)
      for (let m = 41; m <= 48; m++) {
        sessionTimeline.push({ minute: m, hr: 158 + (m % 5), dfaAlpha1: 0.68 - ((m - 40) * 0.015), power: 230 });
      }

      // Phase 4: Recovery Back to Zone 2 (Minutes 49-55, 7 min) -> Zone 2 Re-entry
      for (let m = 49; m <= 55; m++) {
        sessionTimeline.push({ minute: m, hr: 140 - (m % 3), dfaAlpha1: 0.81 + ((m - 48) * 0.01), power: 175 });
      }

      // Phase 5: Cool Down (Minutes 56-60, 5 min) -> Zone 1 Recovery
      for (let m = 56; m <= 60; m++) {
        sessionTimeline.push({ minute: m, hr: 115 - ((m - 55) * 3), dfaAlpha1: 1.10 + ((m - 55) * 0.03), power: 110 });
      }

      assert.equal(sessionTimeline.length, 60, 'Total session duration must be 60 minutes');

      // Accumulate Time in Zone
      const timeInZoneSeconds = {
        ZONE_1: 0,
        ZONE_2: 0,
        ZONE_3: 0,
        ZONE_4: 0,
        ZONE_5: 0,
      };

      for (const pt of sessionTimeline) {
        const zone = classifyDfaZone(pt.dfaAlpha1);
        timeInZoneSeconds[zone] += 60; // 60 seconds per minute point
      }

      // Assertions on accumulated duration
      assert.ok(timeInZoneSeconds.ZONE_2 >= 2220, `Zone 2 duration (${timeInZoneSeconds.ZONE_2}s) must be >= 37 minutes (2220s)`);
      assert.ok(timeInZoneSeconds.ZONE_1 >= 900, `Zone 1 duration (${timeInZoneSeconds.ZONE_1}s) must be >= 15 minutes (900s)`);
      assert.ok(timeInZoneSeconds.ZONE_3 >= 480, `Zone 3 duration (${timeInZoneSeconds.ZONE_3}s) must be >= 8 minutes (480s)`);
    });
  });

  describe('4.2 Aerobic Decoupling (Pw:HR Drift %) Split-Half Computation', () => {
    /**
     * Standard Joe Friel / Coggan Aerobic Decoupling Formula:
     * Split 1 Efficiency Factor (EF1) = Avg Power (Split 1) / Avg HR (Split 1)
     * Split 2 Efficiency Factor (EF2) = Avg Power (Split 2) / Avg HR (Split 2)
     * Decoupling % = ((EF1 / EF2) - 1) * 100
     */
    function calculateAerobicDecoupling(split1Samples, split2Samples) {
      const avgP1 = split1Samples.reduce((sum, s) => sum + s.power, 0) / split1Samples.length;
      const avgH1 = split1Samples.reduce((sum, s) => sum + s.hr, 0) / split1Samples.length;
      const ef1 = avgP1 / avgH1;

      const avgP2 = split2Samples.reduce((sum, s) => sum + s.power, 0) / split2Samples.length;
      const avgH2 = split2Samples.reduce((sum, s) => sum + s.hr, 0) / split2Samples.length;
      const ef2 = avgP2 / avgH2;

      const decouplingPct = ((ef1 / ef2) - 1) * 100;
      return {
        ef1,
        ef2,
        decouplingPct: Number(decouplingPct.toFixed(2)),
        isDecoupled: decouplingPct > 5.0, // > 5% indicates cardiac drift / aerobic decoupling
      };
    }

    it('Well-trained aerobic base maintains cardiac decoupling below 5.0% threshold', () => {
      // First 30 min: Power 180W, HR 138 bpm -> EF1 = 1.304
      const split1 = Array(30).fill(null).map(() => ({ power: 180, hr: 138 }));
      // Second 30 min: Power 180W, HR 142 bpm -> EF2 = 1.268 (mild cardiac drift)
      const split2 = Array(30).fill(null).map(() => ({ power: 180, hr: 142 }));

      const result = calculateAerobicDecoupling(split1, split2);
      assert.ok(result.decouplingPct >= 2.0 && result.decouplingPct <= 4.0, `Decoupling % was ${result.decouplingPct}%`);
      assert.equal(result.isDecoupled, false, 'Cardiac drift under 5% is acceptable in Zone 2 base training');
    });

    it('Severe cardiac drift (> 5.0% decoupling) flags aerobic decoupling warning', () => {
      // First 30 min: Power 180W, HR 135 bpm
      const split1 = Array(30).fill(null).map(() => ({ power: 180, hr: 135 }));
      // Second 30 min: Power 180W, HR 150 bpm (severe drift due to heat/dehydration/fatigue)
      const split2 = Array(30).fill(null).map(() => ({ power: 180, hr: 150 }));

      const result = calculateAerobicDecoupling(split1, split2);
      assert.ok(result.decouplingPct > 5.0, `Decoupling % was ${result.decouplingPct}%`);
      assert.equal(result.isDecoupled, true, 'Drift > 5% must trigger aerobic decoupling flag');
    });
  });

  describe('4.3 128Hz Oscilloscope Canvas Sweep Circular Ring Buffer', () => {
    class EcgSweepRingBuffer {
      constructor(capacity = 640) {
        this.capacity = capacity; // 640 samples = 5.0s at 128Hz
        this.buffer = new Float32Array(capacity);
        this.writeIndex = 0;
        this.totalSamplesPushed = 0;
      }

      push(sampleVoltage) {
        this.buffer[this.writeIndex] = sampleVoltage;
        this.writeIndex = (this.writeIndex + 1) % this.capacity;
        this.totalSamplesPushed++;
      }

      getSweepGap(gapWidth = 10) {
        // Erase gap ahead of sweep head for classic medical monitor look
        const gapIndices = [];
        for (let i = 0; i < gapWidth; i++) {
          gapIndices.push((this.writeIndex + i) % this.capacity);
        }
        return gapIndices;
      }
    }

    it('Ring buffer handles continuous streaming at 128Hz without memory leaks or index overflow', () => {
      const ringBuffer = new EcgSweepRingBuffer(640);

      // Stream 5,000 samples (simulating ~39 seconds of 128Hz streaming)
      for (let i = 0; i < 5000; i++) {
        const dummyVoltage = Math.sin(i * 0.1) * 1.2;
        ringBuffer.push(dummyVoltage);
      }

      assert.equal(ringBuffer.totalSamplesPushed, 5000);
      assert.equal(ringBuffer.writeIndex, 5000 % 640);
      assert.equal(ringBuffer.buffer.length, 640, 'Buffer capacity must remain fixed at 640');
      
      const gap = ringBuffer.getSweepGap(10);
      assert.equal(gap.length, 10);
      assert.equal(gap[0], ringBuffer.writeIndex);
    });
  });
});
