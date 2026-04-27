/**
 * Bluetooth machine connector — real BLE path via react-native-ble-plx.
 *
 * State machine exposed to the UI (truthful, never fake-connected):
 *   bluetooth_unavailable   → module not linked in this native build
 *   permission_required     → module linked but iOS/Android denied
 *   scanning                → BLE scan in progress
 *   device_found            → at least one candidate in range
 *   connected               → GATT connection established
 *   receiving_data          → live FTMS / HR samples streaming
 *   partial_manual_fallback → device connected but its fields are
 *                             limited (e.g. HR only); user logs the
 *                             rest manually
 *   error                   → last action threw; lastError populated
 *
 * Scope of this first native BLE build (build 9):
 *   ✓ Scan for FTMS (0x1826) + HR (0x180D) devices
 *   ✓ Connect / disconnect
 *   ✓ Subscribe to HR measurement characteristic (0x2A37) — live HR
 *     samples flow into callers that subscribe via onHrSample.
 *   △ FTMS Indoor Bike Data (0x2AD2) / Rower (0x2AD1) / Treadmill
 *     (0x2ACD) — parsed minimally (instantaneous power + heart
 *     rate + calories if flagged). More FTMS field decoding lands
 *     in a later iteration.
 *   ✗ Concept2 PM5 proprietary protocol — NOT implemented yet.
 *     PM5 advertises FTMS AND a Concept2 service; we catch its
 *     FTMS half here; richer C2 metrics (pace, strokes, split)
 *     need the proprietary protocol and are a follow-up.
 */

import { Platform, PermissionsAndroid } from 'react-native';

// Lazy loader — react-native-ble-plx resolves on linked builds. On a
// build without the native module it still throws a helpful error
// instead of crashing the whole JS side.
type BleManagerCtor = new () => {
  state(): Promise<string>;
  onStateChange(cb: (state: string) => void, emitCurrent?: boolean): { remove: () => void };
  startDeviceScan(
    uuids: string[] | null,
    options: Record<string, unknown> | null,
    listener: (error: unknown, device: unknown) => void,
  ): void;
  stopDeviceScan(): void;
  connectToDevice(id: string, options?: Record<string, unknown>): Promise<unknown>;
  cancelDeviceConnection(id: string): Promise<unknown>;
};

let _BleManager: BleManagerCtor | null = null;
let _moduleLoadError: string | null = null;

function loadBleManager(): BleManagerCtor | null {
  if (_BleManager) return _BleManager;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('react-native-ble-plx');
    const Ctor = (mod?.BleManager ?? mod?.default?.BleManager) as BleManagerCtor | undefined;
    if (typeof Ctor === 'function') {
      _BleManager = Ctor;
      return _BleManager;
    }
    _moduleLoadError = 'react-native-ble-plx: BleManager export missing';
    return null;
  } catch (e: any) {
    _moduleLoadError = e?.message ?? 'react-native-ble-plx failed to load';
    return null;
  }
}

export type BleMachineStatus =
  | 'bluetooth_unavailable' // native module not linked in this build
  | 'initializing'         // module linked, adapter state not settled yet
  | 'idle'                 // module linked, adapter powered on, waiting for user
  | 'permission_required'
  | 'scanning'
  | 'device_found'
  | 'connected'
  | 'receiving_data'
  | 'partial_manual_fallback'
  | 'error';

export interface DiscoveredDevice {
  id: string;
  name: string;
  kind: 'ftms_bike' | 'ftms_rower' | 'ftms_skierg' | 'pm5' | 'hr_only' | 'whoop_proprietary' | 'unknown';
  rssi: number | null;
}

export interface BleMachineState {
  status: BleMachineStatus;
  // Split device roles so a connected HR strap is NOT forgotten when
  // the user pairs a machine, and vice-versa. `connectedDevice` is
  // retained as a computed "primary" for back-compat with existing
  // rendering (machine wins; falls back to HR).
  connectedDevice: DiscoveredDevice | null;
  hrDevice: DiscoveredDevice | null;
  machineDevice: DiscoveredDevice | null;
  discoveredDevices: DiscoveredDevice[];
  lastError: string | null;
  moduleLinked: boolean;
  // adapterState reflects the OS Bluetooth radio — seeded via
  // onStateChange(cb, true) so the very first render doesn't flash
  // "Unknown" before the underlying state event arrives.
  adapterState: 'Unknown' | 'Resetting' | 'Unsupported' | 'Unauthorized' | 'PoweredOff' | 'PoweredOn';
}

// Well-known UUIDs.
const HR_SERVICE_UUID = '0000180d-0000-1000-8000-00805f9b34fb';
const FTMS_SERVICE_UUID = '00001826-0000-1000-8000-00805f9b34fb';
// Echelon / Rogue Echo BLE — proprietary service used by Echelon
// Connect Sport, EX-series, and (per community reports) Rogue Echo
// Bike V3 firmware. Reverse-engineered by qdomyos-zwift and echbt.
// Data characteristic 0x…f3 carries frame-prefixed workout packets;
// 0x…f4 carries secondary status. 0x…f2 is the write/control char
// used to wake the data stream.
const ECHELON_SERVICE_UUID = '0bf669f1-45f2-11e7-9598-0800200c9a66';
const ECHELON_WRITE_CHAR_UUID = '0bf669f2-45f2-11e7-9598-0800200c9a66';
const ECHELON_DATA_CHAR_UUID = '0bf669f3-45f2-11e7-9598-0800200c9a66';
const ECHELON_STATUS_CHAR_UUID = '0bf669f4-45f2-11e7-9598-0800200c9a66';
// Activation payload: F0 B0 01 01 A2 (checksum A2 = sum of first
// four bytes & 0xFF). Written to the control char on connect to
// kick the workout data stream into notification mode.
// Pre-computed base64 string so module init doesn't touch Buffer
// at the top level — the `buffer` polyfill is not guaranteed to be
// installed before this module loads during app startup. Touching
// Buffer here crashed the launch bundle.
const ECHELON_ACTIVATE_PAYLOAD_B64 = '8LABAaI=';
const PM5_PRIMARY_SERVICE_UUID = 'ce060000-43e5-11e4-916c-0800200c9a66';

// Eagerly probe at module-import so the initial _state.status reflects
// whether the native module is linked, before any component reads it.
// Prevents a race where the first render of TrainMachineSection /
// FTMSMachineCard sees `bluetooth_unavailable` for a build where the
// module IS actually linked, simply because nothing has called
// loadBleManager() yet. The status will flip to 'idle' for Build 9+.
const _initialModuleLinked: boolean = (() => {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('react-native-ble-plx');
    const Ctor = (mod?.BleManager ?? mod?.default?.BleManager);
    if (typeof Ctor === 'function') {
      _BleManager = Ctor as BleManagerCtor;
      return true;
    }
    _moduleLoadError = 'react-native-ble-plx: BleManager export missing';
    return false;
  } catch (e: any) {
    _moduleLoadError = e?.message ?? 'react-native-ble-plx failed to load';
    return false;
  }
})();

let _state: BleMachineState = {
  // Start in 'initializing' when the module IS linked — the adapter
  // state subscription hasn't fired yet, so we shouldn't claim 'idle'
  // (which the UI treats as "ready to scan"). The moment onStateChange
  // reports PoweredOn, this flips to 'idle' so the first scan never
  // has to race the adapter probe. Eliminates the "adapter state:
  // Unknown" first-tap message entirely.
  status: _initialModuleLinked ? 'initializing' : 'bluetooth_unavailable',
  connectedDevice: null,
  hrDevice: null,
  machineDevice: null,
  discoveredDevices: [],
  lastError: null,
  moduleLinked: _initialModuleLinked,
  adapterState: 'Unknown',
};
let _manager: InstanceType<BleManagerCtor> | null = null;
// Eagerly build the manager + adapter-state subscription at module
// import so iOS has already resolved PoweredOn by the time the user
// taps Scan. Lazy construction (only inside scanBleMachines) was the
// root cause of "adapter state: Unknown" on the first tap — the
// onStateChange callback hadn't fired yet because the manager didn't
// exist. Calling buildManager here is synchronous and cheap; the
// actual state probe is async and handled by the subscription.
// Guard the require in a function so it runs lazily the first time
// any component mounts, avoiding import-order issues.
let _hrConnectedRef: any = null;       // HR-only device (e.g. Polar H10)
let _machineConnectedRef: any = null;  // FTMS bike/rower/skierg or PM5
let _scanTimer: ReturnType<typeof setTimeout> | null = null;
let _stateSubscription: { remove: () => void } | null = null;

function buildManager(): InstanceType<BleManagerCtor> | null {
  if (_manager) return _manager;
  const Ctor = loadBleManager();
  if (!Ctor) return null;
  try {
    _manager = new Ctor();
    _state = { ..._state, moduleLinked: true };
    // Seed adapterState ASAP via onStateChange(cb, emitCurrent=true).
    // Without this, the first call to manager.state() returns 'Unknown'
    // because the OS hasn't yet pushed the initial state event. The
    // callback fires synchronously on subscribe with emitCurrent=true,
    // then again on every transition (PoweredOff → PoweredOn etc.).
    try {
      _stateSubscription?.remove();
      _stateSubscription = _manager.onStateChange((adapterState: string) => {
        const normalized = (['Unknown', 'Resetting', 'Unsupported', 'Unauthorized', 'PoweredOff', 'PoweredOn']
          .includes(adapterState) ? adapterState : 'Unknown') as BleMachineState['adapterState'];
        // Promote status out of 'initializing' the moment the adapter
        // reports a definitive state. Without this, 'initializing'
        // could stick forever if the user never taps Scan.
        let nextStatus = _state.status;
        if (_state.status === 'initializing' || _state.status === 'bluetooth_unavailable') {
          if (normalized === 'PoweredOn') nextStatus = 'idle';
          else if (normalized === 'Unauthorized') nextStatus = 'permission_required';
          else if (normalized === 'PoweredOff' || normalized === 'Unsupported') nextStatus = 'bluetooth_unavailable';
        }
        _state = { ..._state, adapterState: normalized, status: nextStatus };
      }, true);
    } catch { /* non-fatal — first scan will still probe manager.state() */ }
    return _manager;
  } catch (e: any) {
    _moduleLoadError = e?.message ?? 'BleManager construction failed';
    return null;
  }
}

// Kick off manager construction at module import so the adapter-state
// subscription is alive before the user ever taps Scan. Skip silently
// if the native module isn't linked (older builds) — the state
// machine still handles that case correctly.
if (_initialModuleLinked) {
  try { buildManager(); } catch { /* non-fatal — scan will retry */ }
}

/** Classify a scanned device by its advertised service UUIDs + name. */
function classifyDevice(rawName: string | null, serviceUUIDs: string[] | null): DiscoveredDevice['kind'] {
  const name = (rawName ?? '').toLowerCase();
  const uuids = (serviceUUIDs ?? []).map((u) => u.toLowerCase());
  // WHOOP straps advertise their own proprietary service UUID and do
  // NOT expose the standard Heart Rate Service (0x180D). Detecting
  // them by name lets Train rank them last and label them honestly
  // so they never hijack the live capture path.
  if (name.includes('whoop')) return 'whoop_proprietary';
  if (uuids.includes(PM5_PRIMARY_SERVICE_UUID) || name.includes('pm5')) return 'pm5';
  // Echelon / Rogue Echo proprietary BLE — classify as an ftms_bike
  // so the rank-sort surfaces it near standard FTMS bikes. The
  // connect path will prefer the Echelon decoder when the 0x0bf6…f1
  // service is present.
  if (uuids.includes(ECHELON_SERVICE_UUID) || /echelon|rogue.*echo|echo.?bike/i.test(name)) return 'ftms_bike';
  if (uuids.includes(FTMS_SERVICE_UUID)) {
    if (name.includes('bike') || name.includes('echo') || name.includes('assault')) return 'ftms_bike';
    if (name.includes('row')) return 'ftms_rower';
    if (name.includes('ski')) return 'ftms_skierg';
    return 'ftms_bike';
  }
  if (uuids.includes(HR_SERVICE_UUID)) return 'hr_only';
  return 'unknown';
}

/**
 * Rank order for surfacing discovered devices in Train. Lower number
 * = more preferred as a live-capture source. WHOOP is explicitly last
 * because its proprietary profile cannot stream live HR to us.
 */
export function deviceRank(d: DiscoveredDevice): number {
  switch (d.kind) {
    case 'ftms_bike': return 0;
    case 'ftms_rower': return 1;
    case 'ftms_skierg': return 2;
    case 'pm5': return 3;
    case 'hr_only': return 4;
    case 'unknown': return 5;
    case 'whoop_proprietary': return 9;
    default: return 9;
  }
}

async function requestAndroidPermissions(): Promise<boolean> {
  if (Platform.OS !== 'android') return true;
  try {
    const granted = await PermissionsAndroid.requestMultiple([
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
      PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
      PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
    ]);
    return Object.values(granted).every((v) => v === 'granted');
  } catch {
    return false;
  }
}

export function getBleMachineState(): BleMachineState {
  const mod = loadBleManager();
  const linked = mod != null;
  // Decouple status from "module not linked" once the module IS
  // linked. Previously status started as 'bluetooth_unavailable' and
  // stayed that way until buildManager() ran — which meant Build 9
  // (which DOES have the native module linked) still flashed the
  // "BLE module not linked in this build" copy until the user tapped
  // Scan. Fix: flip to 'idle' whenever we have a module but haven't
  // moved past the default status yet.
  let effectiveStatus: BleMachineStatus = _state.status;
  if (!linked) {
    effectiveStatus = 'bluetooth_unavailable';
  } else if (_state.status === 'bluetooth_unavailable') {
    effectiveStatus = 'initializing';
  } else if (_state.status === 'initializing' && _state.adapterState === 'PoweredOn') {
    // Adapter came up after the initial state render. Flip to 'idle'
    // so the UI shows "Ready to scan" immediately.
    effectiveStatus = 'idle';
  }
  return {
    ..._state,
    status: effectiveStatus,
    moduleLinked: linked,
    lastError: _state.lastError ?? _moduleLoadError,
  };
}

export async function scanBleMachines(timeoutMs = 10_000): Promise<void> {
  const manager = buildManager();
  if (!manager) {
    _state = {
      ..._state,
      status: 'bluetooth_unavailable',
      lastError: _moduleLoadError ?? 'react-native-ble-plx not available',
    };
    return;
  }

  // Android needs runtime permissions; iOS picks up via Info.plist.
  if (Platform.OS === 'android') {
    const ok = await requestAndroidPermissions();
    if (!ok) {
      _state = { ..._state, status: 'permission_required', lastError: 'Bluetooth / location permissions not granted' };
      return;
    }
  }

  // Wait up to 2s for the adapter to settle. The onStateChange
  // subscription (set up in buildManager) caches transitions into
  // _state.adapterState — so we prefer that cached value. If it's
  // still 'Unknown' after the grace window, probe manager.state()
  // directly as a last resort. This eliminates the "adapter state:
  // Unknown" flash users used to see on the very first scan.
  let bleState: string = _state.adapterState;
  const deadline = Date.now() + 2000;
  while (bleState === 'Unknown' && Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 100));
    bleState = _state.adapterState;
  }
  if (bleState === 'Unknown') {
    try {
      bleState = await manager.state();
    } catch (e: any) {
      _state = { ..._state, status: 'error', lastError: e?.message ?? 'manager.state() threw' };
      return;
    }
  }
  if (bleState !== 'PoweredOn') {
    // Never surface a raw adapter state string like "Unknown" to the
    // user — it's CoreBluetooth internal jargon, not actionable. Map
    // every non-PoweredOn state to a plain-English sentence.
    const friendly =
      bleState === 'PoweredOff' ? 'Bluetooth is off. Turn it on in Settings and tap Scan again.'
      : bleState === 'Unauthorized' ? 'Bluetooth permission denied for Lauburu. Enable it in Settings → Lauburu.'
      : bleState === 'Unsupported' ? 'This device doesn\u2019t support Bluetooth Low Energy.'
      : 'Bluetooth is still initialising. Wait a second and tap Scan again.';
    _state = {
      ..._state,
      status: bleState === 'Unauthorized' ? 'permission_required'
        : bleState === 'Unsupported' ? 'bluetooth_unavailable'
        : 'initializing',
      lastError: friendly,
    };
    return;
  }

  _state = { ..._state, status: 'scanning', lastError: null, discoveredDevices: [] };

  const discovered = new Map<string, DiscoveredDevice>();
  try {
    manager.startDeviceScan(
      [HR_SERVICE_UUID, FTMS_SERVICE_UUID, PM5_PRIMARY_SERVICE_UUID, ECHELON_SERVICE_UUID],
      { allowDuplicates: false },
      (error: unknown, device: unknown) => {
        if (error || !device) return;
        const d = device as any;
        const id = d?.id as string | undefined;
        if (!id) return;
        const name = (d?.name ?? d?.localName ?? id) as string;
        const serviceUUIDs = (d?.serviceUUIDs ?? []) as string[];
        const kind = classifyDevice(name, serviceUUIDs);
        discovered.set(id, {
          id,
          name,
          kind,
          rssi: typeof d?.rssi === 'number' ? d.rssi : null,
        });
        _state = {
          ..._state,
          status: 'device_found',
          discoveredDevices: Array.from(discovered.values()),
        };
      },
    );
  } catch (e: any) {
    _state = { ..._state, status: 'error', lastError: e?.message ?? 'startDeviceScan threw' };
    return;
  }

  // Auto-stop scan after timeoutMs.
  if (_scanTimer) clearTimeout(_scanTimer);
  await new Promise<void>((resolve) => {
    _scanTimer = setTimeout(() => {
      try { manager.stopDeviceScan(); } catch { /* ignore */ }
      if (discovered.size === 0) {
        // Distinguish genuinely-empty scan from permission issues. The
        // previous code lumped both as 'permission_required' which
        // misled users with permissions granted but no nearby device.
        _state = { ..._state, status: 'error', lastError: 'No HR straps or FTMS machines found in range. Wake the device (pedal the bike / tap the strap) and tap Scan again.' };
      }
      resolve();
    }, timeoutMs);
  });
}

export async function connectBleMachine(deviceId: string): Promise<void> {
  const manager = buildManager();
  if (!manager) {
    _state = { ..._state, status: 'bluetooth_unavailable', lastError: _moduleLoadError ?? 'BLE module unavailable' };
    return;
  }
  // BLE spec: the radio cannot connect while a scan is active. iOS
  // silently fails connect attempts if startDeviceScan is still
  // running. Always stop scanning before attempting a connect.
  try {
    if (_scanTimer) { clearTimeout(_scanTimer); _scanTimer = null; }
    if (typeof (manager as any).stopDeviceScan === 'function') {
      await (manager as any).stopDeviceScan();
    }
  } catch { /* ignore — stop is best-effort */ }
  const existing = _state.discoveredDevices.find((d) => d.id === deviceId) ?? null;
  // Determine role from the device kind so HR straps and FTMS machines
  // occupy independent slots. Both can be connected simultaneously:
  // the live-stream path subscribes to whichever device(s) are bound.
  const role: 'hr' | 'machine' = (() => {
    if (!existing) return 'machine';
    if (existing.kind === 'hr_only') return 'hr';
    if (existing.kind === 'ftms_bike' || existing.kind === 'ftms_rower' || existing.kind === 'ftms_skierg' || existing.kind === 'pm5') return 'machine';
    return 'machine';
  })();
  // Surface a connecting state immediately so the UI shows progress
  // and so repeated taps can't fire overlapping connect attempts.
  _state = {
    ..._state,
    status: 'scanning', // "scanning" already reads as "in progress" to the UI pill
    connectedDevice: existing, // remembered for header label during the attempt
    lastError: null,
  };
  try {
    const device = await manager.connectToDevice(deviceId, { timeout: 15_000, autoConnect: false } as any) as any;
    // Some peripherals require a short settle before service discovery
    // returns a populated list. 300ms is imperceptible to the user.
    await new Promise((r) => setTimeout(r, 300));
    if (typeof device?.discoverAllServicesAndCharacteristics === 'function') {
      try {
        await device.discoverAllServicesAndCharacteristics();
      } catch (e: any) {
        // Service discovery can fail while the physical link is up.
        // Persist the connection reference so later retries can work
        // but surface the specific reason.
        _state = { ..._state, status: 'error', lastError: `Service discovery failed: ${e?.message ?? 'unknown'}. Try again.` };
        if (role === 'hr') _hrConnectedRef = device; else _machineConnectedRef = device;
        return;
      }
    }
    if (role === 'hr') _hrConnectedRef = device; else _machineConnectedRef = device;
    // Record which services the device actually advertises so we can
    // warn users when they've connected to a device (like WHOOP) that
    // does NOT expose the standard Heart Rate Service. WHOOP uses a
    // proprietary profile and we cannot read HR from it via BLE.
    _lastConnectedServices = [];
    _lastConnectedFtmsNotifyChars = [];
    _lastConnectedVendorNotifyChars = [];
    _vendorFrames.length = 0;
    try {
      if (typeof device?.services === 'function') {
        const svcs = await device.services();
        if (Array.isArray(svcs)) {
          _lastConnectedServices = svcs.map((s: any) => String(s?.uuid ?? '').toLowerCase()).filter(Boolean);
          // Walk every service. FTMS notify chars go to the FTMS list
          // (parsed as Indoor Bike / Cross Trainer / Rower / Treadmill
          // data). Every other notify-capable char goes to the vendor
          // list — we subscribe to them too but only log raw frames,
          // never invent metrics. That captures proprietary streams
          // (e.g. Rogue Echo V3's vendor service) for future decode.
          for (const svc of svcs) {
            const svcUuid = String(svc?.uuid ?? '').toLowerCase();
            if (!svcUuid || typeof svc.characteristics !== 'function') continue;
            try {
              const chars = await svc.characteristics();
              if (!Array.isArray(chars)) continue;
              for (const c of chars) {
                const charUuid = String(c?.uuid ?? '').toLowerCase();
                if (!charUuid) continue;
                const isNotify = !!(c?.isNotifiable || c?.isIndicatable);
                if (!isNotify) continue;
                if (svcUuid === FTMS_SERVICE_UUID) {
                  _lastConnectedFtmsNotifyChars.push(charUuid);
                } else if (svcUuid !== HR_SERVICE_UUID) {
                  // Skip HR — already handled by the standard HR path.
                  // Everything else is vendor/proprietary and gets
                  // logged + subscribed for debug capture.
                  _lastConnectedVendorNotifyChars.push({ serviceUuid: svcUuid, charUuid });
                }
              }
            } catch { /* non-fatal — char enumeration */ }
          }
        }
      }
    } catch { /* non-fatal — services list is diagnostic only */ }
    const resolvedDevice = existing ?? { id: deviceId, name: device?.name ?? deviceId, kind: 'unknown' as const, rssi: null };
    const nextHrDevice = role === 'hr' ? resolvedDevice : _state.hrDevice;
    const nextMachineDevice = role === 'machine' ? resolvedDevice : _state.machineDevice;
    _state = {
      ..._state,
      status: 'connected',
      // `connectedDevice` stays a computed primary (machine wins over
      // HR) so existing UI strings keep working without a refactor.
      connectedDevice: nextMachineDevice ?? nextHrDevice ?? resolvedDevice,
      hrDevice: nextHrDevice,
      machineDevice: nextMachineDevice,
      lastError: null,
    };
    // Auto-start live subscription + FTMS wake sequence immediately on
    // successful connect. Previously the Rogue Echo would connect but
    // stay silent because startBleSession was only fired when the user
    // tapped "Start live read". From a UX perspective, tapping Connect
    // means "I want live data"; the wake sequence is harmless on
    // devices that don't need it. Fire-and-forget; if it throws the
    // user can still tap Start live read manually from the card.
    try {
      const _maybeHandle = startBleSession();
      if (_maybeHandle && _maybeHandle.live) {
        markSessionStart();
      }
    } catch { /* non-fatal */ }
  } catch (e: any) {
    // Classify the most common failure modes so the UI message is
    // actionable rather than a raw native error string.
    const raw = String(e?.message ?? '');
    let friendly = raw || 'Connect failed';
    if (/cancell?ed/i.test(raw)) friendly = 'Connect cancelled. Wake the device (pedal once) and tap Connect again.';
    else if (/timeout/i.test(raw) || /timed out/i.test(raw)) friendly = 'Connect timed out. Move the phone closer, wake the device, try again.';
    else if (/disconnected/i.test(raw) || /not connected/i.test(raw)) friendly = 'Device dropped before handshake. Tap Connect again.';
    else if (/not found|no peripheral/i.test(raw)) friendly = 'Device not in range. Re-scan and try again.';
    _state = { ..._state, status: 'error', lastError: friendly };
  }
}

export function disconnectBleMachine(role?: 'hr' | 'machine' | 'all'): void {
  const manager = _manager;
  const scope: 'hr' | 'machine' | 'all' = role ?? 'all';
  const targets: Array<{ id: string | undefined; kind: 'hr' | 'machine' }> = [];
  if (scope === 'all' || scope === 'machine') targets.push({ id: _state.machineDevice?.id, kind: 'machine' });
  if (scope === 'all' || scope === 'hr') targets.push({ id: _state.hrDevice?.id, kind: 'hr' });
  if (manager) {
    for (const t of targets) {
      if (t.id) manager.cancelDeviceConnection(t.id).catch(() => { /* ignore */ });
    }
  }
  if (scope === 'all' || scope === 'hr') _hrConnectedRef = null;
  if (scope === 'all' || scope === 'machine') _machineConnectedRef = null;
  const nextHr = scope === 'all' || scope === 'hr' ? null : _state.hrDevice;
  const nextMachine = scope === 'all' || scope === 'machine' ? null : _state.machineDevice;
  // If any slot is still bound, stay in 'connected' — the other stream
  // continues. Only drop to idle when both slots are empty.
  const anyStillBound = !!(nextHr || nextMachine);
  _state = {
    ..._state,
    status: anyStillBound ? 'connected' : (_state.moduleLinked ? 'idle' : 'bluetooth_unavailable'),
    hrDevice: nextHr,
    machineDevice: nextMachine,
    connectedDevice: nextMachine ?? nextHr ?? null,
  };
}

/**
 * Start a live session. Subscribes to HR Measurement (0x2A37). If the
 * connected device is FTMS, also subscribes to its Indoor Bike Data /
 * Rower Data / Treadmill Data characteristic and emits a minimal
 * parsed payload on each frame.
 *
 * Returns a handle with `.stop()` + `.onHr` + `.onFtms` callback
 * setters. Caller pushes samples into the HIIT workout per-set buffer.
 */
export interface LiveBleSessionHandle {
  stop: () => void;
  live: boolean;
  onHr: (cb: ((bpm: number, atEpochMs: number) => void) | null) => void;
  onFtms: (cb: ((sample: FtmsLiveSample) => void) | null) => void;
}

export interface FtmsLiveSample {
  atEpochMs: number;
  instantaneousPowerW: number | null;
  heartRateBpm: number | null;
  energyKj: number | null;
  instantaneousCadenceRpm: number | null;
  instantaneousSpeedKph: number | null;
  totalDistanceM: number | null;
  resistanceLevel: number | null;
  elapsedTimeS: number | null;
}

// Shared ring of recent samples. Any caller can subscribe to the
// stream while another caller (e.g. the FTMS card) owns the actual
// BLE session. Keeps the Train tab independent from the Health tab's
// lifecycle without requiring a second characteristic subscription.
type HrListener = (bpm: number, atEpochMs: number) => void;
type FtmsListener = (sample: FtmsLiveSample) => void;
const _hrListeners = new Set<HrListener>();
const _ftmsListeners = new Set<FtmsListener>();
let _lastHrBpm: number | null = null;
let _lastHrAtMs: number | null = null;
let _lastFtms: FtmsLiveSample | null = null;

// Session ring buffer — captures HR + power samples over the active
// session so the Train save path can auto-fill avgHr/peakHr/avgWatts
// even if the user never sees the Machine card live chip. Capped so
// a long session doesn't blow up JS heap (5000 samples × ~40 bytes
// ≈ 200KB worst-case).
const MAX_SESSION_SAMPLES = 5000;
interface SessionSample {
  atEpochMs: number;
  hrBpm: number | null;
  powerW: number | null;
  cadenceRpm: number | null;
  distanceM: number | null;
  energyKj: number | null;
}
const _sessionSamples: SessionSample[] = [];
let _sessionStartAtMs: number | null = null;

// Live-stream health: tracks whether samples are actually arriving
// from the connected device after subscriptions started. A WHOOP
// strap in particular connects successfully but does NOT advertise
// the standard Heart Rate Service (0x180D / 0x2A37) — it uses a
// proprietary profile. Our subscription silently never fires, so
// we need to report "connected but no data" explicitly.
let _liveStartedAtMs: number | null = null;
let _liveLastSampleAtMs: number | null = null;
let _lastConnectedServices: string[] = [];
let _lastConnectedFtmsNotifyChars: string[] = [];
// Characteristics outside FTMS/HR that we've discovered on the
// connected device (vendor-specific or unknown). Surface via
// getLiveStreamStatus so the Train card can render a debug log.
let _lastConnectedVendorNotifyChars: Array<{ serviceUuid: string; charUuid: string }> = [];
// Rolling ring of the N most-recent raw vendor frames we've captured
// (as hex). Never interpreted as metrics — used only to feed the
// debug pane so future integration can reverse-engineer the layout.
type VendorFrame = { atEpochMs: number; serviceUuid: string; charUuid: string; hex: string; byteLen: number };
const MAX_VENDOR_FRAMES = 40;
const _vendorFrames: VendorFrame[] = [];

export function getLiveStreamStatus(): {
  started: boolean;
  startedAtMs: number | null;
  secondsSinceStart: number | null;
  secondsSinceLastSample: number | null;
  hasEverReceivedSample: boolean;
  servicesOnDevice: string[];
  ftmsCharsOnDevice: string[];
  vendorCharsOnDevice: Array<{ serviceUuid: string; charUuid: string }>;
  vendorFrames: VendorFrame[];
  hasFtmsService: boolean;
  hasHrService: boolean;
} {
  const started = _liveStartedAtMs != null;
  const now = Date.now();
  return {
    started,
    startedAtMs: _liveStartedAtMs,
    secondsSinceStart: _liveStartedAtMs != null ? (now - _liveStartedAtMs) / 1000 : null,
    secondsSinceLastSample: _liveLastSampleAtMs != null ? (now - _liveLastSampleAtMs) / 1000 : null,
    hasEverReceivedSample: _liveLastSampleAtMs != null,
    servicesOnDevice: _lastConnectedServices,
    ftmsCharsOnDevice: _lastConnectedFtmsNotifyChars,
    vendorCharsOnDevice: _lastConnectedVendorNotifyChars,
    vendorFrames: _vendorFrames.slice(),
    hasFtmsService: _lastConnectedServices.includes(FTMS_SERVICE_UUID),
    hasHrService: _lastConnectedServices.includes(HR_SERVICE_UUID),
  };
}

function pushSessionSample(sample: SessionSample): void {
  _sessionSamples.push(sample);
  if (_sessionSamples.length > MAX_SESSION_SAMPLES) {
    _sessionSamples.splice(0, _sessionSamples.length - MAX_SESSION_SAMPLES);
  }
}

export function markSessionStart(atEpochMs: number = Date.now()): void {
  _sessionStartAtMs = atEpochMs;
  _sessionSamples.length = 0;
}

export function clearSession(): void {
  _sessionStartAtMs = null;
  _sessionSamples.length = 0;
}

export interface SessionStats {
  sampleCount: number;
  sinceEpochMs: number | null;
  avgHrBpm: number | null;
  peakHrBpm: number | null;
  avgPowerW: number | null;
  peakPowerW: number | null;
  avgCadenceRpm: number | null;
  totalDistanceM: number | null;
  totalEnergyKj: number | null;
  totalEnergyKcal: number | null;
}

export function getSessionStats(sinceEpochMs?: number): SessionStats {
  const cutoff = sinceEpochMs ?? _sessionStartAtMs ?? null;
  const relevant = cutoff != null
    ? _sessionSamples.filter((s) => s.atEpochMs >= cutoff)
    : [..._sessionSamples];
  const hrs = relevant.map((s) => s.hrBpm).filter((v): v is number => typeof v === 'number' && v > 0);
  const powers = relevant.map((s) => s.powerW).filter((v): v is number => typeof v === 'number' && v > 0);
  const cadences = relevant.map((s) => s.cadenceRpm).filter((v): v is number => typeof v === 'number' && v > 0);
  // Distance + energy are monotonic counters from the machine, so the
  // session total is the LAST non-null sample minus the FIRST non-null
  // sample (which is typically 0 for distance or a start-marker for
  // energy). Falls back to last-value when first-value isn't 0.
  const distances = relevant.map((s) => s.distanceM).filter((v): v is number => typeof v === 'number' && v >= 0);
  const energies = relevant.map((s) => s.energyKj).filter((v): v is number => typeof v === 'number' && v >= 0);
  const distanceTotal = distances.length > 0
    ? Math.max(0, distances[distances.length - 1] - distances[0])
    : null;
  const energyKjTotal = energies.length > 0
    ? Math.max(0, energies[energies.length - 1] - energies[0])
    : null;
  // FTMS spec reports Expended Energy in kJ. Convert to kcal (1 kcal
  // ≈ 4.184 kJ). Round to integer for a reasonable display.
  const energyKcalTotal = energyKjTotal != null ? Math.round(energyKjTotal / 4.184) : null;
  return {
    sampleCount: relevant.length,
    sinceEpochMs: cutoff,
    avgHrBpm: hrs.length > 0 ? Math.round(hrs.reduce((a, b) => a + b, 0) / hrs.length) : null,
    peakHrBpm: hrs.length > 0 ? Math.max(...hrs) : null,
    avgPowerW: powers.length > 0 ? Math.round(powers.reduce((a, b) => a + b, 0) / powers.length) : null,
    peakPowerW: powers.length > 0 ? Math.max(...powers) : null,
    avgCadenceRpm: cadences.length > 0 ? Math.round(cadences.reduce((a, b) => a + b, 0) / cadences.length) : null,
    totalDistanceM: distanceTotal,
    totalEnergyKj: energyKjTotal,
    totalEnergyKcal: energyKcalTotal,
  };
}

export function subscribeHr(cb: HrListener): () => void {
  _hrListeners.add(cb);
  return () => { _hrListeners.delete(cb); };
}
export function subscribeFtms(cb: FtmsListener): () => void {
  _ftmsListeners.add(cb);
  return () => { _ftmsListeners.delete(cb); };
}
export function getLastLiveSample(): { bpm: number | null; bpmAtMs: number | null; ftms: FtmsLiveSample | null } {
  return { bpm: _lastHrBpm, bpmAtMs: _lastHrAtMs, ftms: _lastFtms };
}

export function startBleSession(): LiveBleSessionHandle {
  // HR subscription runs on the HR-role device when present, else
  // falls back to the machine device (some FTMS bikes publish HR via
  // the heart-rate service embedded in the same GATT server).
  const machineDev = _machineConnectedRef;
  const hrDev = _hrConnectedRef ?? _machineConnectedRef;
  const anyDevice = machineDev ?? hrDev;
  if (!anyDevice || typeof anyDevice.monitorCharacteristicForService !== 'function') {
    return {
      stop: () => {},
      live: false,
      onHr: () => {},
      onFtms: () => {},
    };
  }
  // Stamp so the UI can report "no samples after N seconds" when the
  // device doesn't advertise the standard HR or FTMS profiles (WHOOP,
  // most notably — it uses a proprietary BLE profile we can't read).
  _liveStartedAtMs = Date.now();
  _liveLastSampleAtMs = null;
  let hrCb: ((bpm: number, atEpochMs: number) => void) | null = null;
  let ftmsCb: ((s: FtmsLiveSample) => void) | null = null;
  const subs: Array<{ remove?: () => void } | null> = [];

  // HR Measurement characteristic (0x2A37) under Heart Rate Service.
  // Prefer the dedicated HR-role device (e.g. Polar H10); fall back to
  // the machine device if its GATT server also exposes 0x180D.
  try {
    const s = (hrDev ?? machineDev).monitorCharacteristicForService(
      HR_SERVICE_UUID,
      '00002a37-0000-1000-8000-00805f9b34fb',
      (error: unknown, char: any) => {
        if (error || !char?.value) return;
        try {
          const bytes = Buffer.from(String(char.value), 'base64');
          if (bytes.length < 2) return;
          const flags = bytes[0];
          const hrIs16 = (flags & 0x01) === 0x01;
          const bpm = hrIs16 ? bytes.readUInt16LE(1) : bytes[1];
          if (typeof bpm === 'number') {
            const at = Date.now();
            _lastHrBpm = bpm;
            _lastHrAtMs = at;
            _liveLastSampleAtMs = at;
            if (_sessionStartAtMs != null) pushSessionSample({ atEpochMs: at, hrBpm: bpm, powerW: null, cadenceRpm: null, distanceM: null, energyKj: null });
            if (hrCb) hrCb(bpm, at);
            for (const listener of _hrListeners) { try { listener(bpm, at); } catch { /* ignore listener errors */ } }
          }
        } catch { /* ignore bad frame */ }
      },
    );
    subs.push(s ?? null);
  } catch { /* no HR service on this device */ }

  // FTMS data-characteristic subscriptions. The spec reserves
  // 0x2AD2 Indoor Bike Data, 0x2ACE Cross Trainer Data, 0x2AD1 Rower
  // Data, 0x2ACD Treadmill Data. Some Rogue Echo / Assault firmware
  // publishes bike data on 0x2ACE (Cross Trainer) despite the device
  // being a bike, so we subscribe to every notify-capable FTMS data
  // char we discovered plus a hard-coded fallback list. The parser
  // below is flag-based and safely drops malformed frames, so non-
  // bike frames cost nothing if they arrive.
  const ftmsCandidates = new Set<string>([
    '00002ad2-0000-1000-8000-00805f9b34fb', // Indoor Bike Data
    '00002ace-0000-1000-8000-00805f9b34fb', // Cross Trainer Data
    '00002ad1-0000-1000-8000-00805f9b34fb', // Rower Data
    '00002acd-0000-1000-8000-00805f9b34fb', // Treadmill Data
    ...(_lastConnectedFtmsNotifyChars ?? []),
  ]);
  // Skip the Control-Point UUID; it's not a data char.
  ftmsCandidates.delete('00002ad9-0000-1000-8000-00805f9b34fb');
  const ftmsFrameHandler = (error: unknown, char: any) => {
        if (error || !char?.value) return;
        try {
          const bytes = Buffer.from(String(char.value), 'base64');
          if (bytes.length < 2) return;
          const flags = bytes[0] | (bytes[1] << 8);
          let offset = 2;
          // FTMS Indoor Bike Data flag meanings per the spec:
          //   bit 0 (0x0001) = More Data (if SET, Instantaneous Speed is NOT present; if CLEAR, it IS present)
          //   bit 1 (0x0002) = Average Speed present
          //   bit 2 (0x0004) = Instantaneous Cadence present
          //   bit 3 (0x0008) = Average Cadence present
          //   bit 4 (0x0010) = Total Distance present (3 bytes)
          //   bit 5 (0x0020) = Resistance Level present
          //   bit 6 (0x0040) = Instantaneous Power present
          //   bit 7 (0x0080) = Average Power present
          //   bit 8 (0x0100) = Expended Energy present (5 bytes: total u16 + per-hr u16 + per-min u8)
          //   bit 9 (0x0200) = Heart Rate present (1 byte)
          //   bit 10 (0x0400) = Metabolic Equivalent present
          //   bit 11 (0x0800) = Elapsed Time present (2 bytes)
          //   bit 12 (0x1000) = Remaining Time present
          let instantSpeedKph: number | null = null;
          if ((flags & 0x0001) === 0 && bytes.length >= offset + 2) {
            // uint16 in 0.01 km/h
            instantSpeedKph = bytes.readUInt16LE(offset) / 100;
            offset += 2;
          }
          if ((flags & 0x0002) === 0x0002) offset += 2; // Average Speed
          let instantCadenceRpm: number | null = null;
          if ((flags & 0x0004) === 0x0004 && bytes.length >= offset + 2) {
            // uint16 in 0.5 rpm
            instantCadenceRpm = bytes.readUInt16LE(offset) / 2;
            offset += 2;
          }
          if ((flags & 0x0008) === 0x0008) offset += 2; // Average Cadence
          let totalDistanceM: number | null = null;
          if ((flags & 0x0010) === 0x0010 && bytes.length >= offset + 3) {
            // uint24 in meters
            totalDistanceM = bytes[offset] | (bytes[offset + 1] << 8) | (bytes[offset + 2] << 16);
            offset += 3;
          }
          let resistanceLevel: number | null = null;
          if ((flags & 0x0020) === 0x0020 && bytes.length >= offset + 2) {
            resistanceLevel = bytes.readInt16LE(offset);
            offset += 2;
          }
          let instantPower: number | null = null;
          if ((flags & 0x0040) === 0x0040 && bytes.length >= offset + 2) {
            instantPower = bytes.readInt16LE(offset);
            offset += 2;
          }
          if ((flags & 0x0080) === 0x0080) offset += 2; // Average Power
          let energyKj: number | null = null;
          if ((flags & 0x0100) === 0x0100 && bytes.length >= offset + 5) {
            energyKj = bytes.readUInt16LE(offset);
            offset += 5;
          }
          let hr: number | null = null;
          if ((flags & 0x0200) === 0x0200 && bytes.length >= offset + 1) {
            hr = bytes[offset];
            offset += 1;
          }
          if ((flags & 0x0400) === 0x0400) offset += 1; // Metabolic Equivalent (uint8)
          let elapsedTimeS: number | null = null;
          if ((flags & 0x0800) === 0x0800 && bytes.length >= offset + 2) {
            elapsedTimeS = bytes.readUInt16LE(offset);
            offset += 2;
          }
          const sample: FtmsLiveSample = {
            atEpochMs: Date.now(),
            instantaneousPowerW: instantPower,
            heartRateBpm: hr,
            energyKj,
            instantaneousCadenceRpm: instantCadenceRpm,
            instantaneousSpeedKph: instantSpeedKph,
            totalDistanceM,
            resistanceLevel,
            elapsedTimeS,
          };
          _lastFtms = sample;
          _liveLastSampleAtMs = sample.atEpochMs;
          if (typeof hr === 'number') { _lastHrBpm = hr; _lastHrAtMs = sample.atEpochMs; }
          if (_sessionStartAtMs != null) pushSessionSample({
            atEpochMs: sample.atEpochMs,
            hrBpm: typeof hr === 'number' ? hr : null,
            powerW: typeof instantPower === 'number' ? instantPower : null,
            cadenceRpm: typeof instantCadenceRpm === 'number' ? instantCadenceRpm : null,
            distanceM: typeof totalDistanceM === 'number' ? totalDistanceM : null,
            energyKj: typeof energyKj === 'number' ? energyKj : null,
          });
          if (ftmsCb) ftmsCb(sample);
          for (const listener of _ftmsListeners) { try { listener(sample); } catch { /* ignore */ } }
          _state = { ..._state, status: 'receiving_data' };
        } catch { /* ignore */ }
      };
  // Subscribe to every candidate FTMS data characteristic. Each
  // subscription is independent; a failure on one UUID must not
  // prevent the others from streaming.
  if (machineDev) {
    for (const uuid of ftmsCandidates) {
      try {
        const s = machineDev.monitorCharacteristicForService(
          FTMS_SERVICE_UUID,
          uuid,
          ftmsFrameHandler,
        );
        subs.push(s ?? null);
      } catch { /* characteristic not present on this device */ }
    }
    // Vendor/proprietary notify chars — subscribe with a debug
    // handler that logs raw frames but NEVER invents metrics. Lets
    // us capture Rogue Echo V3 vendor data for reverse-engineering
    // without risking fake HR/power values. The frames feed
    // getLiveStreamStatus().vendorFrames → Train debug pane.
    for (const vc of _lastConnectedVendorNotifyChars) {
      try {
        const s = machineDev.monitorCharacteristicForService(
          vc.serviceUuid,
          vc.charUuid,
          (error: unknown, char: any) => {
            if (error || !char?.value) return;
            try {
              const bytes = Buffer.from(String(char.value), 'base64');
              const hex = bytes.toString('hex');
              _vendorFrames.push({
                atEpochMs: Date.now(),
                serviceUuid: vc.serviceUuid,
                charUuid: vc.charUuid,
                hex,
                byteLen: bytes.length,
              });
              if (_vendorFrames.length > MAX_VENDOR_FRAMES) {
                _vendorFrames.splice(0, _vendorFrames.length - MAX_VENDOR_FRAMES);
              }
            } catch { /* ignore bad frame */ }
          },
        );
        subs.push(s ?? null);
      } catch { /* characteristic not subscribable */ }
    }
  }

  // FTMS Fitness Machine Control Point (0x2AD9) wake sequence.
  // Per the FTMS 1.0 spec, many compliant machines — Rogue Echo among
  // them — do NOT start broadcasting Indoor Bike Data notifications
  // until a client has (a) subscribed to the Control Point response,
  // (b) sent 0x01 (Request Control), and (c) sent 0x07 (Start/Resume).
  // Without those writes, the bike stays silent even though the CCCD
  // on 0x2AD2 is enabled. Fire-and-forget: if the machine doesn't
  // need the wake sequence (some Peloton-style units don't), these
  // writes simply no-op or return an unsupported-op code.
  const CONTROL_POINT_UUID = '00002ad9-0000-1000-8000-00805f9b34fb';
  // Write via writeCharacteristicWithResponseForDevice. Some BLE
  // stacks expose the method on the device, others on the manager;
  // try both paths.
  const writeControl = async (payloadBase64: string) => {
    if (!machineDev) return null;
    try {
      if (typeof machineDev.writeCharacteristicWithResponseForService === 'function') {
        return await machineDev.writeCharacteristicWithResponseForService(
          FTMS_SERVICE_UUID,
          CONTROL_POINT_UUID,
          payloadBase64,
        );
      }
    } catch { /* try WithoutResponse below */ }
    try {
      if (typeof machineDev.writeCharacteristicWithoutResponseForService === 'function') {
        return await machineDev.writeCharacteristicWithoutResponseForService(
          FTMS_SERVICE_UUID,
          CONTROL_POINT_UUID,
          payloadBase64,
        );
      }
    } catch { /* noop */ }
    return null;
  };
  // Also subscribe to the control-point response so the machine
  // knows a client is listening — required by some vendors before
  // they'll honour Start/Resume.
  try {
    if (!machineDev) throw new Error('no-machine');
    const resp = machineDev.monitorCharacteristicForService(
      FTMS_SERVICE_UUID,
      CONTROL_POINT_UUID,
      () => { /* ignore response payloads; diagnostic only */ },
    );
    subs.push(resp ?? null);
  } catch { /* some machines expose CP as write-only */ }
  // Sequence the wake writes with tiny gaps so the machine state
  // machine can move: 0x01 Request Control → 0x07 Start/Resume.
  // Base64 of 0x01 is 'AQ=='; base64 of 0x07 is 'Bw=='.
  // Longer initial delay (600ms) gives the Indoor-Bike-Data + Control-
  // Point subscriptions time to finish arming before we issue writes;
  // some Echo / Assault firmware discards Start writes arriving before
  // the client's CCCD on the CP is committed.
  if (machineDev) {
    void (async () => {
      try {
        await new Promise((r) => setTimeout(r, 600));
        await writeControl('AQ==');
        await new Promise((r) => setTimeout(r, 300));
        await writeControl('Bw==');
      } catch { /* non-fatal */ }
    })();
  }

  // Echelon / Rogue Echo proprietary parser (ported from
  // qdomyos-zwift + echbt community work). Frame layout observed on
  // Echelon Connect Sport / EX-series (Rogue Echo V3 uses the same
  // chipset per community reports):
  //   byte 0 = 0xF0 header
  //   byte 1 = opcode (0xD1 workout-data, 0xD2 HR, 0xA1 device-info)
  //   byte 2 = payload length
  //   payload for 0xD1 (workout data):
  //     bytes 3..5   = elapsed time (seconds, big-endian u24)
  //     bytes 6..8   = total distance (tenths of a km, big-endian u24) — model-specific
  //     byte 9       = cadence (RPM)
  //     byte 10..11  = speed (0.1 km/h, big-endian u16) — model-specific
  //     byte 12      = resistance level (1..32)
  //   payload for 0xD2 (HR):
  //     byte 3..4    = HR bpm (u8 or big-endian u16 depending on firmware)
  // Power is NOT emitted by Echelon over BLE — keep it null rather
  // than fabricating a resistance×cadence estimate.
  const echelonFrameHandler = (error: unknown, char: any) => {
    if (error || !char?.value) return;
    try {
      const bytes = Buffer.from(String(char.value), 'base64');
      if (bytes.length < 3) return;
      if (bytes[0] !== 0xF0) return; // not an Echelon frame
      const opcode = bytes[1];
      const atEpochMs = Date.now();
      let cadenceRpm: number | null = null;
      let hr: number | null = null;
      let distanceM: number | null = null;
      let elapsedTimeS: number | null = null;
      let instantSpeedKph: number | null = null;
      let decoded = false;
      if (opcode === 0xD1 && bytes.length >= 13) {
        elapsedTimeS = (bytes[3] << 16) | (bytes[4] << 8) | bytes[5];
        const distTenths = (bytes[6] << 16) | (bytes[7] << 8) | bytes[8];
        distanceM = distTenths * 100; // tenths-of-km → meters
        const rpm = bytes[9];
        if (rpm >= 0 && rpm <= 250) cadenceRpm = rpm;
        const speed01 = (bytes[10] << 8) | bytes[11];
        if (speed01 <= 1200) instantSpeedKph = speed01 / 10;
        decoded = cadenceRpm != null;
      } else if (opcode === 0xD2 && bytes.length >= 4) {
        // Some variants encode HR as u8 at offset 3; others as
        // big-endian u16. Accept u8 when the u16 value looks invalid.
        const bpm8 = bytes[3];
        const bpm16 = (bytes[3] << 8) | bytes[4];
        if (bpm16 >= 30 && bpm16 <= 240) hr = bpm16;
        else if (bpm8 >= 30 && bpm8 <= 240) hr = bpm8;
        decoded = hr != null;
      }
      if (!decoded) {
        // Unknown or malformed Echelon frame — log for future decode,
        // do not emit metrics.
        _vendorFrames.push({
          atEpochMs,
          serviceUuid: ECHELON_SERVICE_UUID,
          charUuid: ECHELON_DATA_CHAR_UUID,
          hex: bytes.toString('hex'),
          byteLen: bytes.length,
        });
        if (_vendorFrames.length > MAX_VENDOR_FRAMES) {
          _vendorFrames.splice(0, _vendorFrames.length - MAX_VENDOR_FRAMES);
        }
        return;
      }
      const sample: FtmsLiveSample = {
        atEpochMs,
        instantaneousPowerW: null, // Echelon doesn't transmit power
        heartRateBpm: hr,
        energyKj: null,
        instantaneousCadenceRpm: cadenceRpm,
        instantaneousSpeedKph: instantSpeedKph,
        totalDistanceM: distanceM,
        resistanceLevel: bytes[12] >= 0 && bytes[12] <= 40 ? bytes[12] : null,
        elapsedTimeS,
      };
      _lastFtms = sample;
      _liveLastSampleAtMs = atEpochMs;
      if (typeof hr === 'number') { _lastHrBpm = hr; _lastHrAtMs = atEpochMs; }
      if (_sessionStartAtMs != null) pushSessionSample({
        atEpochMs,
        hrBpm: hr,
        powerW: null,
        cadenceRpm,
        distanceM,
        energyKj: null,
      });
      if (ftmsCb) ftmsCb(sample);
      for (const listener of _ftmsListeners) { try { listener(sample); } catch { /* ignore */ } }
      _state = { ..._state, status: 'receiving_data' };
    } catch { /* ignore bad frame */ }
  };

  if (machineDev && _lastConnectedServices.includes(ECHELON_SERVICE_UUID)) {
    // Subscribe to the two data characteristics.
    for (const dataChar of [ECHELON_DATA_CHAR_UUID, ECHELON_STATUS_CHAR_UUID]) {
      try {
        const s = machineDev.monitorCharacteristicForService(
          ECHELON_SERVICE_UUID,
          dataChar,
          echelonFrameHandler,
        );
        subs.push(s ?? null);
      } catch { /* char not notifiable on this firmware */ }
    }
    // Wake the data stream by writing the Echelon activation packet
    // to the write char. Schedule after the subscriptions are armed.
    void (async () => {
      try {
        await new Promise((r) => setTimeout(r, 400));
        if (typeof machineDev.writeCharacteristicWithResponseForService === 'function') {
          await machineDev.writeCharacteristicWithResponseForService(
            ECHELON_SERVICE_UUID,
            ECHELON_WRITE_CHAR_UUID,
            ECHELON_ACTIVATE_PAYLOAD_B64,
          ).catch(async () => {
            // Firmware that rejects with-response; fall through.
            if (typeof machineDev.writeCharacteristicWithoutResponseForService === 'function') {
              await machineDev.writeCharacteristicWithoutResponseForService(
                ECHELON_SERVICE_UUID,
                ECHELON_WRITE_CHAR_UUID,
                ECHELON_ACTIVATE_PAYLOAD_B64,
              ).catch(() => {});
            }
          });
        } else if (typeof machineDev.writeCharacteristicWithoutResponseForService === 'function') {
          await machineDev.writeCharacteristicWithoutResponseForService(
            ECHELON_SERVICE_UUID,
            ECHELON_WRITE_CHAR_UUID,
            ECHELON_ACTIVATE_PAYLOAD_B64,
          ).catch(() => {});
        }
      } catch { /* non-fatal */ }
    })();
  }

  return {
    stop: () => {
      for (const s of subs) { try { s?.remove?.(); } catch { /* ignore */ } }
      _liveStartedAtMs = null;
      const anyBound = !!(_hrConnectedRef || _machineConnectedRef);
      _state = { ..._state, status: anyBound ? 'connected' : (_state.moduleLinked ? 'idle' : 'bluetooth_unavailable') };
    },
    live: true,
    onHr: (cb) => { hrCb = cb; },
    onFtms: (cb) => { ftmsCb = cb; },
  };
}
