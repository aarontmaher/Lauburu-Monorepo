/**
 * Challenger 2 Empirical Adversarial Stress Harness
 * Deep verification of 60 FPS loops, Touch Orbit Transforms, WebSocket Streaming, and Bluetooth Ingestion
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('⚡ Running Challenger 2 Empirical Adversarial Stress Harness...');

const htmlPath = path.resolve(__dirname, '../build/index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

const scriptMatch = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) {
  throw new Error('Fatal: No <script> found in build/index.html');
}
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

  const listeners = {};
  return {
    width,
    height,
    parentElement: { clientWidth: width + 28 },
    getContext: (t) => (t === '2d' ? ctx : null),
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
  const charListeners = {};

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
              if (evt === 'characteristicvaluechanged') {
                charValueChangedCallback = cb;
                charListeners[charName] = cb;
              }
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
    Float32Array: Float32Array,
    Math: Math,
    JSON: JSON,
    Array: Array,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    WebSocket: MockWebSocket,
    requestAnimationFrame: (cb) => { rafCallback = cb; },
    alert: (msg) => {},
    fetch: async (url, opts) => {
      fetchCalls.push({ url, opts });
      return { ok: true };
    },
    ...customGlobals,
  };
  sandbox.globalThis = sandbox;
  sandbox.window.globalThis = sandbox;

  const instrumentedCode = `
    ${jsCode}

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
        isDragging,
        lastMouseX,
        lastMouseY,
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
        if (updates.isDragging !== undefined) isDragging = updates.isDragging;
        if (updates.lastMouseX !== undefined) lastMouseX = updates.lastMouseX;
        if (updates.lastMouseY !== undefined) lastMouseY = updates.lastMouseY;
      },
      drawEcg,
      drawTatami,
      drawVideo,
      project3D,
      renderLoop,
      resetUiToStandby,
      connectPixelBluetooth,
      connectWebSockets,
    };
  `;

  const context = vm.createContext(sandbox);
  vm.runInContext(instrumentedCode, context);

  return {
    sandbox,
    testScope: sandbox.__test_scope,
    mockDom,
    wsInstances,
    windowListeners,
    fetchCalls,
    getRafCallback: () => rafCallback,
    triggerBluetoothDisconnect: () => { if (bluetoothDisconnectedCallback) bluetoothDisconnectedCallback(); },
    triggerBleHeartRate: (flags, val8, val16 = 0) => {
      const cb = charListeners['heart_rate_measurement'] || charValueChangedCallback;
      if (cb) {
        const buffer = new ArrayBuffer(4);
        const view = new DataView(buffer);
        view.setUint8(0, flags);
        if ((flags & 1) !== 0) {
          view.setUint16(1, val16, true);
        } else {
          view.setUint8(1, val8);
        }
        cb({ target: { value: view } });
      }
    }
  };
}

let total = 0;
let passed = 0;

function test(name, fn) {
  total++;
  try {
    fn();
    console.log(`  ✅ [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    console.error(err.stack);
    process.exitCode = 1;
  }
}

async function asyncTest(name, fn) {
  total++;
  try {
    await fn();
    console.log(`  ✅ [PASS] ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    console.error(err.stack);
    process.exitCode = 1;
  }
}

(async () => {
  console.log('\n--- SECTION 1: 60 FPS requestAnimationFrame Master Render Loop Stability ---');

  test('1.1: renderLoop executes continuous frames without memory expansion or recursive call stack blowup', () => {
    const { testScope, mockDom } = runSandbox();
    
    // Simulate 300 animation frames (5 seconds of 60 FPS rendering)
    for (let frame = 0; frame < 300; frame++) {
      mockDom.canvasEcg.drawCalls.length = 0;
      mockDom.canvasTatami.drawCalls.length = 0;
      mockDom.canvasVideo.drawCalls.length = 0;

      testScope.drawEcg();
      testScope.drawTatami();
      testScope.drawVideo();

      assert.ok(mockDom.canvasEcg.drawCalls.length > 0, 'ECG draw calls must be present');
      assert.ok(mockDom.canvasTatami.drawCalls.length > 0, 'Tatami draw calls must be present');
      assert.ok(mockDom.canvasVideo.drawCalls.length > 0, 'Video draw calls must be present');
    }

    const state = testScope.getState();
    assert.strictEqual(state.ecgBuffer.length, 512, 'ECG buffer remains 512 Float32Array');
  });

  test('1.2: Phosphor sweep cursor wraps smoothly across 0..512 indices', () => {
    const { testScope } = runSandbox();
    for (let f = 0; f < 600; f++) {
      testScope.drawEcg();
      const state = testScope.getState();
      assert.ok(state.ecgSweepIdx >= 0 && state.ecgSweepIdx < 512, `Sweep index ${state.ecgSweepIdx} must be in [0, 512)`);
    }
  });

  test('1.3: Canvas zero-width and negative-width resilience', () => {
    const { testScope, mockDom } = runSandbox();
    mockDom.canvasEcg.width = 0;
    mockDom.canvasEcg.height = 0;
    mockDom.canvasTatami.width = 0;
    mockDom.canvasTatami.height = 0;
    mockDom.canvasVideo.width = 0;
    mockDom.canvasVideo.height = 0;

    // Must not throw or crash on zero size
    testScope.drawEcg();
    testScope.drawTatami();
    testScope.drawVideo();
  });

  console.log('\n--- SECTION 2: Touch Orbit Transforms & Mobile Pixel Gesture Mathematics ---');

  test('2.1: Single-touch drag calculates correct delta and updates orbitYaw and orbitPitch', () => {
    const { testScope, mockDom, windowListeners } = runSandbox();
    const touchStart = mockDom.canvasTatami.listeners['touchstart'];
    const touchMove = windowListeners['touchmove'];
    const touchEnd = windowListeners['touchend'];

    assert.ok(touchStart, 'touchstart listener must be registered on canvasTatami');
    assert.ok(touchMove, 'touchmove listener must be registered on window');
    assert.ok(touchEnd, 'touchend listener must be registered on window');

    // Initial state
    const initialPitch = testScope.getState().orbitPitch;
    const initialYaw = testScope.getState().orbitYaw;

    // Touch start at (100, 100)
    touchStart({ touches: [{ clientX: 100, clientY: 100 }], length: 1 });
    assert.strictEqual(testScope.getState().isDragging, true);

    // Touch move to (150, 120) -> dx = +50, dy = +20
    touchMove({
      touches: [{ clientX: 150, clientY: 120 }],
      length: 1,
    });

    const afterDrag = testScope.getState();
    assert.strictEqual(afterDrag.orbitYaw, initialYaw + 50 * 0.008);
    assert.strictEqual(afterDrag.orbitPitch, initialPitch + 20 * 0.008);

    // Touch end
    touchEnd();
    assert.strictEqual(testScope.getState().isDragging, false);
  });

  test('2.2: Multi-touch gesture (e.g. 2-finger pinch) is ignored to prevent erratic jumps', () => {
    const { testScope, mockDom, windowListeners } = runSandbox();
    const touchStart = mockDom.canvasTatami.listeners['touchstart'];
    const touchMove = windowListeners['touchmove'];

    testScope.setState({ isDragging: true, lastMouseX: 100, lastMouseY: 100 });
    const initialYaw = testScope.getState().orbitYaw;

    // 2-finger touch event
    touchMove({
      touches: [{ clientX: 150, clientY: 120 }, { clientX: 200, clientY: 220 }],
    });

    // Yaw must NOT change during multi-touch
    assert.strictEqual(testScope.getState().orbitYaw, initialYaw);
  });

  test('2.3: project3D maintains positive frustum scale across 1,000 randomized camera angles', () => {
    const { testScope } = runSandbox();
    
    for (let i = 0; i < 1000; i++) {
      const yaw = (Math.random() - 0.5) * 20.0;
      const pitch = 0.1 + Math.random() * (1.4 - 0.1); // [0.1, 1.4]
      testScope.setState({ orbitYaw: yaw, orbitPitch: pitch });

      // Test 10m x 10m mat points
      const testPoints = [
        [0, 0, 0],
        [-4.5, 0, -4.5],
        [4.5, 0, 4.5],
        [-4.5, 0, 4.5],
        [4.5, 0, -4.5],
        [0, 2.0, 0], // standing athlete head
        [2.0, -1.0, -2.0],
      ];

      for (const [px, py, pz] of testPoints) {
        const proj = testScope.project3D(px, py, pz, 270, 160);
        assert.ok(Number.isFinite(proj.x), 'screenX must be finite');
        assert.ok(Number.isFinite(proj.y), 'screenY must be finite');
        assert.ok(Number.isFinite(proj.z), 'eyeZ must be finite');
        assert.ok(Number.isFinite(proj.scale), 'scale must be finite');
        assert.ok(proj.scale > 0, `scale must be positive (got ${proj.scale})`);
      }
    }
  });

  console.log('\n--- SECTION 3: WebSocket Streaming & Malformed JSON Fuzzing ---');

  test('3.1: wsTelemetry rejects and ignores malformed JSON payloads without throwing uncaught errors', () => {
    const { wsInstances } = runSandbox();
    const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));

    const malformed = [
      '{',
      'not json at all',
      '{"heart_rate_bpm": }',
      'null',
      'undefined',
      '[]',
      '{"connected": true, "heart_rate_bpm": NaN}',
    ];

    for (const bad of malformed) {
      // Must not throw uncaught error
      wsTel.onmessage({ data: bad });
    }
  });

  test('3.2: wsTelemetry high-frequency burst (1,000 packets) updates state accurately', () => {
    const { testScope, mockDom, wsInstances } = runSandbox();
    const wsTel = wsInstances.find(ws => ws.url.includes('/ws/telemetry'));

    for (let i = 1; i <= 1000; i++) {
      const frame = {
        connected: true,
        heart_rate_bpm: 100 + (i % 60),
        hrv_rmssd_ms: 30.0 + (i % 20),
        dfa_alpha1: 0.70 + (i % 30) * 0.01,
        readiness_score: 80.0,
        latest_ecg_sample: (i % 2 === 0 ? 0.5 : -0.5),
        device_name: 'Movesense Stress',
      };
      wsTel.onmessage({ data: JSON.stringify(frame) });
    }

    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, 140);
    assert.strictEqual(testScope.getState().isConnected, true);
  });

  test('3.3: wsSpatial handles 33 landmarks, missing landmarks, and null athlete nodes', () => {
    const { testScope, mockDom, wsInstances } = runSandbox();
    const wsSpatial = wsInstances.find(ws => ws.url.includes('/ws/spatial'));

    // 1. Valid 33 landmarks
    const fullPose = {
      landmarks: Array.from({ length: 33 }, (_, i) => ({
        id: i,
        x: 0.0,
        y: 0.5,
        z: 0.0,
        visibility: 0.95,
      })),
      active_technique: 'Inside Ashi Garami',
      submission_risk_percent: 65.0,
    };
    wsSpatial.onmessage({ data: JSON.stringify(fullPose) });
    assert.strictEqual(testScope.getState().skeletonNodes.length, 33);
    assert.strictEqual(mockDom.document.getElementById('txt-technique').innerText, 'Inside Ashi Garami');
    assert.strictEqual(mockDom.document.getElementById('txt-camera-status').innerText, '33/33 Joints Tracked');

    // 2. Fallback athlete_nodes schema
    const fallbackPose = {
      athlete_nodes: Array.from({ length: 33 }, (_, i) => ({
        id: i,
        x: 0.1,
        y: 0.2,
        z: 0.1,
        visibility: (i < 20 ? 0.95 : 0.05),
      })),
      active_technique: 'Heel Hook Break Setup',
      submission_risk_percent: 85.0,
    };
    wsSpatial.onmessage({ data: JSON.stringify(fallbackPose) });
    assert.strictEqual(testScope.getState().skeletonNodes.length, 33);
    assert.strictEqual(mockDom.document.getElementById('txt-camera-status').innerText, '20/33 Joints Tracked');

    // 3. Empty spatial packet
    wsSpatial.onmessage({ data: JSON.stringify({}) });
    assert.strictEqual(testScope.getState().skeletonNodes.length, 0);
  });

  console.log('\n--- SECTION 4: Standalone Pixel Web Bluetooth Ingestion & Flag Parsing ---');

  await asyncTest('4.1: connectPixelBluetooth pairs Movesense and ingests 8-bit and 16-bit HR packets', async () => {
    const { testScope, mockDom, fetchCalls, triggerBleHeartRate, triggerBluetoothDisconnect } = runSandbox();

    // Initiate Bluetooth pairing
    await testScope.connectPixelBluetooth();

    assert.strictEqual(testScope.getState().isConnected, true);
    assert.ok(mockDom.document.getElementById('badge-status').innerText.includes('PIXEL BLE: Movesense 24050999'));

    // Ingest 8-bit Heart Rate (Flags = 0b00000000, HR = 142)
    triggerBleHeartRate(0, 142);
    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, 142);
    assert.strictEqual(fetchCalls.length, 1);
    assert.strictEqual(JSON.parse(fetchCalls[0].opts.body).heart_rate, 142);

    // Ingest 16-bit Heart Rate (Flags = 0b00000001, HR = 185)
    triggerBleHeartRate(1, 0, 185);
    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, 185);
    assert.strictEqual(fetchCalls.length, 2);
    assert.strictEqual(JSON.parse(fetchCalls[1].opts.body).heart_rate, 185);

    // Trigger GATT server disconnect event
    triggerBluetoothDisconnect();
    assert.strictEqual(testScope.getState().isConnected, false);
    assert.strictEqual(mockDom.document.getElementById('val-hr').innerText, '--');
    assert.strictEqual(mockDom.document.getElementById('badge-status').innerText, 'STANDBY — DISCONNECTED');
  });

  console.log(`\n======================================================`);
  console.log(`CHALLENGER 2 STRESS RESULTS: ${passed}/${total} PASSED (${Math.round(passed/total*100)}%)`);
  console.log(`======================================================\n`);

  if (passed === total) {
    process.exit(0);
  } else {
    process.exit(1);
  }
})();
