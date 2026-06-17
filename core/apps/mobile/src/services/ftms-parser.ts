/**
 * FTMS (Fitness Machine Service) characteristic parser.
 *
 * Parses the raw BLE characteristic values from FTMS-compliant machines
 * (Indoor Bike Data 0x2AD2, Rower Data 0x2AD5, Treadmill Data 0x2ACD,
 * Cross Trainer Data 0x2AD1) into our LiveMachineSample shape.
 *
 * BLE data arrives as a DataView (little-endian). The first 2 bytes
 * are a flags field that tells which optional fields are present.
 *
 * This parser is pure: no BLE calls, no side effects. Tests can run
 * it against captured byte arrays.
 *
 * BLOCKED: This code compiles and is ready to use, but requires
 * react-native-ble-plx to actually receive BLE notifications.
 * Adding react-native-ble-plx requires a native rebuild (new APK).
 */

import type { LiveMachineSample, MachineKind } from './machine-connector';

/**
 * Parse Indoor Bike Data (UUID 0x2AD2).
 * Spec: FTMS Indoor Bike Data characteristic, Bluetooth SIG.
 */
export function parseIndoorBikeData(bytes: DataView): Partial<LiveMachineSample> {
  const flags = bytes.getUint16(0, true);
  let offset = 2;
  const sample: Partial<LiveMachineSample> = { kind: 'bike', at: Date.now() };

  // Bit 0: More Data (0 = present)
  if (!(flags & 0x0001)) {
    sample.speed_kmh = bytes.getUint16(offset, true) / 100;
    offset += 2;
  }
  // Bit 1: Average Speed Present
  if (flags & 0x0002) { offset += 2; }
  // Bit 2: Instantaneous Cadence
  if (flags & 0x0004) {
    sample.cadence = bytes.getUint16(offset, true) / 2; // 0.5 resolution
    offset += 2;
  }
  // Bit 3: Average Cadence
  if (flags & 0x0008) { offset += 2; }
  // Bit 4: Total Distance (3 bytes)
  if (flags & 0x0010) {
    sample.distance_m = bytes.getUint8(offset) | (bytes.getUint8(offset + 1) << 8) | (bytes.getUint8(offset + 2) << 16);
    offset += 3;
  }
  // Bit 5: Resistance Level
  if (flags & 0x0020) { offset += 2; }
  // Bit 6: Instantaneous Power
  if (flags & 0x0040) {
    sample.power_w = bytes.getInt16(offset, true);
    offset += 2;
  }
  // Bit 7: Average Power
  if (flags & 0x0080) { offset += 2; }
  // Bit 8-9: Expended Energy
  if (flags & 0x0100) {
    sample.calories = bytes.getUint16(offset, true);
    offset += 4; // total + per-hour + per-minute
  }
  // Bit 10: Heart Rate
  if (flags & 0x0400) {
    sample.heart_rate_bpm = bytes.getUint8(offset);
    offset += 1;
  }
  // Bit 12: Elapsed Time
  if (flags & 0x1000) {
    sample.elapsed_s = bytes.getUint16(offset, true);
  }

  return sample;
}

/**
 * Parse Rower Data (UUID 0x2AD5).
 */
export function parseRowerData(bytes: DataView): Partial<LiveMachineSample> {
  const flags = bytes.getUint16(0, true);
  let offset = 2;
  const sample: Partial<LiveMachineSample> = { kind: 'rower', at: Date.now() };

  // Bit 0: More Data
  if (!(flags & 0x0001)) {
    sample.stroke_count = bytes.getUint16(offset, true);
    offset += 2;
  }
  // Bit 1: Average Stroke Rate
  if (flags & 0x0002) { offset += 1; }
  // Bit 2: Total Distance (3 bytes)
  if (flags & 0x0004) {
    sample.distance_m = bytes.getUint8(offset) | (bytes.getUint8(offset + 1) << 8) | (bytes.getUint8(offset + 2) << 16);
    offset += 3;
  }
  // Bit 3: Instantaneous Pace (seconds per 500m)
  if (flags & 0x0008) {
    sample.pace_s = bytes.getUint16(offset, true);
    offset += 2;
  }
  // Bit 5: Instantaneous Power
  if (flags & 0x0020) {
    sample.power_w = bytes.getInt16(offset, true);
    offset += 2;
  }
  // Bit 9: Expended Energy
  if (flags & 0x0200) {
    sample.calories = bytes.getUint16(offset, true);
    offset += 4;
  }
  // Bit 10: Heart Rate
  if (flags & 0x0400) {
    sample.heart_rate_bpm = bytes.getUint8(offset);
    offset += 1;
  }
  // Bit 12: Elapsed Time
  if (flags & 0x1000) {
    sample.elapsed_s = bytes.getUint16(offset, true);
  }

  return sample;
}

/**
 * Route a BLE characteristic UUID to the correct parser.
 */
export function parseFTMSCharacteristic(
  uuid: string,
  bytes: DataView,
): Partial<LiveMachineSample> | null {
  const lower = uuid.toLowerCase();
  if (lower.includes('2ad2')) return parseIndoorBikeData(bytes);
  if (lower.includes('2ad5')) return parseRowerData(bytes);
  // Treadmill (2ACD) and Cross Trainer (2AD1) share a similar structure.
  // Add parsers when real device testing begins.
  return null;
}

/**
 * FTMS Service UUID and key characteristic UUIDs for BLE scanning.
 */
export const FTMS_SERVICE_UUID = '00001826-0000-1000-8000-00805f9b34fb';
export const FTMS_INDOOR_BIKE_CHAR = '00002ad2-0000-1000-8000-00805f9b34fb';
export const FTMS_ROWER_CHAR = '00002ad5-0000-1000-8000-00805f9b34fb';
export const FTMS_TREADMILL_CHAR = '00002acd-0000-1000-8000-00805f9b34fb';
export const FTMS_CROSS_TRAINER_CHAR = '00002ad1-0000-1000-8000-00805f9b34fb';
export const FTMS_CONTROL_POINT_CHAR = '00002ad9-0000-1000-8000-00805f9b34fb';

/**
 * Per-set accumulation from a stream of samples.
 */
export interface SetAccumulator {
  startedAt: number;
  endedAt: number;
  samples: Partial<LiveMachineSample>[];
  avgWatts: number | null;
  peakWatts: number | null;
  totalCalories: number | null;
  avgHr: number | null;
  maxHr: number | null;
  minHr: number | null;
  hrRange: number | null;
  totalDistance: number | null;
  avgCadence: number | null;
}

export function accumulateSet(samples: Partial<LiveMachineSample>[]): SetAccumulator | null {
  if (samples.length === 0) return null;
  const watts = samples.map((s) => s.power_w).filter((w): w is number => w != null);
  const hrs = samples.map((s) => s.heart_rate_bpm).filter((h): h is number => h != null);
  const cadences = samples.map((s) => s.cadence).filter((c): c is number => c != null);
  const distances = samples.map((s) => s.distance_m).filter((d): d is number => d != null);
  const calories = samples.map((s) => s.calories).filter((c): c is number => c != null);

  const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
  const maxVal = (arr: number[]) => arr.length ? Math.max(...arr) : null;
  const minVal = (arr: number[]) => arr.length ? Math.min(...arr) : null;

  return {
    startedAt: samples[0].at ?? Date.now(),
    endedAt: samples[samples.length - 1].at ?? Date.now(),
    samples,
    avgWatts: avg(watts),
    peakWatts: maxVal(watts),
    totalCalories: calories.length ? Math.max(...calories) : null,
    avgHr: avg(hrs),
    maxHr: maxVal(hrs),
    minHr: minVal(hrs),
    hrRange: hrs.length >= 2 ? Math.max(...hrs) - Math.min(...hrs) : null,
    totalDistance: distances.length ? Math.max(...distances) : null,
    avgCadence: avg(cadences),
  };
}
