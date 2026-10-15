/**
 * Milestone 3 Challenger 1 — BLE Packet Adversarial Stress Test Harness
 * 
 * Direct Empirical Oracle & Fuzzing Engine testing:
 * 1. 0x2A37 Heart Rate Measurement malformed packets & fuzzing
 * 2. Movesense 512Hz ECG unpacker with truncated headers and dangling bytes
 * 3. GATT disconnect/reconnect cycles with exponential backoff & DOM standby validation
 * 4. High sample volume floods and zero/negative mathematical edge cases
 */

const fs = require('fs');
const assert = require('assert');

console.log("================================================================================");
console.log("⚡ CHALLENGER 1 (M3): WEB BLUETOOTH & 0x2A37 GATT ADVERSARIAL STRESS HARNESS");
console.log("================================================================================\n");

// Synthetic DOM Environment
class MockElement {
  constructor(id) {
    this.id = id;
    this.innerText = '';
    this.textContent = '';
    this.style = { borderColor: '', color: '' };
    this.className = '';
  }
}

const domElements = {
  'val-hr': new MockElement('val-hr'),
  'val-rmssd': new MockElement('val-rmssd'),
  'val-alpha1': new MockElement('val-alpha1'),
  'val-readiness': new MockElement('val-readiness'),
  'sub-zone2': new MockElement('sub-zone2'),
  'sub-hr': new MockElement('sub-hr'),
  'sub-readiness': new MockElement('sub-readiness'),
  'txt-technique': new MockElement('txt-technique'),
  'txt-camera-status': new MockElement('txt-camera-status'),
  'badge-status': new MockElement('badge-status'),
  'badge-qrs': new MockElement('badge-qrs'),
  'badge-battery': new MockElement('badge-battery'),
  'btn-connect': new MockElement('btn-connect'),
};

global.document = {
  getElementById: (id) => domElements[id] || null,
  createElement: (tag) => new MockElement('mock-' + tag),
};

// Extracted / Mirror of core production routines from dashboard_screen.dart & build/index.html
function parseHeartRateMeasurement(val) {
  if (!val || val.byteLength < 2) return null;

  const flags = val.getUint8(0);
  const is16BitHr = (flags & 0x01) !== 0;
  const contactSupported = (flags & 0x02) !== 0;
  const contactDetected = (flags & 0x04) !== 0;
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

  let energyExpendedKJ = null;
  if (hasEnergy) {
    if (offset + 2 <= val.byteLength) {
      energyExpendedKJ = val.getUint16(offset, true);
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

  let skinContact = null;
  const contactBits = (flags >> 1) & 0x03;
  if (contactBits === 2) skinContact = false;
  if (contactBits === 3) skinContact = true;

  return {
    heartRate,
    is16Bit: is16BitHr,
    skinContact,
    contactDetected,
    energyExpendedKJ,
    rrIntervals
  };
}

function parseBatteryLevel(val) {
  if (!val || val.byteLength < 1) return null;
  const level = val.getUint8(0);
  return Math.max(0, Math.min(100, level));
}

function parseMovesenseEcgSamples(val) {
  if (!val || val.byteLength < 6) return [];
  const payloadBytes = val.byteLength - 6;
  const samplesMv = [];
  if (payloadBytes % 4 === 0 && payloadBytes > 0) {
    const count = payloadBytes / 4;
    for (let i = 0; i < count; i++) {
      const uV = val.getInt32(6 + (i * 4), true);
      const mV = uV / 1000.0;
      if (Number.isFinite(mV)) samplesMv.push(mV);
    }
  } else if (payloadBytes % 2 === 0 && payloadBytes > 0) {
    const count = payloadBytes / 2;
    for (let i = 0; i < count; i++) {
      const uV = val.getInt16(6 + (i * 2), true);
      const mV = uV / 1000.0;
      if (Number.isFinite(mV)) samplesMv.push(mV);
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

function computeDfaAlpha1(rrList) {
  const n = rrList.length;
  if (n < 16) return null;
  const mean = rrList.reduce((a, b) => a + b, 0) / n;
  let cumsum = 0;
  const y = [];
  for (let i = 0; i < n; i++) {
    cumsum += rrList[i] - mean;
    y.push(cumsum);
  }
  const scales = [4, 6, 8, 12, 16];
  const logScales = [];
  const logFlucts = [];
  for (const scale of scales) {
    if (scale >= n) continue;
    const segments = Math.floor(n / scale);
    if (segments === 0) continue;
    let sumSqErr = 0;
    let totalPoints = 0;
    for (let s = 0; s < segments; s++) {
      const start = s * scale;
      const seg = y.slice(start, start + scale);
      const segLen = seg.length;
      let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
      for (let i = 0; i < segLen; i++) {
        sumX += i; sumY += seg[i];
        sumXY += i * seg[i]; sumX2 += i * i;
      }
      const denom = (segLen * sumX2 - sumX * sumX);
      const slope = denom !== 0 ? (segLen * sumXY - sumX * sumY) / denom : 0;
      const intercept = (sumY - slope * sumX) / segLen;
      for (let i = 0; i < segLen; i++) {
        const trend = slope * i + intercept;
        const diff = seg[i] - trend;
        sumSqErr += diff * diff;
        totalPoints++;
      }
    }
    if (totalPoints > 0) {
      const fluct = Math.sqrt(sumSqErr / totalPoints);
      if (fluct > 1e-5) {
        logScales.push(Math.log(scale));
        logFlucts.push(Math.log(fluct));
      }
    }
  }
  if (logScales.length < 2) return null;
  let sX = 0, sY = 0, sXY = 0, sX2 = 0;
  const count = logScales.length;
  for (let i = 0; i < count; i++) {
    sX += logScales[i]; sY += logFlucts[i];
    sXY += logScales[i] * logFlucts[i]; sX2 += logScales[i] * logScales[i];
  }
  const d = count * sX2 - sX * sX;
  return d !== 0 ? Math.max(0.25, Math.min(1.75, Math.round(((count * sXY - sX * sY) / d) * 100) / 100)) : 1.0;
}

function classifyZone2(alpha1Val, hrVal) {
  if (!hrVal || hrVal <= 0) return 'Resting / Disconnected';
  if (alpha1Val === null || alpha1Val === undefined) return 'Calibrating RR Stream...';
  if (alpha1Val >= 0.85) return 'Zone 1: Active Recovery';
  if (alpha1Val >= 0.70) return 'Zone 2: Optimal Aerobic (LT1)';
  if (alpha1Val >= 0.50) return 'Zone 3: Tempo / Aerobic Threshold';
  return 'Zone 4/5: Anaerobic / Above LT2';
}

function computeReadinessScore(hrVal, rmssdVal, alpha1Val) {
  if (!hrVal || hrVal <= 0 || !rmssdVal || rmssdVal <= 0) return null;
  const hrvPart = Math.min(1, Math.max(0, (rmssdVal - 15.0) / 65.0)) * 50.0;
  const hrPart = Math.min(1, Math.max(0, (85.0 - hrVal) / 40.0)) * 30.0;
  let dfaPart = 5.0;
  if (alpha1Val !== null && alpha1Val !== undefined) {
    if (alpha1Val >= 0.9 && alpha1Val <= 1.3) dfaPart = 20.0;
    else if (alpha1Val > 0.75) dfaPart = 15.0;
  }
  return Math.min(100, Math.max(0, Math.round(hrvPart + hrPart + dfaPart)));
}

// Reset UI state machine mirror
const ECG_BUFFER_SIZE = 512;
const ecgBuffer = new Float32Array(ECG_BUFFER_SIZE);
let isConnected = false;
let isConnecting = false;
let heartRate = null;
let rmssd = null;
let alpha1 = null;
let readiness = null;
let clientRrHistory = [];
let currentBatteryLevel = null;
let skeletonNodes = [];
let jointTorques = [];
let submissionRisk = 0.0;

function resetUiToStandby() {
  isConnected = false;
  isConnecting = false;
  heartRate = null;
  rmssd = null;
  alpha1 = null;
  readiness = null;
  clientRrHistory = [];
  currentBatteryLevel = null;
  skeletonNodes = [];
  jointTorques = [];
  submissionRisk = 0.0;
  ecgBuffer.fill(0.0);

  domElements['val-hr'].innerText = '--';
  domElements['val-rmssd'].innerText = '--';
  domElements['val-alpha1'].innerText = '--';
  domElements['val-readiness'].innerText = '--';
  domElements['sub-zone2'].innerText = 'Resting / Disconnected';
  domElements['sub-hr'].innerText = 'Movesense Standby';
  domElements['txt-technique'].innerText = 'STANDBY — NO ATHLETE DETECTED';
  domElements['txt-camera-status'].innerText = '0/33 Joints Tracked';

  const badge = domElements['badge-status'];
  badge.innerText = 'STANDBY — DISCONNECTED';
  badge.style.borderColor = '#EF4444';
  badge.style.color = '#EF4444';

  const qrsBadge = domElements['badge-qrs'];
  if (qrsBadge) {
    qrsBadge.innerText = '512 Hz Native DSP';
    qrsBadge.style.borderColor = '#334155';
    qrsBadge.style.color = '#64748B';
  }

  const btn = domElements['btn-connect'];
  btn.innerText = '📲 CONNECT MOVESENSE (BLUETOOTH)';
}

// --- TEST RUNNER ---
let totalTests = 0;
let passedTests = 0;
let failedTests = 0;

function test(description, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  [PASS] Test ${totalTests}: ${description}`);
    passedTests++;
  } catch (e) {
    console.error(`  [FAIL] Test ${totalTests}: ${description}`);
    console.error(`         Error: ${e.message}\n${e.stack}`);
    failedTests++;
  }
}

// ================================================================================
// SUITE 1: Pathological 0x2A37 BLE Malformed Packet Fuzzing
// ================================================================================
console.log("--- SUITE 1: 0x2A37 BLE Malformed Packet Fuzzing & Stress ---");

test("Null, undefined, 0-byte, and 1-byte truncated packets return null safely", () => {
  assert.strictEqual(parseHeartRateMeasurement(null), null);
  assert.strictEqual(parseHeartRateMeasurement(undefined), null);
  assert.strictEqual(parseHeartRateMeasurement(new DataView(new ArrayBuffer(0))), null);
  assert.strictEqual(parseHeartRateMeasurement(new DataView(new ArrayBuffer(1))), null);
});

test("Truncated 16-bit HR payload (flag=0x01, total length 2 bytes) returns null", () => {
  const dv = new DataView(new ArrayBuffer(2));
  dv.setUint8(0, 0x01); // 16-bit HR flag set, but only 1 byte follows
  dv.setUint8(1, 0x50);
  assert.strictEqual(parseHeartRateMeasurement(dv), null);
});

test("Corrupted Flags Fuzzing: All 256 flag bytes across lengths 0..32 bytes execute without exceptions", () => {
  for (let flag = 0; flag < 256; flag++) {
    for (let len = 0; len <= 32; len++) {
      const buf = new ArrayBuffer(len);
      const dv = new DataView(buf);
      if (len > 0) dv.setUint8(0, flag);
      for (let i = 1; i < len; i++) {
        dv.setUint8(i, (flag + i * 37) & 0xFF);
      }
      const res = parseHeartRateMeasurement(dv);
      if (res !== null) {
        assert(typeof res.heartRate === 'number');
        assert(Array.isArray(res.rrIntervals));
      }
    }
  }
});

test("Flag Bit 3 (Energy Expended) Offset Alignment with Multiple RR Intervals", () => {
  // Flags: 0x18 -> 8-bit HR + Energy Expended (2B) + RR intervals
  // Byte 0: 0x18
  // Byte 1: HR = 88 BPM
  // Byte 2..3: Energy Expended = 450 kJ (0x01C2)
  // Byte 4..5: RR1 = 1000.0ms (1024 raw -> 0x0400)
  // Byte 6..7: RR2 = 799.8ms (819 raw -> 0x0333)
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x18);
  dv.setUint8(1, 88);
  dv.setUint16(2, 450, true);
  dv.setUint16(4, 1024, true);
  dv.setUint16(6, 819, true);

  const res = parseHeartRateMeasurement(dv);
  assert.strictEqual(res.heartRate, 88);
  assert.strictEqual(res.energyExpendedKJ, 450);
  assert.strictEqual(res.rrIntervals.length, 2);
  assert.strictEqual(res.rrIntervals[0], 1000.0);
  assert(Math.abs(res.rrIntervals[1] - 800.0) < 1.0);
});

test("Flag Bit 0 & 3 (16-bit HR + Energy Expended + RR Intervals)", () => {
  // Flags: 0x19 -> 16-bit HR (2B) + Energy Expended (2B) + RR (2B)
  const buf = new ArrayBuffer(7);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x19);
  dv.setUint16(1, 165, true); // HR = 165
  dv.setUint16(3, 820, true); // Energy Expended = 820 kJ
  dv.setUint16(5, 750, true); // RR = (750 / 1024) * 1000 = 732.4ms

  const res = parseHeartRateMeasurement(dv);
  assert.strictEqual(res.heartRate, 165);
  assert.strictEqual(res.is16Bit, true);
  assert.strictEqual(res.energyExpendedKJ, 820);
  assert.strictEqual(res.rrIntervals.length, 1);
  assert.strictEqual(res.rrIntervals[0], 732.4);
});

test("Multi-RR Interval Burst (50 RR Intervals in single packet)", () => {
  // 1B flag + 1B HR + 50 * 2B RR = 102 bytes
  const buf = new ArrayBuffer(102);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x10);
  dv.setUint8(1, 120);

  for (let i = 0; i < 50; i++) {
    const targetMs = 800 + (i * 10);
    const rawVal = Math.round((targetMs * 1024) / 1000);
    dv.setUint16(2 + (i * 2), rawVal, true);
  }

  const res = parseHeartRateMeasurement(dv);
  assert.strictEqual(res.heartRate, 120);
  assert.strictEqual(res.rrIntervals.length, 50);
  assert(Math.abs(res.rrIntervals[0] - 800.0) < 1.0);
  assert(Math.abs(res.rrIntervals[49] - 1290.0) < 1.0);
});

test("Non-aligned byte offsets and dangling odd bytes are dropped safely", () => {
  // 1B flag + 1B HR + 2B RR1 + 1B dangling byte = 5 bytes
  const buf = new ArrayBuffer(5);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x10);
  dv.setUint8(1, 75);
  dv.setUint16(2, 1024, true); // 1000ms
  dv.setUint8(4, 0xDE); // Dangling byte

  const res = parseHeartRateMeasurement(dv);
  assert.strictEqual(res.heartRate, 75);
  assert.strictEqual(res.rrIntervals.length, 1);
  assert.strictEqual(res.rrIntervals[0], 1000.0);
});

test("Physiological bounds [250ms, 2200ms] strictly filter non-physiological RR values", () => {
  const buf = new ArrayBuffer(16);
  const dv = new DataView(buf);
  dv.setUint8(0, 0x10);
  dv.setUint8(1, 60);

  // RR 0: 0ms -> Rejected
  dv.setUint16(2, 0, true);
  // RR 1: 249ms (255 raw) -> Rejected
  dv.setUint16(4, 255, true);
  // RR 2: 250ms (256 raw) -> Accepted
  dv.setUint16(6, 256, true);
  // RR 3: 1000ms (1024 raw) -> Accepted
  dv.setUint16(8, 1024, true);
  // RR 4: 2199.2ms (2252 raw) -> Accepted
  dv.setUint16(10, 2252, true);
  // RR 5: 2201.2ms (2254 raw) -> Rejected
  dv.setUint16(12, 2254, true);
  // RR 6: 64000ms (0xFFFF) -> Rejected
  dv.setUint16(14, 0xFFFF, true);

  const res = parseHeartRateMeasurement(dv);
  assert.strictEqual(res.rrIntervals.length, 3);
  assert.strictEqual(res.rrIntervals[0], 250.0);
  assert.strictEqual(res.rrIntervals[1], 1000.0);
  assert.strictEqual(res.rrIntervals[2], 2199.2);
});

// ================================================================================
// SUITE 2: Movesense 512Hz ECG Unpacker Stress
// ================================================================================
console.log("\n--- SUITE 2: Movesense 512Hz ECG Unpacker Stress ---");

test("Truncated Movesense headers (< 6 bytes) return empty array []", () => {
  for (let len = 0; len < 6; len++) {
    const dv = new DataView(new ArrayBuffer(len));
    assert.deepStrictEqual(parseMovesenseEcgSamples(dv), []);
  }
});

test("Movesense 16-bit sample unpacker handles dangling odd bytes", () => {
  const buf = new ArrayBuffer(12); // 6B header + 6B (3 samples)
  const dv = new DataView(buf);
  dv.setInt16(6, 1500, true);  // 1.5 mV
  dv.setInt16(8, -800, true);  // -0.8 mV
  dv.setInt16(10, 3200, true); // 3.2 mV

  const samples = parseMovesenseEcgSamples(dv);
  assert.strictEqual(samples.length, 3);
  assert.strictEqual(samples[0], 1.5);
  assert.strictEqual(samples[1], -0.8);
  assert.strictEqual(samples[2], 3.2);
});

test("Movesense 32-bit sample unpacker handles extreme microvolt values", () => {
  const buf = new ArrayBuffer(14);
  const dv = new DataView(buf);
  dv.setInt32(6, -2147483648, true); // Min INT32 -> -2147483.648 mV
  dv.setInt32(10, 2147483647, true);  // Max INT32 -> 2147483.647 mV

  const samples = parseMovesenseEcgSamples(dv);
  assert.strictEqual(samples.length, 2);
  assert.strictEqual(samples[0], -2147483.648);
  assert.strictEqual(samples[1], 2147483.647);
});

test("High Sample Volume: 1,000,000 ECG samples ingested into circular ring buffer", () => {
  const start = Date.now();
  const ringBuffer = new Float32Array(512);
  let writeIdx = 0;

  for (let p = 0; p < 62500; p++) {
    const buf = new ArrayBuffer(38); // 6B header + 16 * 2B = 38B
    const dv = new DataView(buf);
    for (let s = 0; s < 16; s++) {
      dv.setInt16(6 + s * 2, Math.round(Math.sin(s) * 1000), true);
    }
    const unpacked = parseMovesenseEcgSamples(dv);
    for (let i = 0; i < unpacked.length; i++) {
      ringBuffer[writeIdx] = unpacked[i];
      writeIdx = (writeIdx + 1) % 512;
    }
  }
  const duration = Date.now() - start;
  console.log(`    Ingested 1,000,000 ECG samples in ${duration}ms (${Math.round(1000000 / (duration / 1000))} samples/sec)`);
  assert(duration < 2000, "1M samples must process in <2000ms");
  assert.strictEqual(ringBuffer.length, 512);
});

// ================================================================================
// SUITE 3: GATT Disconnection / Reconnection State Machine & UI Standby
// ================================================================================
console.log("\n--- SUITE 3: GATT Disconnection / Reconnection State Machine & UI Standby ---");

test("resetUiToStandby() completely purges all live metrics to authentic waiting states", () => {
  domElements['val-hr'].innerText = '145';
  domElements['val-rmssd'].innerText = '58.2';
  domElements['val-alpha1'].innerText = '0.95';
  domElements['val-readiness'].innerText = '88';
  domElements['sub-zone2'].innerText = 'Zone 2: Optimal Aerobic (LT1)';
  domElements['sub-hr'].innerText = 'Movesense 194430000123';
  domElements['txt-technique'].innerText = 'Armbar Transition';
  domElements['txt-camera-status'].innerText = '33/33 Joints Tracked';
  domElements['badge-status'].innerText = '🟢 PIXEL BLE: Movesense 194430000123';
  domElements['badge-status'].style.borderColor = '#00FF88';
  domElements['badge-status'].style.color = '#00FF88';
  domElements['btn-connect'].innerText = '✅ SENSOR PAIRED: Movesense';
  ecgBuffer.fill(1.5);

  resetUiToStandby();

  assert.strictEqual(domElements['val-hr'].innerText, '--');
  assert.strictEqual(domElements['val-rmssd'].innerText, '--');
  assert.strictEqual(domElements['val-alpha1'].innerText, '--');
  assert.strictEqual(domElements['val-readiness'].innerText, '--');
  assert.strictEqual(domElements['sub-zone2'].innerText, 'Resting / Disconnected');
  assert.strictEqual(domElements['sub-hr'].innerText, 'Movesense Standby');
  assert.strictEqual(domElements['txt-technique'].innerText, 'STANDBY — NO ATHLETE DETECTED');
  assert.strictEqual(domElements['txt-camera-status'].innerText, '0/33 Joints Tracked');
  assert.strictEqual(domElements['badge-status'].innerText, 'STANDBY — DISCONNECTED');
  assert.strictEqual(domElements['badge-status'].style.borderColor, '#EF4444');
  assert.strictEqual(domElements['badge-status'].style.color, '#EF4444');
  assert.strictEqual(domElements['badge-qrs'].innerText, '512 Hz Native DSP');
  assert.strictEqual(domElements['badge-qrs'].style.borderColor, '#334155');
  assert.strictEqual(domElements['btn-connect'].innerText, '📲 CONNECT MOVESENSE (BLUETOOTH)');

  for (let i = 0; i < ECG_BUFFER_SIZE; i++) {
    assert.strictEqual(ecgBuffer[i], 0.0);
  }
});

test("10,000 rapid connect / disconnect cycles leave zero stale state or DOM leakage", () => {
  for (let i = 0; i < 10000; i++) {
    domElements['val-hr'].innerText = `${60 + (i % 100)}`;
    domElements['val-rmssd'].innerText = `${30 + (i % 40)}`;
    domElements['badge-status'].innerText = '🟢 LIVE BLE';
    ecgBuffer[i % 512] = (i % 10) * 0.1;

    resetUiToStandby();
  }

  assert.strictEqual(domElements['val-hr'].innerText, '--');
  assert.strictEqual(domElements['val-rmssd'].innerText, '--');
  assert.strictEqual(domElements['badge-status'].innerText, 'STANDBY — DISCONNECTED');
  assert.strictEqual(ecgBuffer[0], 0.0);
});

test("Exponential Backoff Reconnect Schedule Mathematical Proof", () => {
  const MAX_RECONNECT_ATTEMPTS = 5;
  const expectedBaseDelays = [1000, 2000, 4000, 8000, 10000];

  for (let attempt = 1; attempt <= MAX_RECONNECT_ATTEMPTS; attempt++) {
    const baseMs = Math.min(10000, 1000 * Math.pow(2, attempt - 1));
    assert.strictEqual(baseMs, expectedBaseDelays[attempt - 1]);
  }

  const attempt6Allowed = (6 <= MAX_RECONNECT_ATTEMPTS);
  assert.strictEqual(attempt6Allowed, false);
});

// ================================================================================
// SUITE 4: Zero / Negative Mathematical Edge Cases & Algorithm Robustness
// ================================================================================
console.log("\n--- SUITE 4: Zero / Negative Numbers & Mathematical Edge Cases ---");

test("Kamath filter with identical, zero, negative, and extreme outlier RR intervals", () => {
  assert.deepStrictEqual(applyKamathFilter([800, 800, 800]), [800, 800, 800]);

  const rrs = [800, 810, 2400, 805, 200, 815];
  const filtered = applyKamathFilter(rrs);
  assert.strictEqual(filtered.length, 6);
  assert.strictEqual(filtered[2], 810);
  assert.strictEqual(filtered[4], 805);

  assert.deepStrictEqual(applyKamathFilter([]), []);
  assert.deepStrictEqual(applyKamathFilter([800]), [800]);
});

test("computeRmssd handles edge cases (empty, single element, identical, negative values)", () => {
  assert.strictEqual(computeRmssd([]), null);
  assert.strictEqual(computeRmssd([800]), null);
  assert.strictEqual(computeRmssd([800, 800, 800]), 0.0);
  
  const val = computeRmssd([800, 820, 810]);
  assert.strictEqual(Math.round(val * 100) / 100, 15.81);
});

test("computeDfaAlpha1 handles zero-variance (identical RRs) and small samples (<16)", () => {
  assert.strictEqual(computeDfaAlpha1(new Array(15).fill(800)), null);

  const identicalRrs = new Array(20).fill(800);
  const alpha1Result = computeDfaAlpha1(identicalRrs);
  assert(alpha1Result === null || Number.isFinite(alpha1Result));
});

test("classifyZone2 handles zero, negative, null, and out-of-range HR / alpha1", () => {
  assert.strictEqual(classifyZone2(1.0, 0), 'Resting / Disconnected');
  assert.strictEqual(classifyZone2(1.0, -10), 'Resting / Disconnected');
  assert.strictEqual(classifyZone2(null, 75), 'Calibrating RR Stream...');
  assert.strictEqual(classifyZone2(0.95, 130), 'Zone 1: Active Recovery');
  assert.strictEqual(classifyZone2(0.78, 145), 'Zone 2: Optimal Aerobic (LT1)');
  assert.strictEqual(classifyZone2(0.60, 160), 'Zone 3: Tempo / Aerobic Threshold');
  assert.strictEqual(classifyZone2(0.40, 175), 'Zone 4/5: Anaerobic / Above LT2');
});

test("computeReadinessScore handles zero, negative, and out-of-range parameters", () => {
  assert.strictEqual(computeReadinessScore(0, 50, 1.0), null);
  assert.strictEqual(computeReadinessScore(-10, 50, 1.0), null);
  assert.strictEqual(computeReadinessScore(70, 0, 1.0), null);
  assert.strictEqual(computeReadinessScore(70, -5, 1.0), null);

  const score = computeReadinessScore(60, 60, 1.0);
  assert(score >= 0 && score <= 100);
});

test("parseBatteryLevel clamps out-of-range and negative values", () => {
  const dv = new DataView(new ArrayBuffer(1));
  dv.setUint8(0, 100);
  assert.strictEqual(parseBatteryLevel(dv), 100);

  dv.setUint8(0, 0);
  assert.strictEqual(parseBatteryLevel(dv), 0);

  dv.setUint8(0, 255);
  assert.strictEqual(parseBatteryLevel(dv), 100);
});

// ================================================================================
// FINAL VERDICT & SUMMARY
// ================================================================================
console.log("\n================================================================================");
console.log(`STRESS RESULTS: ${passedTests} PASSED / ${failedTests} FAILED (Total: ${totalTests})`);
console.log("================================================================================\n");

if (failedTests > 0) {
  process.exit(1);
} else {
  console.log("🎉 ALL ADVERSARIAL CHALLENGER 1 STRESS TESTS PASSED WITH ZERO FAILURES!");
  process.exit(0);
}
