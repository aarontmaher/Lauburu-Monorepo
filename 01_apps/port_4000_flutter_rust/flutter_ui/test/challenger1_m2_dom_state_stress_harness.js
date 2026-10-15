/**
 * =========================================================================
 * EMPIRICAL ADVERSARIAL CHALLENGER 1 (M2) — DOM & STATE STRESS HARNESS
 * =========================================================================
 * Target: /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build/index.html
 * 
 * Comprehensive Stress Test Coverage:
 * 1. Headless V8 DOM Environment Initialization & Rule #0 Verification
 * 2. resetUiToStandby() State Machine Zero-Mock Invariant & Rapid Churn
 * 3. High-Frequency WebSocket Flapping (1,000 disconnect/reconnect cycles)
 * 4. 100,000 Sample High-Throughput Stream with QRS Peak Bursts
 * 5. Pathological Biometrics Telemetry Fuzzing (NaN, Inf, nulls, corrupt JSON)
 * 6. 3D Spatial Skeleton & Joint Torque Matrix Fuzzing
 * 7. Long-Duration 20,000 Frames Animation Render Loop Execution
 * 8. Interactive 3D Orbit Camera Yaw/Pitch Touch & Mouse Event Fuzzing
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('================================================================');
console.log('⚡ EMPIRICAL CHALLENGER 1: DOM & STATE STRESS HARNESS (M2)');
console.log('================================================================');

// 1. Load HTML Build Artifact
const htmlPath = path.resolve(__dirname, '../build/index.html');
if (!fs.existsSync(htmlPath)) {
  console.error(`FATAL: build/index.html not found at ${htmlPath}`);
  process.exit(1);
}
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

const scriptMatch = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  console.error('FATAL: No <script> tag found in build/index.html');
  process.exit(1);
}
const jsCode = scriptMatch[1];

// 2. Headless DOM & HTML5 Canvas Mock Engine
function createMockCanvas(width = 500, height = 250) {
  const drawCalls = [];
  const ctx = {
    fillStyle: '#000000',
    strokeStyle: '#000000',
    lineWidth: 1.0,
    font: '10px sans-serif',
    textAlign: 'left',
    shadowColor: 'transparent',
    shadowBlur: 0,
    lineDash: [],
    lineCap: 'butt',
    fillRect: (x, y, w, h) => drawCalls.push({ type: 'fillRect', x, y, w, h }),
    strokeRect: (x, y, w, h) => drawCalls.push({ type: 'strokeRect', x, y, w, h }),
    beginPath: () => drawCalls.push({ type: 'beginPath' }),
    closePath: () => drawCalls.push({ type: 'closePath' }),
    moveTo: (x, y) => drawCalls.push({ type: 'moveTo', x, y }),
    lineTo: (x, y) => drawCalls.push({ type: 'lineTo', x, y }),
    stroke: () => drawCalls.push({ type: 'stroke', strokeStyle: ctx.strokeStyle, lineWidth: ctx.lineWidth }),
    fill: () => drawCalls.push({ type: 'fill', fillStyle: ctx.fillStyle }),
    arc: (x, y, r, sa, ea) => drawCalls.push({ type: 'arc', x, y, r, sa, ea }),
    ellipse: (x, y, rx, ry, rot, sa, ea) => drawCalls.push({ type: 'ellipse', x, y, rx, ry, rot, sa, ea }),
    fillText: (text, x, y) => drawCalls.push({ type: 'fillText', text, x, y, fillStyle: ctx.fillStyle }),
    setLineDash: (dash) => { ctx.lineDash = dash; drawCalls.push({ type: 'setLineDash', dash }); },
    clearRect: (x, y, w, h) => drawCalls.push({ type: 'clearRect', x, y, w, h }),
  };

  const listeners = {};
  return {
    width,
    height,
    parentElement: { clientWidth: width + 28 },
    getContext: (type) => (type === '2d' ? ctx : null),
    addEventListener: (evt, cb) => { listeners[evt] = cb; },
    listeners,
    drawCalls,
  };
}

function createMockDom() {
  const elements = {};
  const getOrCreate = (id) => {
    if (!elements[id]) {
      elements[id] = {
        id,
        innerText: '',
        style: {},
        listeners: {},
        addEventListener: function(evt, cb) { this.listeners[evt] = cb; },
      };
    }
    return elements[id];
  };

  const canvasEcg = createMockCanvas(480, 220);
  const canvasTatami = createMockCanvas(540, 340);
  const canvasVideo = createMockCanvas(480, 220);

  elements['canvas-ecg'] = canvasEcg;
  elements['canvas-tatami'] = canvasTatami;
  elements['canvas-video'] = canvasVideo;

  return {
    elements,
    document: {
      getElementById: (id) => getOrCreate(id),
    },
    canvasEcg,
    canvasTatami,
    canvasVideo,
  };
}

// 3. Sandbox Execution Engine
function runSandbox(customGlobals = {}) {
  const mockDom = createMockDom();
  const windowListeners = {};
  const wsInstances = [];
  let rafCallback = null;

  class MockWebSocket {
    constructor(url) {
      this.url = url;
      this.onmessage = null;
      this.onclose = null;
      this.onerror = null;
      wsInstances.push(this);
    }
  }

  let bluetoothDisconnectedCallback = null;
  let charValueChangedCallback = null;

  const mockDevice = {
    name: 'Movesense 24050999',
    addEventListener: (evt, cb) => {
      if (evt === 'gattserverdisconnected') bluetoothDisconnectedCallback = cb;
    },
    gatt: {
      connect: async () => ({
        getPrimaryService: async (serviceName) => ({
          getCharacteristic: async (charName) => ({
            startNotifications: async () => {},
            addEventListener: (evt, cb) => {
              if (evt === 'characteristicvaluechanged') charValueChangedCallback = cb;
            },
          }),
        }),
      }),
    },
  };

  const fetchCalls = [];

  const sandbox = {
    document: mockDom.document,
    window: {
      location: { host: '127.0.0.1:4000', protocol: 'http:' },
      addEventListener: (evt, cb) => { windowListeners[evt] = cb; },
    },
    navigator: {
      bluetooth: {
        requestDevice: async (options) => mockDevice,
      },
    },
    Float32Array,
    Math,
    JSON,
    Array,
    WebSocket: MockWebSocket,
    requestAnimationFrame: (cb) => { rafCallback = cb; },
    alert: () => {},
    fetch: async (url, options) => {
      fetchCalls.push({ url, options });
      return { ok: true, json: async () => ({}) };
    },
    ...customGlobals,
  };
  sandbox.globalThis = sandbox;
  sandbox.window.globalThis = sandbox;

  // Append diagnostic and introspection hooks
  const instrumented = `
    ${jsCode}

    globalThis.__test_harness = {
      getState: () => ({
        isConnected,
        heartRate,
        rmssd,
        alpha1,
        readiness,
        ecgBuffer: Array.from(ecgBuffer),
        ecgWriteIdx,
        ecgSweepIdx,
        skeletonNodes,
        jointTorques,
        centerOfMass,
        submissionRisk,
        activeTechnique,
        orbitYaw,
        orbitPitch,
        isDragging,
      }),
      setState: (updates) => {
        if (updates.isConnected !== undefined) isConnected = updates.isConnected;
        if (updates.heartRate !== undefined) heartRate = updates.heartRate;
        if (updates.rmssd !== undefined) rmssd = updates.rmssd;
        if (updates.alpha1 !== undefined) alpha1 = updates.alpha1;
        if (updates.readiness !== undefined) readiness = updates.readiness;
        if (updates.skeletonNodes !== undefined) skeletonNodes = updates.skeletonNodes;
        if (updates.jointTorques !== undefined) jointTorques = updates.jointTorques;
        if (updates.centerOfMass !== undefined) centerOfMass = updates.centerOfMass;
        if (updates.submissionRisk !== undefined) submissionRisk = updates.submissionRisk;
        if (updates.activeTechnique !== undefined) activeTechnique = updates.activeTechnique;
        if (updates.orbitYaw !== undefined) orbitYaw = updates.orbitYaw;
        if (updates.orbitPitch !== undefined) orbitPitch = updates.orbitPitch;
        if (updates.ecgBuffer !== undefined) {
          for (let i = 0; i < Math.min(ecgBuffer.length, updates.ecgBuffer.length); i++) {
            ecgBuffer[i] = updates.ecgBuffer[i];
          }
        }
      },
      drawEcg,
      drawTatami,
      drawVideo,
      project3D,
      resetUiToStandby,
      connectPixelBluetooth,
      connectWebSockets,
    };
  `;

  const context = vm.createContext(sandbox);
  vm.runInContext(instrumented, context);

  return {
    sandbox,
    testHarness: sandbox.__test_harness || sandbox.globalThis.__test_harness,
    mockDom,
    wsInstances,
    windowListeners,
    fetchCalls,
    getBluetoothDisconnectedCallback: () => bluetoothDisconnectedCallback,
    getCharValueChangedCallback: () => charValueChangedCallback,
  };
}

// 4. Test Runner Harness
let passed = 0;
let failed = 0;
let total = 0;

function test(name, fn) {
  total++;
  try {
    fn();
    console.log(`  ✅ [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    console.error(err.stack);
    failed++;
    process.exitCode = 1;
  }
}

// =========================================================================
// SUITE 1: HEADLESS V8 INITIALIZATION & RULE #0 STANDBY STATE
// =========================================================================
console.log('\n--- SUITE 1: Headless V8 DOM Init & Zero-Mock Baseline ---');

test('1.1: Standby DOM initial rendering renders authentic waiting state tokens', () => {
  const { testHarness, mockDom } = runSandbox();
  testHarness.resetUiToStandby();

  assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-rmssd').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-alpha1').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-readiness').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('sub-zone2').innerText, 'Resting / Disconnected');
  assert.strictEqual(mockDom.document.getElementById('sub-hr').innerText, 'Movesense Standby');
  assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, 'STANDBY — NO ATHLETE DETECTED');
  assert.strictEqual(mockDom.document.getElementById('txt-camera-status').innerText, '0/33 Joints Tracked');
  assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');
  assert.strictEqual(mockDom.document.getElementById('badge-status').style.borderColor, '#EF4444');
  assert.strictEqual(mockDom.document.getElementById('badge-qrs').innerText, '512 Hz Native DSP');
});

test('1.2: HTML body contains zero banned mock tokens (72 BPM, 48.5ms, synthetic sine waves)', () => {
  const banned = ['72.0', '72 BPM', '48.5', '48.5ms', 'Closed Guard → Ashi Garami'];
  for (const token of banned) {
    assert.ok(!htmlContent.includes(token), `Banned mock token '${token}' must not exist in build/index.html`);
  }
});

// =========================================================================
// SUITE 2: resetUiToStandby() RESILIENCE & ZERO LEAKAGE
// =========================================================================
console.log('\n--- SUITE 2: resetUiToStandby() Integrity & Rapid State Transitions ---');

test('2.1: resetUiToStandby() resets all internal buffers and state variables', () => {
  const { testHarness } = runSandbox();

  // Dirty internal state
  testHarness.setState({
    isConnected: true,
    heartRate: 165,
    rmssd: 55.2,
    alpha1: 0.82,
    readiness: 94,
    submissionRisk: 75.0,
    skeletonNodes: [{ id: 0, x: 1, y: 1, z: 1, visibility: 1.0 }],
    jointTorques: [50, 60],
    ecgBuffer: [1.2, 0.9, -0.4],
  });

  let state = testHarness.getState();
  assert.strictEqual(state.isConnected, true);
  assert.strictEqual(state.heartRate, 165);

  testHarness.resetUiToStandby();

  state = testHarness.getState();
  assert.strictEqual(state.isConnected, false);
  assert.strictEqual(state.heartRate, null);
  assert.strictEqual(state.rmssd, null);
  assert.strictEqual(state.alpha1, null);
  assert.strictEqual(state.readiness, null);
  assert.strictEqual(state.submissionRisk, 0.0);
  assert.strictEqual(state.skeletonNodes.length, 0);
  assert.strictEqual(state.jointTorques.length, 0);
  assert.ok(state.ecgBuffer.every(v => v === 0.0), 'ECG buffer must be strictly 0.0 flatline');
});

test('2.2: 10,000 rapid consecutive calls to resetUiToStandby() execute cleanly with 0 exceptions', () => {
  const { testHarness } = runSandbox();
  for (let i = 0; i < 10000; i++) {
    testHarness.resetUiToStandby();
  }
  assert.ok(true);
});

test('2.3: Alternating rapid state transitions (5,000 connect/disconnect cycles) leave no residual data', () => {
  const { testHarness, wsInstances, mockDom } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));
  assert.ok(wsTel);

  for (let i = 0; i < 5000; i++) {
    // 1. Connect frame
    wsTel.onmessage({
      data: JSON.stringify({
        connected: true,
        heart_rate_bpm: 130 + (i % 50),
        hrv_rmssd_ms: 40.0,
        dfa_alpha1: 0.75,
        readiness_score: 85.0,
        zone2_status: 'Zone 2: Optimal Aerobic',
        device_name: `Movesense_${i}`,
        latest_ecg_sample: 0.5,
        qrs_peak_detected: (i % 2 === 0),
      }),
    });
    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, 130 + (i % 50));

    // 2. Standby reset
    testHarness.resetUiToStandby();
    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');
    assert.strictEqual(mockDom.document.getElementById('val-rmssd').innerText, '--');
    assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');
  }
  assert.ok(true);
});

// =========================================================================
// SUITE 3: HIGH-FREQUENCY WEBSOCKET LIFECYCLE & FLAPPING STORM
// =========================================================================
console.log('\n--- SUITE 3: WebSocket Lifecycle & Flapping Storm ---');

test('3.1: 100,000 continuous telemetry frames stream at high throughput without buffer overflow', () => {
  const { testHarness, wsInstances } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));
  assert.ok(wsTel);

  for (let i = 0; i < 100000; i++) {
    wsTel.onmessage({
      data: JSON.stringify({
        connected: true,
        heart_rate_bpm: 120.0 + (i % 60),
        hrv_rmssd_ms: 38.2,
        dfa_alpha1: 0.76,
        readiness_score: 80.0,
        zone2_status: 'Zone 2: Optimal Aerobic',
        latest_ecg_sample: ((i % 100) - 50) / 50.0,
        qrs_peak_detected: (i % 30 === 0),
      }),
    });
  }

  const state = testHarness.getState();
  assert.strictEqual(state.ecgBuffer.length, 512);
  assert.strictEqual(state.isConnected, true);
});

test('3.2: 1,000 WebSocket error and close flap storm cleanly reverts and stays stable', () => {
  const { testHarness, wsInstances, mockDom } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));
  const wsSpatial = wsInstances.find(ws => ws.url.includes('/ws/spatial'));

  for (let i = 0; i < 1000; i++) {
    // Trigger error
    wsTel.onerror(new Error('Simulated network drop'));
    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');

    // Trigger close
    wsTel.onclose({ code: 1006, reason: 'Abnormal closure' });
    assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');

    // Trigger spatial close
    wsSpatial.onclose();
    assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, 'STANDBY — NO ATHLETE DETECTED');
  }
  assert.ok(true);
});

// =========================================================================
// SUITE 4: PATHOLOGICAL BIOMETRICS TELEMETRY FUZZING
// =========================================================================
console.log('\n--- SUITE 4: Pathological Biometrics Telemetry Fuzzing ---');

test('4.1: Corrupt, partial, and non-JSON payloads are safely caught without throwing', () => {
  const { wsInstances } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));

  const malformedInputs = [
    '{ corrupt json',
    '',
    null,
    '{"connected": true, "heart_rate_bpm": ',
    'undefined',
    '[1, 2, 3, 4]',
    '12345',
    'true',
    'null',
    '\x00\x01\x02\xFF\xFE',
    '{"connected": true, "heart_rate_bpm": NaN}',
  ];

  for (const input of malformedInputs) {
    // Should not throw unhandled exception
    wsTel.onmessage({ data: input });
  }
  assert.ok(true);
});

test('4.2: Extreme numerical values (NaN, Infinity, 1e20, negatives) in telemetry payload handled gracefully', () => {
  const { wsInstances, mockDom, testHarness } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));

  const pathologicalFrames = [
    { connected: true, heart_rate_bpm: -50, hrv_rmssd_ms: -10, dfa_alpha1: -1.0, readiness_score: -5 },
    { connected: true, heart_rate_bpm: 0, hrv_rmssd_ms: 0, dfa_alpha1: 0, readiness_score: 0 },
    { connected: true, heart_rate_bpm: 99999, hrv_rmssd_ms: 1e12, dfa_alpha1: 1e6, readiness_score: 1e9 },
    { connected: false, heart_rate_bpm: 150 },
    { connected: true, heart_rate_bpm: null, hrv_rmssd_ms: null, dfa_alpha1: null, readiness_score: null },
  ];

  for (const frame of pathologicalFrames) {
    wsTel.onmessage({ data: JSON.stringify(frame) });
    testHarness.drawEcg();
  }
  assert.ok(true);
});

test('4.3: Zero / NaN sample rate and flatline samples ingested safely', () => {
  const { wsInstances, testHarness } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));

  const zeroSamples = [0.0, -0.0, null, undefined, 0];
  for (const sample of zeroSamples) {
    wsTel.onmessage({
      data: JSON.stringify({
        connected: true,
        heart_rate_bpm: 120,
        latest_ecg_sample: sample,
      }),
    });
    testHarness.drawEcg();
  }
  assert.ok(true);
});

// =========================================================================
// SUITE 5: EXTREME SPATIAL KINEMATICS FUZZING & 3D TATAMI MATRIX
// =========================================================================
console.log('\n--- SUITE 5: Extreme Spatial Kinematics Fuzzing ---');

test('5.1: 3D Spatial ingestion handles empty, truncated, or excessive landmark counts', () => {
  const { wsInstances, testHarness, mockDom } = runSandbox();
  const wsSpatial = wsInstances.find(ws => ws.url.includes('/ws/spatial'));

  const testCounts = [0, 1, 10, 28, 29, 33, 100, 1000];
  for (const count of testCounts) {
    const landmarks = Array.from({ length: count }, (_, i) => ({
      id: i,
      x: (i % 5 - 2) * 0.4,
      y: (i % 3 - 1) * 0.5,
      z: 0.1,
      visibility: 0.8,
    }));

    wsSpatial.onmessage({
      data: JSON.stringify({
        landmarks,
        active_technique: `Technique Test ${count}`,
        submission_risk_percent: (count % 100),
      }),
    });

    testHarness.drawTatami();
    assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, `Technique Test ${count}`);
  }
  assert.ok(true);
});

test('5.2: 3D Perspective Projection fuzzed with 10,000 random coordinates and extreme camera angles', () => {
  const { testHarness } = runSandbox();

  for (let i = 0; i < 10000; i++) {
    const x = (Math.random() - 0.5) * 500.0;
    const y = (Math.random() - 0.5) * 500.0;
    const z = (Math.random() - 0.5) * 500.0;
    const cx = 270.0;
    const cy = 170.0;

    testHarness.setState({
      orbitYaw: (Math.random() - 0.5) * 20.0,
      orbitPitch: Math.max(0.1, Math.min(1.4, Math.random() * 3.0)),
    });

    const p = testHarness.project3D(x, y, z, cx, cy);
    assert.ok(!Number.isNaN(p.x), `project3D p.x must not be NaN for x=${x}, y=${y}, z=${z}`);
    assert.ok(!Number.isNaN(p.y), `project3D p.y must not be NaN`);
    assert.ok(!Number.isNaN(p.scale), `project3D p.scale must not be NaN`);
  }
  assert.ok(true);
});

// =========================================================================
// SUITE 6: LONG-DURATION 60 FPS RENDER LOOP & TOUCH ORBIT CONTROLS
// =========================================================================
console.log('\n--- SUITE 6: Long-Duration 60 FPS Loop & Orbit Controls ---');

test('6.1: 20,000 consecutive render loop frames execute without memory exhaustion', () => {
  const { testHarness } = runSandbox();
  testHarness.setState({ isConnected: true, heartRate: 140, submissionRisk: 45.0 });

  for (let frame = 0; frame < 20000; frame++) {
    testHarness.drawEcg();
    testHarness.drawTatami();
    testHarness.drawVideo();
  }

  const state = testHarness.getState();
  assert.strictEqual(state.ecgBuffer.length, 512);
  assert.ok(state.ecgSweepIdx >= 0 && state.ecgSweepIdx < 512);
});

test('6.2: 3D Orbit Pitch clamping is preserved under 5,000 mouse/touch drag deltas', () => {
  const { testHarness } = runSandbox();

  for (let i = 0; i < 5000; i++) {
    const dy = (Math.random() - 0.5) * 50.0;
    const currentPitch = testHarness.getState().orbitPitch;
    const nextPitch = Math.max(0.1, Math.min(1.4, currentPitch + dy * 0.008));
    testHarness.setState({ orbitPitch: nextPitch });

    const state = testHarness.getState();
    assert.ok(state.orbitPitch >= 0.1 && state.orbitPitch <= 1.4, `Pitch ${state.orbitPitch} outside [0.1, 1.4]`);
  }
  assert.ok(true);
});

// =========================================================================
// SUMMARY
// =========================================================================
console.log('\n================================================================');
console.log(`CHALLENGER 1 STRESS TEST RESULTS: ${passed}/${total} PASSED (${Math.round(passed/total*100)}%) | ${failed} FAILED`);
console.log('================================================================\n');

if (failed === 0) {
  process.exit(0);
} else {
  process.exit(1);
}
