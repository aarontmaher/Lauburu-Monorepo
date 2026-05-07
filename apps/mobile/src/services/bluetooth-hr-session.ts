/**
 * Phase 1 scaffold for Train-session Bluetooth Heart Rate Service support.
 *
 * This module intentionally does not scan, connect, subscribe, render UI, or
 * persist session data. Phase 2 can replace the stubbed methods with
 * react-native-ble-plx HRS reads after a native rebuild proves the permission
 * scaffold on both platforms.
 *
 * Privacy guardrail: never expose MAC addresses, peripheral UUIDs, raw service
 * UUIDs, or stable device identifiers through this API.
 */

export const BLUETOOTH_HR_SERVICE_UUID = '0000180d-0000-1000-8000-00805f9b34fb';
export const BLUETOOTH_HR_MEASUREMENT_UUID = '00002a37-0000-1000-8000-00805f9b34fb';

export type BluetoothHrSessionStatus =
  | 'planned'
  | 'native_rebuild_required'
  | 'permission_needed'
  | 'ready_to_scan'
  | 'scanning'
  | 'connected'
  | 'disconnected'
  | 'error';

export interface BluetoothHrSensorPreview {
  /** Vendor-supplied display name only. Do not include MAC/UUID. */
  displayName: string;
  /** Stateless signal indicator for the current scan result. */
  signalStrength: 'weak' | 'ok' | 'strong' | 'unknown';
}

export interface BluetoothHrSample {
  bpm: number;
  sampledAt: string;
  sourceLabel: 'Bluetooth HR sensor';
}

export interface BluetoothHrSessionSnapshot {
  status: BluetoothHrSessionStatus;
  sourceLabel: 'Bluetooth HR sensor';
  latestSample: BluetoothHrSample | null;
  sensors: BluetoothHrSensorPreview[];
  message: string;
}

export function getBluetoothHrSessionSnapshot(): BluetoothHrSessionSnapshot {
  return {
    status: 'native_rebuild_required',
    sourceLabel: 'Bluetooth HR sensor',
    latestSample: null,
    sensors: [],
    message:
      'Bluetooth heart-rate sensor support is scaffolded only. A native rebuild and admin-gated Train UI are required before scanning.',
  };
}

export async function startBluetoothHrScan(): Promise<BluetoothHrSensorPreview[]> {
  // TODO Phase 2: request permission on user tap, scan foreground-only for HRS
  // devices through react-native-ble-plx, and return display name + signal
  // strength only. Do not return MAC addresses or peripheral UUIDs.
  return [];
}

export async function stopBluetoothHrSession(): Promise<void> {
  // TODO Phase 2: disconnect the active HRS peripheral on session end.
}
