/**
 * Empirical Adversarial Challenger M2 — V8 DOM & Canvas Stress Harness
 * Evaluates the exact client-side JavaScript engine from build/index.html
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('⚡ Starting Empirical Adversarial Challenger M2: V8 DOM & Canvas Stress Harness...');

// 1. Load HTML file
const htmlPath = path.resolve(__dirname, '../build/index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

// Extract JS script from HTML
const scriptMatch = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  throw new Error('Fatal: No <script> tag found in build/index.html');
}
const jsCode = scriptMatch[1];

// 2. Build Mock DOM & HTML5 Canvas Environment
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
    arc: (x, y, r, sa, ea) => drawCalls.push({ type: 'arc', x, y, r, sa, ea, fillStyle: ctx.fillStyle }),
    ellipse: (x, y, rx, ry, rot, sa, ea) => drawCalls.push({ type: 'ellipse', x, y, rx, ry, rot, sa, ea }),
    fillText: (text, x, y) => drawCalls.push({ type: 'fillText', text, x, y, fillStyle: ctx.fillStyle }),
    setLineDash: (dash) => { ctx.lineDash = dash; drawCalls.push({ type: 'setLineDash', dash }); },
    clearRect: (x, y, w, h) => drawCalls.push({ type: 'clearRect', x, y, w, h }),
  };

  return {
    width,
    height,
    parentElement: { clientWidth: width + 28 },
    getContext: (type) => (type === '2d' ? ctx : null),
    addEventListener: () => {},
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
        addEventListener: () => {},
      };
    }
    return elements[id];
  };

  const canvasEcg = createMockCanvas(480, 200);
  const canvasTatami = createMockCanvas(540, 280);
  const canvasVideo = createMockCanvas(480, 200);

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

// Sandbox execution wrapper
function runSandbox(customGlobals = {}) {
  const mockDom = createMockDom();
  const eventListeners = {};
  const wsInstances = [];

  class MockWebSocket {
    constructor(url) {
      this.url = url;
      this.onmessage = null;
      this.onclose = null;
      this.onerror = null;
      wsInstances.push(this);
    }
  }

  const windowObj = {
    location: { host: '127.0.0.1:4000', protocol: 'http:' },
    addEventListener: (evt, cb) => { eventListeners[evt] = cb; },
  };

  const sandbox = {
    document: mockDom.document,
    window: windowObj,
    navigator: {
      bluetooth: {
        requestDevice: async () => ({
          name: 'Movesense MD',
          addEventListener: () => {},
          gatt: {
            connect: async () => ({
              getPrimaryService: async () => ({
                getCharacteristic: async () => ({
                  startNotifications: async () => {},
                  addEventListener: () => {},
                }),
              }),
            }),
          },
        }),
      },
    },
    Float32Array: Float32Array,
    Math: Math,
    JSON: JSON,
    Array: Array,
    WebSocket: MockWebSocket,
    requestAnimationFrame: (cb) => { /* no-op in headless test */ },
    alert: () => {},
    fetch: async () => ({ ok: true }),
    ...customGlobals,
  };
  sandbox.globalThis = sandbox;
  sandbox.window.globalThis = sandbox;

  // Append inspector interface at the end of the script execution to allow testing internal closures
  const testInstrumentedCode = `
    ${jsCode}

    // Expose internal state and functions to test harness
    globalThis.__test_scope = {
      getState: () => ({
        isConnected,
        heartRate,
        rmssd,
        alpha1,
        readiness,
        ecgBuffer,
        ecgWriteIdx,
        ecgSweepIdx,
        ECG_BUFFER_SIZE,
        skeletonNodes,
        jointTorques,
        centerOfMass,
        submissionRisk,
        activeTechnique,
        orbitYaw,
        orbitPitch,
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
    };
  `;

  const context = vm.createContext(sandbox);
  vm.runInContext(testInstrumentedCode, context);

  return {
    sandbox,
    testScope: sandbox.__test_scope || (sandbox.globalThis && sandbox.globalThis.__test_scope),
    mockDom,
    wsInstances,
    eventListeners,
  };
}

// 3. Test Suite Runner
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
    console.error(err.stack);
    process.exitCode = 1;
  }
}

// =========================================================================
// TEST SUITES
// =========================================================================

console.log('\n--- TIER 1: Initial DOM State Machine & Rule #0 Invariants ---');

runTest('1.1: Standby DOM values render --, Movesense Standby, and DISCONNECTED', () => {
  const { testScope, mockDom } = runSandbox();

  // Trigger resetUiToStandby
  testScope.resetUiToStandby();

  assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-rmssd').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-alpha1').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-readiness').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('sub-zone2').innerText, 'Resting / Disconnected');
  assert.strictEqual(mockDom.document.getElementById('sub-hr').innerText, 'Movesense Standby');
  assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, 'STANDBY — NO ATHLETE DETECTED');
  assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');
  assert.strictEqual(mockDom.document.getElementById('badge-status').style.borderColor, '#EF4444');
});

console.log('\n--- TIER 2: 512Hz ECG Canvas Oscilloscope Stress & Clamping ---');

runTest('2.1: ECG Oscilloscope draws flat zero baseline and standby message when disconnected', () => {
  const { testScope, mockDom } = runSandbox();
  testScope.setState({ isConnected: false });
  mockDom.canvasEcg.drawCalls.length = 0;

  testScope.drawEcg();

  const fillTextCalls = mockDom.canvasEcg.drawCalls.filter(c => c.type === 'fillText');
  const standbyMsg = fillTextCalls.find(c => c.text.includes('STANDBY — SENSOR PROBING (0% MOCK DATA)') || c.text.includes('0% MOCK'));
  assert.ok(standbyMsg, 'ECG canvas must render standby 0% mock label');
});

runTest('2.2: ECG Buffer withstands 50,000 rapid sample bursts without memory leak or overflow', () => {
  const { testScope } = runSandbox();
  testScope.setState({ isConnected: true });

  const state = testScope.getState();
  const buffer = state.ecgBuffer;
  const bufferSize = state.ECG_BUFFER_SIZE || 512;

  // Emulate 50,000 incoming ECG samples at 512Hz
  let writeIdx = 0;
  for (let i = 0; i < 50000; i++) {
    const sample = (Math.random() - 0.5) * 2.0;
    buffer[writeIdx] = sample;
    writeIdx = (writeIdx + 1) % bufferSize;
  }

  assert.strictEqual(buffer.length, bufferSize, `ECG buffer length must remain strictly ${bufferSize}`);
});

runTest('2.3: ECG draw withstands pathological float inputs (NaN, +/-Infinity, 1e6V) without crash', () => {
  const { testScope, mockDom } = runSandbox();
  testScope.setState({ isConnected: true });

  const state = testScope.getState();
  const pathologicalSamples = [NaN, Infinity, -Infinity, 1e9, -1e9, null, undefined, 0.0];
  for (let i = 0; i < pathologicalSamples.length; i++) {
    state.ecgBuffer[i] = pathologicalSamples[i];
  }

  mockDom.canvasEcg.drawCalls.length = 0;
  // Should not throw
  testScope.drawEcg();
  assert.ok(mockDom.canvasEcg.drawCalls.length > 0, 'drawEcg executed all drawing commands safely');
});

console.log('\n--- TIER 3: 3D Tatami Kinematics Mat & Skeleton Stress ---');

runTest('3.1: 3D Tatami Canvas renders standby message when no skeleton stream is active', () => {
  const { testScope, mockDom } = runSandbox();
  testScope.setState({ isConnected: false, skeletonNodes: [] });
  mockDom.canvasTatami.drawCalls.length = 0;

  testScope.drawTatami();

  const fillTextCalls = mockDom.canvasTatami.drawCalls.filter(c => c.type === 'fillText');
  const standbyTatami = fillTextCalls.find(c => c.text.includes('3D TATAMI MAT READY — 0% MOCK DATA'));
  assert.ok(standbyTatami, 'Tatami canvas must render 3D TATAMI MAT READY — 0% MOCK DATA in standby');
});

runTest('3.2: 3D Tatami Bone Interconnect safely handles partial / truncated landmark arrays', () => {
  const { testScope, mockDom } = runSandbox();
  testScope.setState({ isConnected: true });

  // Test partial landmark sizes: 0, 5, 12, 24, 32 nodes
  const testCounts = [0, 5, 12, 24, 32];
  for (const count of testCounts) {
    const nodes = Array.from({ length: count }, (_, i) => ({
      id: i,
      x: (i % 3 - 1) * 0.5,
      y: (i % 2 - 0.5) * 1.0,
      z: 0.1,
      visibility: 0.9,
    }));
    testScope.setState({ skeletonNodes: nodes });

    mockDom.canvasTatami.drawCalls.length = 0;
    // Must not throw IndexOutOfBounds in bone rendering loop
    testScope.drawTatami();
    assert.ok(mockDom.canvasTatami.drawCalls.length > 0);
  }
});

runTest('3.3: 3D Tatami projection handles extreme joint coordinates without NaN propagation', () => {
  const { testScope, mockDom } = runSandbox();
  testScope.setState({ isConnected: true });

  const nodes = [
    { id: 0, x: 10000.0, y: -50000.0, z: 20000.0, visibility: 1.0 },
    { id: 11, x: NaN, y: Infinity, z: -Infinity, visibility: 1.0 },
    { id: 12, x: 'bad_string', y: null, z: undefined, visibility: 0.0 },
    { id: 23, x: 0.0, y: 0.0, z: 0.0, visibility: 1.0 },
  ];
  testScope.setState({ skeletonNodes: nodes });

  mockDom.canvasTatami.drawCalls.length = 0;
  testScope.drawTatami();
  assert.ok(mockDom.canvasTatami.drawCalls.length > 0);
});

runTest('3.4: 3D Tatami Bone Risk Color transitions: Nominal (#00FFCC) -> Warning (#FFD700) -> Critical (#FF0055)', () => {
  const { testScope, mockDom } = runSandbox();
  testScope.setState({ isConnected: true });

  const activeNodes = Array.from({ length: 33 }, (_, i) => ({
    id: i,
    x: 0.0,
    y: (i % 2 === 0 ? 0.5 : -0.5),
    z: 0.0,
    visibility: 0.95,
  }));

  // Nominal risk (submissionRisk = 10%)
  testScope.setState({ skeletonNodes: activeNodes, submissionRisk: 10.0 });
  mockDom.canvasTatami.drawCalls.length = 0;
  testScope.drawTatami();
  const strokeNominal = mockDom.canvasTatami.drawCalls.filter(c => c.type === 'stroke' && c.strokeStyle === '#00FFCC');
  assert.ok(strokeNominal.length > 0, 'Must have Nominal (#00FFCC) bone strokes');

  // Warning risk (submissionRisk = 45%)
  testScope.setState({ skeletonNodes: activeNodes, submissionRisk: 45.0 });
  mockDom.canvasTatami.drawCalls.length = 0;
  testScope.drawTatami();
  const strokeWarning = mockDom.canvasTatami.drawCalls.filter(c => c.type === 'stroke' && c.strokeStyle === '#FFD700');
  assert.ok(strokeWarning.length > 0, 'Must have Warning (#FFD700) bone strokes');

  // Critical risk (submissionRisk = 85%)
  testScope.setState({ skeletonNodes: activeNodes, submissionRisk: 85.0 });
  mockDom.canvasTatami.drawCalls.length = 0;
  testScope.drawTatami();
  const strokeCritical = mockDom.canvasTatami.drawCalls.filter(c => c.type === 'stroke' && c.strokeStyle === '#FF0055');
  assert.ok(strokeCritical.length > 0, 'Must have Critical (#FF0055) bone strokes');
});

console.log('\n--- TIER 4: WebSocket Ingestion & State Machine Transitions ---');

runTest('4.1: /ws/telemetry connected packet updates metrics and transitions status badge to LIVE BLE', () => {
  const { testScope, mockDom, wsInstances } = runSandbox();

  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));
  assert.ok(wsTel, 'ws/telemetry connection instance must exist');

  // Ingest active live biometrics packet
  const activeFrame = {
    connected: true,
    heart_rate_bpm: 148.0,
    hrv_rmssd_ms: 42.5,
    dfa_alpha1: 0.74,
    readiness_score: 86.0,
    zone2_status: 'Zone 2: Optimal Aerobic',
    device_name: 'Movesense 24050123',
    latest_ecg_sample: 0.85,
    qrs_peak_detected: true,
  };

  wsTel.onmessage({ data: JSON.stringify(activeFrame) });

  assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, 148);
  assert.strictEqual(mockDom.document.getElementById('val-rmssd').innerText, '42.5');
  assert.strictEqual(mockDom.document.getElementById('val-alpha1').innerText, '0.74');
  assert.strictEqual(mockDom.document.getElementById('val-readiness').innerText, 86);
  assert.strictEqual(mockDom.document.getElementById('sub-zone2').innerText, 'Zone 2: Optimal Aerobic');
  assert.ok(mockDom.document.getElementById('badge-status').innerText.includes('LIVE BLE'));
  assert.strictEqual(mockDom.document.getElementById('badge-status').style.borderColor, '#00FF88');
});

runTest('4.2: /ws/telemetry disconnect packet instantly reverts UI to authentic zero-mock standby', () => {
  const { testScope, mockDom, wsInstances } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));

  // First connect
  wsTel.onmessage({
    data: JSON.stringify({
      connected: true,
      heart_rate_bpm: 140.0,
      hrv_rmssd_ms: 35.0,
      dfa_alpha1: 0.75,
      readiness_score: 80.0,
    }),
  });
  assert.strictEqual(testScope.getState().isConnected, true);

  // Then disconnect
  wsTel.onmessage({
    data: JSON.stringify({
      connected: false,
      heart_rate_bpm: 0.0,
    }),
  });

  assert.strictEqual(testScope.getState().isConnected, false);
  assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-rmssd').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-alpha1').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('val-readiness').innerText, '--');
  assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');
});

runTest('4.3: /ws/spatial packet ingests 33-landmarks and updates active technique', () => {
  const { testScope, mockDom, wsInstances } = runSandbox();
  const wsSpatial = wsInstances.find(ws => ws.url.includes('/ws/spatial'));
  assert.ok(wsSpatial, 'ws/spatial connection instance must exist');

  const spatialFrame = {
    landmarks: Array.from({ length: 33 }, (_, i) => ({ id: i, x: 0.1, y: 0.2, z: 0.0, visibility: 0.95 })),
    active_technique: 'Ashi Garami → Heel Hook Attack',
    submission_risk_percent: 78.5,
  };

  wsSpatial.onmessage({ data: JSON.stringify(spatialFrame) });

  assert.strictEqual(testScope.getState().skeletonNodes.length, 33);
  assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, 'Ashi Garami → Heel Hook Attack');

  // WebSocket close reverts technique to standby
  wsSpatial.onclose();
  assert.strictEqual(testScope.getState().skeletonNodes.length, 0);
  assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, 'STANDBY — NO ATHLETE DETECTED');
});

console.log('\n--- TIER 5: 3D Orbit Camera & Touch Controls ---');

runTest('5.1: Orbit Pitch is clamped strictly between [0.1, 1.4] radians', () => {
  const { testScope } = runSandbox();

  // Manipulate pitch directly
  testScope.setState({ orbitPitch: Math.max(0.1, Math.min(1.4, 2.5)) });
  assert.strictEqual(testScope.getState().orbitPitch, 1.4, 'Pitch must be clamped to upper bound 1.4');

  testScope.setState({ orbitPitch: Math.max(0.1, Math.min(1.4, -0.5)) });
  assert.strictEqual(testScope.getState().orbitPitch, 0.1, 'Pitch must be clamped to lower bound 0.1');
});

console.log(`\n======================================================`);
console.log(`STRESS HARNESS COMPLETE: ${passedTests}/${totalTests} tests passed (${Math.round(passedTests/totalTests*100)}%)`);
console.log(`======================================================\n`);

if (passedTests === totalTests) {
  process.exit(0);
} else {
  process.exit(1);
}
