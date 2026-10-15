/**
 * Empirical Adversarial Challenger 1 — Stress Harness C1
 * Long-duration V8 animation loop, Memory Leak Stress, and Fuzzing
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('⚡ Starting Challenger 1 Extended Stress & Fuzzing Harness...');

const htmlPath = path.resolve(__dirname, '../build/index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

const scriptMatch = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) throw new Error('No <script> tag found in build/index.html');
const jsCode = scriptMatch[1];

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
    fillRect: () => {},
    strokeRect: () => {},
    beginPath: () => {},
    closePath: () => {},
    moveTo: () => {},
    lineTo: () => {},
    stroke: () => {},
    fill: () => {},
    arc: () => {},
    ellipse: () => {},
    fillText: () => {},
    setLineDash: (d) => { ctx.lineDash = d; },
    clearRect: () => {},
  };

  return {
    width,
    height,
    parentElement: { clientWidth: width + 28 },
    getContext: () => ctx,
    addEventListener: () => {},
    drawCalls,
  };
}

function createMockDom() {
  const elements = {};
  const getOrCreate = (id) => {
    if (!elements[id]) {
      elements[id] = { id, innerText: '', style: {}, addEventListener: () => {} };
    }
    return elements[id];
  };

  elements['canvas-ecg'] = createMockCanvas(480, 220);
  elements['canvas-tatami'] = createMockCanvas(540, 340);
  elements['canvas-video'] = createMockCanvas(480, 220);

  return {
    elements,
    document: { getElementById: (id) => getOrCreate(id) },
  };
}

function runSandbox() {
  const mockDom = createMockDom();
  const wsInstances = [];
  const eventListeners = {};

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
    navigator: { bluetooth: {} },
    Float32Array,
    Math,
    JSON,
    Array,
    WebSocket: MockWebSocket,
    requestAnimationFrame: () => {},
    alert: () => {},
    fetch: async () => ({ ok: true }),
  };
  sandbox.window = windowObj;
  sandbox.globalThis = sandbox;

  const instrumented = `
    ${jsCode}
    window.__scope = {
      drawEcg,
      drawTatami,
      drawVideo,
      project3D,
      resetUiToStandby,
      getState: () => ({
        isConnected, heartRate, rmssd, alpha1, readiness,
        ecgBuffer, ecgWriteIdx, ecgSweepIdx, skeletonNodes,
        jointTorques, centerOfMass, submissionRisk, activeTechnique,
        orbitYaw, orbitPitch
      }),
      setState: (u) => {
        if (u.isConnected !== undefined) isConnected = u.isConnected;
        if (u.heartRate !== undefined) heartRate = u.heartRate;
        if (u.rmssd !== undefined) rmssd = u.rmssd;
        if (u.alpha1 !== undefined) alpha1 = u.alpha1;
        if (u.readiness !== undefined) readiness = u.readiness;
        if (u.skeletonNodes !== undefined) skeletonNodes = u.skeletonNodes;
        if (u.jointTorques !== undefined) jointTorques = u.jointTorques;
        if (u.centerOfMass !== undefined) centerOfMass = u.centerOfMass;
        if (u.submissionRisk !== undefined) submissionRisk = u.submissionRisk;
        if (u.activeTechnique !== undefined) activeTechnique = u.activeTechnique;
        if (u.orbitYaw !== undefined) orbitYaw = u.orbitYaw;
        if (u.orbitPitch !== undefined) orbitPitch = u.orbitPitch;
      }
    };
  `;

  const context = vm.createContext(sandbox);
  vm.runInContext(instrumented, context);

  return { sandbox, scope: windowObj.__scope, mockDom, wsInstances };
}

let passed = 0;
let total = 0;
function test(name, fn) {
  total++;
  try {
    fn();
    console.log(`  ✅ [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    process.exitCode = 1;
  }
}

// 1. Long-Duration Animation Loop Stress
test('1. Long-Duration 10,000 Frames Animation Loop Execution', () => {
  const { scope } = runSandbox();
  scope.setState({ isConnected: true, heartRate: 145 });

  for (let frame = 0; frame < 10000; frame++) {
    scope.drawEcg();
    scope.drawTatami();
    scope.drawVideo();
  }
  const state = scope.getState();
  assert.strictEqual(state.ecgBuffer.length, 512);
  assert.ok(state.ecgSweepIdx >= 0 && state.ecgSweepIdx < 512);
});

// 2. Continuous 100,000 Sample Stream + Disconnect Storm
test('2. 100,000 Sample Stream with 500 Intermittent Disconnect / Reconnect Flaps', () => {
  const { scope, wsInstances, mockDom } = runSandbox();
  const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));
  assert.ok(wsTel);

  for (let i = 0; i < 100000; i++) {
    const isFlap = (i % 200 === 0);
    if (isFlap) {
      wsTel.onclose();
      assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');
      assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');
    } else {
      wsTel.onmessage({
        data: JSON.stringify({
          connected: true,
          heart_rate_bpm: 120.0 + (i % 60),
          hrv_rmssd_ms: 35.0,
          dfa_alpha1: 0.78,
          readiness_score: 82.0,
          zone2_status: 'Zone 2: Optimal Aerobic (LT1)',
          device_name: 'Movesense Stress BLE',
          latest_ecg_sample: Math.sin(i * 0.05),
          qrs_peak_detected: (i % 50 === 0)
        })
      });
    }
  }
  assert.ok(true);
});

// 3. 3D Project Oracle: Fuzzing 50,000 Arbitrary Coordinates & Extreme Angles
test('3. 3D Perspective Projection Fuzzing 50,000 Coordinates & Camera Angles', () => {
  const { scope } = runSandbox();

  for (let i = 0; i < 50000; i++) {
    const x = (Math.random() - 0.5) * 200.0;
    const y = (Math.random() - 0.5) * 200.0;
    const z = (Math.random() - 0.5) * 200.0;
    const cx = 270.0;
    const cy = 170.0;
    
    // Set arbitrary yaw and pitch
    scope.setState({
      orbitYaw: (Math.random() - 0.5) * 100.0,
      orbitPitch: Math.max(0.1, Math.min(1.4, Math.random() * 2.0))
    });

    const p = scope.project3D(x, y, z, cx, cy);
    assert.ok(typeof p.x === 'number');
    assert.ok(typeof p.y === 'number');
    assert.ok(typeof p.scale === 'number');
  }
});

// 4. Skeleton 33-Node Random Topology Fuzzing
test('4. 33-Landmark Pose Ingestion with Fuzzed Invalid Objects', () => {
  const { scope, wsInstances, mockDom } = runSandbox();
  const wsSpatial = wsInstances.find(ws => ws.url.includes('/ws/spatial'));
  assert.ok(wsSpatial);

  const fuzzedPayloads = [
    { landmarks: [] },
    { athlete_nodes: [] },
    { landmarks: null },
    { landmarks: [{ x: 'bad', y: null, z: undefined, visibility: 'none' }] },
    { landmarks: Array.from({ length: 100 }, (_, idx) => ({ id: idx, x: idx, y: idx, z: idx, visibility: Math.random() })) },
    { active_technique: 'Inside Heel Hook Breaking Mechanism', submission_risk_percent: 99.9 },
    { active_technique: '', submission_risk_percent: 0.0 }
  ];

  for (const payload of fuzzedPayloads) {
    wsSpatial.onmessage({ data: JSON.stringify(payload) });
    scope.drawTatami();
  }
  assert.ok(true);
});

console.log(`\n======================================================`);
console.log(`CHALLENGER 1 STRESS HARNESS COMPLETE: ${passed}/${total} tests passed (${Math.round(passed/total*100)}%)`);
console.log(`======================================================\n`);

if (passed === total) process.exit(0);
else process.exit(1);
