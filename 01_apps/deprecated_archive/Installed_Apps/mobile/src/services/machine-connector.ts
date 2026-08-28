/**
 * Machine connector — unified interface for cardio machine data sources.
 *
 * ARCHITECTURE INTENT
 *
 * This file generalises `bike-connect.ts` (which was Rogue-Echo specific)
 * into a modality-aware connector surface that covers every FTMS device
 * category we care about: bike, rower, skierg, treadmill. It is the
 * seam a real BLE/FTMS implementation will land on.
 *
 * Today this is a stub — no BLE, no pairing, no live metrics. The stub
 * exists so the rest of the app (store + UI) can depend on a stable
 * shape while the hardware path is wired incrementally.
 *
 * WHY THIS EXISTS
 *
 * WHOOP provides excellent readiness + post-session strain + HRV/RHR
 * trends, but it cannot see the machine-side output of a cardio session.
 * It doesn't know power, cadence, distance, calories, pace, stroke rate,
 * or lap splits — all of which the machine itself publishes over
 * Bluetooth FTMS. For the app to become a real ErgZone replacement it
 * needs the machine-output layer as first-class data, and WHOOP stays
 * as the physiology layer alongside it.
 *
 * TARGET PROTOCOL
 *
 * Bluetooth Fitness Machine Service (FTMS) — service UUID 0x1826.
 * Characteristic UUIDs we care about:
 *   0x2ACD  Treadmill Data
 *   0x2AD1  Cross Trainer Data
 *   0x2AD2  Indoor Bike Data
 *   0x2AD3  Step Climber Data
 *   0x2AD4  Stair Climber Data
 *   0x2AD5  Rower Data
 *   0x2ACE  Fitness Machine Feature
 *   0x2ACC  Fitness Machine Control Point
 *
 * IMPLEMENTATION PATH WHEN READY
 *   1. npm install react-native-ble-plx (or equivalent expo module)
 *   2. Implement scan/connect for FTMS service UUID 0x1826
 *   3. For each target characteristic above, parse per the FTMS spec
 *      (little-endian flags field + conditional fields)
 *   4. Feed parsed metrics to the machine-store as live data
 *   5. On disconnect, freeze final metrics into machine-store.lastSession
 *
 * Nothing in the app should call BLE directly — always go through
 * `getMachineConnector()` so the stub/real swap is a one-file change.
 */

import type { Modality } from '@lauburu/shared';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MachineConnectionState =
  | 'disconnected'
  | 'scanning'
  | 'connecting'
  | 'connected'
  | 'error';

/** Machine categories we map onto shared `Modality`. */
export type MachineKind = 'bike' | 'rower' | 'skierg' | 'treadmill' | 'other';

/**
 * A single live sample from a connected machine. Every field is optional
 * because different FTMS profiles expose different subsets (e.g. treadmill
 * exposes speed+incline but not power; rower exposes pace+stroke rate).
 */
export interface LiveMachineSample {
  at: number; // Date.now() when the sample was emitted
  kind: MachineKind;
  elapsed_s?: number;
  distance_m?: number;
  calories?: number;
  power_w?: number;
  cadence?: number;
  speed_kmh?: number;
  pace_s?: number;
  heart_rate_bpm?: number;
  stroke_count?: number;
}

/** Metadata about a discovered but not-yet-connected machine. */
export interface DiscoveredMachine {
  id: string;
  name: string;
  kind: MachineKind;
  rssi?: number;
}

/** Unified connector interface. Stub or real implementations satisfy this. */
export interface IMachineConnector {
  getState(): MachineConnectionState;
  /** Start scanning for FTMS devices. No-op on stub. */
  startScan(timeoutMs?: number): Promise<DiscoveredMachine[]>;
  stopScan(): void;
  connect(deviceId: string): Promise<boolean>;
  disconnect(): Promise<void>;
  getLatestSample(): LiveMachineSample | null;
  /** Subscribe to live samples. Returns an unsubscribe function. */
  onSample(cb: (sample: LiveMachineSample) => void): () => void;
}

// ---------------------------------------------------------------------------
// Stub implementation
// ---------------------------------------------------------------------------

class StubMachineConnector implements IMachineConnector {
  getState(): MachineConnectionState {
    return 'disconnected';
  }
  async startScan(): Promise<DiscoveredMachine[]> {
    return [];
  }
  stopScan(): void {}
  async connect(): Promise<boolean> {
    return false;
  }
  async disconnect(): Promise<void> {}
  getLatestSample(): LiveMachineSample | null {
    return null;
  }
  onSample(): () => void {
    return () => {};
  }
}

let _singleton: IMachineConnector | null = null;

/**
 * Get the current machine connector. Returns the stub today. When real
 * BLE lands, this is the single file to swap — every caller goes
 * through this accessor.
 */
export function getMachineConnector(): IMachineConnector {
  if (!_singleton) _singleton = new StubMachineConnector();
  return _singleton;
}

// ---------------------------------------------------------------------------
// Modality helpers
// ---------------------------------------------------------------------------

/** Map the shared Modality enum to a machine kind for connector targeting. */
export function machineKindForModality(modality: Modality | undefined): MachineKind {
  if (modality === 'assault_bike' || modality === 'bike') return 'bike';
  if (modality === 'rower') return 'rower';
  if (modality === 'skierg') return 'skierg';
  if (modality === 'running') return 'treadmill';
  return 'other';
}

/** True if this modality would plausibly expose machine metrics via FTMS. */
export function modalitySupportsMachineData(modality: Modality | undefined): boolean {
  return ['assault_bike', 'bike', 'rower', 'skierg', 'running'].includes(
    modality ?? '',
  );
}
