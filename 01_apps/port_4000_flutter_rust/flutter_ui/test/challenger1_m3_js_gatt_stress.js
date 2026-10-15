/**
 * Milestone 3 Adversarial Challenger 1 — Empirical Stress Test Harness for Web Bluetooth GATT Parsers
 * Tests exact JavaScript parser logic from dashboard_screen.dart against pathological payloads,
 * variable-length frames, Energy Expended offsets, dangling bytes, and 512Hz sample floods.
 */

const fs = require('fs');
const assert = require('assert');

console.log("🔥 Starting Milestone 3 JavaScript GATT Stress Harness...");

// 1. Extract JavaScript functions from dashboard_screen.dart or define identical mirrors
function parseHeartRateMeasurement(val) {
  if (!val || val.byteLength < 2) return null;

  const flags = val.getUint8(0);
  const is16BitHr = (flags & 0x01) !== 0;
  const hasRr = (flags & 0x10) !== 0;

  let offset = 1;
  let heartRate = 0;
  if (is16BitHr) {
    if (val.byteLength < offset + 2) return null;
    heartRate = val.getUint16(offset, true);
    offset += 2;
  } else {
    heartRate = val.getUint8(offset);
    offset += 1;
  }

  const rrIntervals = [];
  if (hasRr) {
    while (offset + 2 <= val.byteLength) {
      const rawRr = val.getUint16(offset, true);
      const rrMs = (rawRr / 1024.0) * 1000.0;
      if (rrMs >= 250.0 && rrMs <= 2200.0) {
        rrIntervals.push(Math.round(rrMs * 10) / 10);
      }
      offset += 2;
    }
  }

  return { heartRate, rrIntervals };
}

function parseHeartRateMeasurementFullSig(val) {
  if (!val || val.byteLength < 2) return null;

  const flags = val.getUint8(0);
  const is16BitHr = (flags & 0x01) !== 0;
  const hasEnergy = (flags & 0x08) !== 0;
  const hasRr = (flags & 0x10) !== 0;

  let offset = 1;
  let heartRate = 0;
  if (is16BitHr) {
    if (val.byteLength < offset + 2) return null;
    heartRate = val.getUint16(offset, true);
    offset += 2;
  } else {
    heartRate = val.getUint8(offset);
    offset += 1;
  }

  let energyExpended = null;
  if (hasEnergy) {
    if (offset + 2 <= val.byteLength) {
      energyExpended = val.getUint16(offset, true);
      offset += 2;
    }
  }

  const rrIntervals = [];
  if (hasRr) {
    while (offset + 2 <= val.byteLength) {
      const rawRr = val.getUint16(offset, true);
      const rrMs = (rawRr / 1024.0) * 1000.0;
      if (rrMs >= 250.0 && rrMs <= 2200.0) {
        rrIntervals.push(Math.round(rrMs * 10) / 10);
      }
      offset += 2;
    }
  }

  return { heartRate, energyExpended, rrIntervals };
}

function parseMovesenseEcgSamplesInt32(val) {
  if (!val || val.byteLength < 6) return [];
  const samplesMv = [];
  let offset = 6;
  while (offset + 4 <= val.byteLength) {
    const microvolts = val.getInt32(offset, true);
    const millivolts = microvolts / 1000.0;
    samplesMv.push(millivolts);
    offset += 4;
  }
  return samplesMv;
}

function parseMovesenseEcgSamplesInt16(val) {
  if (!val || val.byteLength < 6) return [];
  const samplesMv = [];
  let offset = 6;
  while (offset + 2 <= val.byteLength) {
    const microvolts = val.getInt16(offset, true);
    const millivolts = microvolts / 1000.0;
    samplesMv.push(millivolts);
    offset += 2;
  }
  return samplesMv;
}

function parseMovesenseEcgAdaptive(val) {
  if (!val || val.byteLength < 6) return [];
  const payloadBytes = val.byteLength - 6;
  const samplesMv = [];
  if (payloadBytes % 4 === 0 && payloadBytes > 0) {
    let offset = 6;
    while (offset + 4 <= val.byteLength) {
      const microvolts = val.getInt32(offset, true);
      samplesMv.push(microvolts / 1000.0);
      offset += 4;
    }
  } else if (payloadBytes % 2 === 0 && payloadBytes > 0) {
    let offset = 6;
    while (offset + 2 <= val.byteLength) {
      const microvolts = val.getInt16(offset, true);
      samplesMv.push(microvolts / 1000.0);
      offset += 2;
    }
  }
  return samplesMv;
}

function applyKamathFilter(rrList) {
  if (!rrList || rrList.length < 2) return rrList ? [...rrList] : [];
  const clean = [rrList[0]];
  for (let i = 1; i < rrList.length; i++) {
    const prev = clean[clean.length - 1];
    const curr = rrList[i];
    if (prev > 0 && Math.abs(curr - prev) / prev <= 0.20) {
      clean.push(curr);
    } else {
      clean.push(prev);
    }
  }
  return clean;
}

function computeRmssd(rrList) {
  if (!rrList || rrList.length < 2) return null;
  let sumSq = 0.0;
  for (let i = 1; i < rrList.length; i++) {
    const diff = rrList[i] - rrList[i - 1];
    sumSq += diff * diff;
  }
  return Math.sqrt(sumSq / (rrList.length - 1));
}

// --- TEST SUITE ---
let passed = 0;
let failed = 0;

function runTest(name, fn) {
  try {
    fn();
    console.log(`  ✅ PASS: ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ❌ FAIL: ${name} -> ${err.message}`);
    failed++;
  }
}

// Suite 1: Pathological Payloads for HRS 0x2A37
runTest("HRS 0x2A37: Null and zero-length buffer", () => {
  assert.strictEqual(parseHeartRateMeasurement(null), null);
  const empty = new DataView(new ArrayBuffer(0));
  assert.strictEqual(parseHeartRateMeasurement(empty), null);
  const oneByte = new DataView(new ArrayBuffer(1));
  assert.strictEqual(parseHeartRateMeasurement(oneByte), null);
});

runTest("HRS 0x2A37: Truncated 16-bit HR payload (flag=0x01, length=2 bytes)", () => {
  const buf = new ArrayBuffer(2);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x01); // 16-bit HR flag
  dv.setUint8(1, 0x48); // Only 1 byte of HR data
  // Should return null gracefully without throwing RangeError
  assert.strictEqual(parseHeartRateMeasurement(dv), null);
});

runTest("HRS 0x2A37: Truncated trailing RR interval (1 dangling byte)", () => {
  // Flag = 0x10 (8-bit + RR), HR = 80, RR1 = 1000ms (1024 raw = 0x00 0x04), Dangling byte = 0xFF
  const buf = new ArrayBuffer(5);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x10);
  dv.setUint8(1, 80);
  dv.setUint16(2, 1024, true);
  dv.setUint8(4, 0xFF); // Dangling 5th byte

  const res = parseHeartRateMeasurement(dv);
  assert.strictEqual(res.heartRate, 80);
  assert.strictEqual(res.rrIntervals.length, 1);
  assert.strictEqual(res.rrIntervals[0], 1000.0);
});

runTest("HRS 0x2A37: Flag Bit 3 Energy Expended Offset Discrepancy Analysis", () => {
  // When Energy Expended bit (0x08) is set, 2 bytes are inserted before RR intervals.
  // Flag = 0x18 (8-bit HR + Energy Expended + RR)
  // Byte 0: 0x18
  // Byte 1: HR = 70 BPM
  // Byte 2..3: Energy Expended = 350 kJ (0x015E -> 350)
  // Byte 4..5: RR = 1000.0ms (1024 raw -> [0x00, 0x04])
  const buf = new ArrayBuffer(6);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x18);
  dv.setUint8(1, 70);
  dv.setUint16(2, 350, true);
  dv.setUint16(4, 1024, true);

  // Full SIG parser correctly skips Energy Expended and reads RR = 1000ms
  const sigRes = parseHeartRateMeasurementFullSig(dv);
  assert.strictEqual(sigRes.heartRate, 70);
  assert.strictEqual(sigRes.energyExpended, 350);
  assert.strictEqual(sigRes.rrIntervals.length, 1);
  assert.strictEqual(sigRes.rrIntervals[0], 1000.0);

  // Worker's current parser (dashboard_screen.dart) ignores Bit 3 and attempts to parse Energy Expended as RR
  const workerRes = parseHeartRateMeasurement(dv);
  // Energy Expended 350 is (350 / 1024.0) * 1000 = 341.8ms (which falls into 250-2200ms window!)
  // Therefore, the worker parser mistakenly treats Energy Expended (350 kJ) as an RR interval (341.8ms)!
  console.log(`    Note: Worker parser parsed ${workerRes.rrIntervals.length} RR intervals (first RR: ${workerRes.rrIntervals[0]}ms from 350kJ energy!)`);
});

runTest("HRS 0x2A37: High-Frequency Packet Flood (100,000 rapid packets)", () => {
  const start = Date.now();
  for (let i = 0; i < 100000; i++) {
    const buf = new ArrayBuffer(8);
    const dv = new DataView(buf);
    dv.setUint8(0, (i % 2 === 0) ? 0x10 : 0x11);
    if (i % 2 === 0) {
      dv.setUint8(1, (i % 120) + 50);
      dv.setUint16(2, 800 + (i % 200), true);
      dv.setUint16(4, 820 + (i % 200), true);
      dv.setUint16(6, 810 + (i % 200), true);
    } else {
      dv.setUint16(1, (i % 150) + 60, true);
      dv.setUint16(3, 850 + (i % 200), true);
      dv.setUint16(5, 840 + (i % 200), true);
    }
    const res = parseHeartRateMeasurement(dv);
    assert(res.heartRate > 0);
  }
  const elapsed = Date.now() - start;
  console.log(`    100,000 HRS packets unpacked in ${elapsed}ms (${(100000 / (elapsed / 1000)).toFixed(0)} packets/sec)`);
  assert(elapsed < 2000, "Should process 100,000 packets in under 2000ms");
});

// Suite 2: Pathological Payloads for Movesense 512Hz ECG
runTest("Movesense ECG: Empty and truncated headers (<6 bytes)", () => {
  assert.deepStrictEqual(parseMovesenseEcgSamplesInt16(null), []);
  assert.deepStrictEqual(parseMovesenseEcgSamplesInt16(new DataView(new ArrayBuffer(0))), []);
  assert.deepStrictEqual(parseMovesenseEcgSamplesInt16(new DataView(new ArrayBuffer(5))), []);
  assert.deepStrictEqual(parseMovesenseEcgSamplesInt32(new DataView(new ArrayBuffer(5))), []);
});

runTest("Movesense ECG: Dangling odd bytes in Int16 stream", () => {
  // Header: 6 bytes + 2 samples (4 bytes) + 1 dangling byte = 11 bytes
  const buf = new ArrayBuffer(11);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x02); // Opcode
  dv.setUint8(1, 0x63); // RefId
  dv.setUint32(2, 123456, true); // Timestamp
  dv.setInt16(6, 1200, true); // 1.200 mV
  dv.setInt16(8, -850, true); // -0.850 mV
  dv.setUint8(10, 0xAA); // Dangling byte

  const samples = parseMovesenseEcgSamplesInt16(dv);
  assert.strictEqual(samples.length, 2);
  assert.strictEqual(samples[0], 1.2);
  assert.strictEqual(samples[1], -0.85);
});

runTest("Movesense ECG: Dangling bytes (1..3) in Int32 stream", () => {
  // Header: 6 bytes + 1 sample (4 bytes) + 3 dangling bytes = 13 bytes
  const buf = new ArrayBuffer(13);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x02);
  dv.setUint8(1, 0x63);
  dv.setUint32(2, 1000, true);
  dv.setInt32(6, 2500, true); // 2.500 mV
  dv.setUint8(10, 0x11);
  dv.setUint8(11, 0x22);
  dv.setUint8(12, 0x33);

  const samples = parseMovesenseEcgSamplesInt32(dv);
  assert.strictEqual(samples.length, 1);
  assert.strictEqual(samples[0], 2.5);
});

runTest("Movesense ECG: 512Hz Sample Flood into Circular Ring Buffer (500,000 samples)", () => {
  const ECG_BUFFER_SIZE = 512;
  const ecgBuffer = new Float32Array(ECG_BUFFER_SIZE);
  let ecgWriteIdx = 0;

  const start = Date.now();
  // 500,000 samples = ~976 seconds of real-time 512Hz stream
  for (let p = 0; p < 31250; p++) {
    // 16 samples per packet (32 bytes payload + 6 bytes header = 38 bytes)
    const buf = new ArrayBuffer(38);
    const dv = new DataView(buf);
    dv.setUint8(0, 0x02);
    dv.setUint8(1, 0x63);
    dv.setUint32(2, p * 31, true);

    for (let s = 0; s < 16; s++) {
      const uV = Math.round(1500 * Math.sin((p * 16 + s) * 0.05));
      dv.setInt16(6 + s * 2, uV, true);
    }

    const unpacked = parseMovesenseEcgSamplesInt16(dv);
    for (let i = 0; i < unpacked.length; i++) {
      ecgBuffer[ecgWriteIdx] = unpacked[i];
      ecgWriteIdx = (ecgWriteIdx + 1) % ECG_BUFFER_SIZE;
    }
  }

  const elapsed = Date.now() - start;
  console.log(`    500,000 ECG samples (31,250 packets) ingested into ring buffer in ${elapsed}ms (${(500000 / (elapsed / 1000)).toFixed(0)} samples/sec)`);
  assert.strictEqual(ecgBuffer.length, 512, "Circular buffer size must stay constant at 512");
  assert(elapsed < 2000, "Should process 500,000 ECG samples in under 2000ms");
});

// Suite 3: Kamath Filter & RMSSD under Extreme Ectopic / Noise Storms
runTest("Kamath Filter: Outlier and Noise Storm Resistance", () => {
  // Baseline 800ms with ectopic spikes (+150%, -80%)
  const rrs = [800, 810, 805, 2000, 800, 200, 805, 810];
  const cleaned = applyKamathFilter(rrs);
  assert.strictEqual(cleaned.length, rrs.length);
  assert.strictEqual(cleaned[3], 805); // 2000 rejected -> replaced with 805
  assert.strictEqual(cleaned[5], 800); // 200 rejected -> replaced with 800

  const rmssd = computeRmssd(cleaned);
  assert(rmssd !== null);
  assert(rmssd < 20.0, `Cleaned RMSSD should be calm (<20ms), got ${rmssd}`);
});

console.log(`\n========================================`);
console.log(`Summary: ${passed} passed, ${failed} failed.`);
console.log(`========================================\n`);

if (failed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
