/**
 * Milestone 3: Node.js V8 Web Bluetooth Mock GATT Stress Test Harness
 * File: test/stress_web_bluetooth_harness.js
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const vm = require('vm');

console.log('⚡ Starting Milestone 3 Web Bluetooth GATT Stress Harness (Node.js V8)...');

// 1. Load compiled HTML & extract JavaScript engine
const htmlPath = path.resolve(__dirname, '../build/index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');
const scriptMatch = htmlContent.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) throw new Error('Fatal: No <script> tag found in build/index.html');
const jsCode = scriptMatch[1];

// 2. Mock Web Bluetooth Implementation
class MockDataView {
  constructor(buffer) {
    this.buffer = buffer;
    this.byteLength = buffer.length;
  }
  getUint8(offset) { return this.buffer[offset]; }
  getUint16(offset, littleEndian = true) {
    if (littleEndian) {
      return this.buffer[offset] | (this.buffer[offset + 1] << 8);
    }
    return (this.buffer[offset] << 8) | this.buffer[offset + 1];
  }
}

class MockCharacteristic {
  constructor(uuid) {
    this.uuid = uuid;
    this.listeners = {};
    this.value = null;
    this.notificationsStarted = false;
  }
  addEventListener(evt, cb) {
    if (!this.listeners[evt]) this.listeners[evt] = [];
    this.listeners[evt].push(cb);
  }
  async startNotifications() {
    this.notificationsStarted = true;
    return this;
  }
  async stopNotifications() {
    this.notificationsStarted = false;
    return this;
  }
  emitValueChanged(byteArray) {
    this.value = new MockDataView(byteArray);
    const event = { target: { value: this.value } };
    if (this.listeners['characteristicvaluechanged']) {
      for (const cb of this.listeners['characteristicvaluechanged']) {
        cb(event);
      }
    }
  }
}

class MockService {
  constructor(uuid) {
    this.uuid = uuid;
    this.characteristics = {
      'heart_rate_measurement': new MockCharacteristic('0x2A37'),
      '0x2a37': new MockCharacteristic('0x2A37'),
      'battery_level': new MockCharacteristic('0x2A19'),
      '0x2a19': new MockCharacteristic('0x2A19'),
      'model_number_string': new MockCharacteristic('0x2A24'),
      'serial_number_string': new MockCharacteristic('0x2A25'),
    };
  }
  async getCharacteristic(uuid) {
    const key = String(uuid).toLowerCase();
    if (this.characteristics[key]) return this.characteristics[key];
    const char = new MockCharacteristic(uuid);
    this.characteristics[key] = char;
    return char;
  }
}

class MockGattServer {
  constructor(device) {
    this.device = device;
    this.connected = false;
    this.services = {
      'heart_rate': new MockService('0x180D'),
      '0x180d': new MockService('0x180D'),
      'battery_service': new MockService('0x180F'),
      '0x180f': new MockService('0x180F'),
      'device_information': new MockService('0x180A'),
      '0x180a': new MockService('0x180A'),
    };
  }
  async connect() {
    this.connected = true;
    return this;
  }
  disconnect() {
    this.connected = false;
    this.device.emitDisconnect();
  }
  async getPrimaryService(uuid) {
    const key = String(uuid).toLowerCase();
    if (this.services[key]) return this.services[key];
    throw new Error(`NotFoundError: Service ${uuid} not found on mock device`);
  }
}

class MockBluetoothDevice {
  constructor(name = 'Movesense 24050123') {
    this.name = name;
    this.id = 'MOCK-BLE-DEVICE-1';
    this.gatt = new MockGattServer(this);
    this.listeners = {};
  }
  addEventListener(evt, cb) {
    if (!this.listeners[evt]) this.listeners[evt] = [];
    this.listeners[evt].push(cb);
  }
  emitDisconnect() {
    if (this.listeners['gattserverdisconnected']) {
      for (const cb of this.listeners['gattserverdisconnected']) {
        cb({ target: this });
      }
    }
  }
}

// 3. Harness Runner & Test Execution Matrix
function buildSandbox(bluetoothOverride = null) {
  const domElements = {};
  const mockCtx = {
    fillStyle: '#000',
    strokeStyle: '#000',
    lineWidth: 1,
    font: '10px sans-serif',
    textAlign: 'left',
    shadowColor: 'transparent',
    shadowBlur: 0,
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
    setLineDash: () => {},
    clearRect: () => {},
  };

  const getOrCreate = (id) => {
    if (!domElements[id]) {
      domElements[id] = {
        id,
        innerText: '',
        style: {},
        width: 500,
        height: 250,
        getContext: () => mockCtx,
        addEventListener: () => {},
        remove: () => {},
      };
    }
    return domElements[id];
  };

  const defaultDevice = new MockBluetoothDevice();
  const mockNavigator = {
    bluetooth: bluetoothOverride || {
      requestDevice: async () => defaultDevice,
    },
  };

  const fetchCalls = [];
  const sandbox = {
    document: {
      getElementById: (id) => getOrCreate(id),
      createElement: (tag) => getOrCreate('elem-' + Math.random()),
    },
    window: {
      location: { host: '127.0.0.1:4000', protocol: 'http:' },
      addEventListener: () => {},
    },
    navigator: mockNavigator,
    Float32Array: Float32Array,
    Math: Math,
    JSON: JSON,
    Array: Array,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    TextDecoder: TextDecoder,
    TextEncoder: TextEncoder,
    WebSocket: class { constructor() {} },
    requestAnimationFrame: () => {},
    alert: (msg) => { sandbox.__lastAlert = msg; },
    fetch: async (url, opts) => {
      fetchCalls.push({ url, opts, body: opts?.body ? JSON.parse(opts.body) : null });
      return { ok: true, json: async () => ({}) };
    },
    defaultDevice,
    fetchCalls,
  };
  sandbox.globalThis = sandbox;
  sandbox.window.globalThis = sandbox;

  const testCode = `${jsCode}; globalThis.__test_scope = { isConnected: () => isConnected, resetUiToStandby, connectPixelBluetooth };`;
  vm.runInContext(testCode, vm.createContext(sandbox));

  return { sandbox, domElements, defaultDevice, fetchCalls };
}

// 4. Test Suites
let total = 0, passed = 0;
function test(name, fn) {
  total++;
  try {
    fn();
    console.log(`  ✅ [PASS] ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ❌ [FAIL] ${name}: ${e.message}`);
    process.exitCode = 1;
  }
}

async function runAsyncTest(name, fn) {
  total++;
  try {
    await fn();
    console.log(`  ✅ [PASS] ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ❌ [FAIL] ${name}: ${e.message}`);
    process.exitCode = 1;
  }
}

(async () => {
  console.log('\n--- TIER 1: Web Bluetooth GATT Pairing & 8-bit/16-bit HR Ingestion ---');
  
  await runAsyncTest('1.1: Web Bluetooth successfully pairs and unpacks 8-bit HRS packet', async () => {
    const { sandbox, domElements, defaultDevice, fetchCalls } = buildSandbox();
    await sandbox.connectPixelBluetooth();

    assert.strictEqual(domElements['badge-status'].innerText.includes('PIXEL BLE'), true);

    const hrsChar = await defaultDevice.gatt.services['heart_rate'].getCharacteristic('heart_rate_measurement');
    hrsChar.emitValueChanged([0x00, 142]); // 8-bit HR = 142 BPM

    assert.strictEqual(domElements['val-hr'].innerText, 142);
    assert.strictEqual(fetchCalls.length > 0, true);
    assert.strictEqual(fetchCalls[fetchCalls.length - 1].body.heart_rate, 142);
  });

  await runAsyncTest('1.2: Web Bluetooth unpacks 16-bit HRS packet (High BPM / Sprint)', async () => {
    const { sandbox, domElements, defaultDevice, fetchCalls } = buildSandbox();
    await sandbox.connectPixelBluetooth();

    const hrsChar = await defaultDevice.gatt.services['heart_rate'].getCharacteristic('heart_rate_measurement');
    hrsChar.emitValueChanged([0x01, 0xDC, 0x00]); // 16-bit HR = 220 BPM (0x00DC)

    assert.strictEqual(domElements['val-hr'].innerText, 220);
    assert.strictEqual(fetchCalls[fetchCalls.length - 1].body.heart_rate, 220);
  });

  console.log('\n--- TIER 2: GATT Disconnect & Zero-Mock Invariant Reversion ---');

  await runAsyncTest('2.1: Device disconnection immediately triggers zero-mock standby state', async () => {
    const { sandbox, domElements, defaultDevice } = buildSandbox();
    await sandbox.connectPixelBluetooth();

    const hrsChar = await defaultDevice.gatt.services['heart_rate'].getCharacteristic('heart_rate_measurement');
    hrsChar.emitValueChanged([0x00, 150]);
    assert.strictEqual(domElements['val-hr'].innerText, 150);

    // Trigger physical BLE disconnect
    defaultDevice.gatt.disconnect();

    assert.strictEqual(domElements['val-hr'].innerText, '--');
    assert.strictEqual(domElements['val-rmssd'].innerText, '--');
    assert.strictEqual(domElements['badge-status'].innerText, 'STANDBY — DISCONNECTED');
    assert.strictEqual(domElements['badge-status'].style.borderColor, '#EF4444');
  });

  console.log('\n--- TIER 3: Pathological GATT Exceptions & Resilience ---');

  await runAsyncTest('3.1: User cancellation (NotFoundError) resets button state cleanly without throw', async () => {
    const mockCancelledBluetooth = {
      requestDevice: async () => {
        const err = new Error('User cancelled the requestDevice() chooser.');
        err.name = 'NotFoundError';
        throw err;
      },
    };
    const { sandbox, domElements } = buildSandbox(mockCancelledBluetooth);
    await sandbox.connectPixelBluetooth();

    assert.strictEqual(domElements['btn-connect'].innerText, '📲 CONNECT MOVESENSE (BLUETOOTH)');
    assert.strictEqual(domElements['badge-status'].innerText, 'STANDBY — DISCONNECTED');
  });

  console.log(`\n======================================================`);
  console.log(`M3 GATT STRESS HARNESS: ${passed}/${total} tests passed (${Math.round(passed/total*100)}%)`);
  console.log(`======================================================\n`);
})();
