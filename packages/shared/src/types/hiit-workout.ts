/**
 * HIIT workout model — structured workout records with per-set
 * metrics for progress tracking and Coach consumption.
 */

export type HIITMachineType = 'assault_bike' | 'rower' | 'ski_erg' | 'treadmill' | 'manual' | 'other';

export type HIITProtocolFormat =
  | '30:15' | '30:30' | '30:60' | '30:90'
  | '20:10' | '20:40' | '10:50'
  | '4x4' | '3x3' | 'custom';

export type HIITMachineProvider =
  | 'concept2'
  | 'assault_bike_manual'
  | 'bluetooth_ftms'
  | 'apple_health_workout'
  | 'whoop_workout'
  | 'manual';

export interface HIITSetMetrics {
  setIndex: number;
  type: 'work' | 'rest';
  durationSeconds: number;
  /** Watts during this set. Null if not from a machine. */
  avgWatts: number | null;
  peakWatts: number | null;
  /** Calories for this set. */
  calories: number | null;
  /** Heart rate. */
  hrMin: number | null;
  hrMax: number | null;
  hrAvg: number | null;
  /** Distance (metres). */
  distanceM: number | null;
  /** Cadence (rpm/spm). */
  avgCadence: number | null;
}

export interface HIITWorkoutRecord {
  id: string;
  athleteId: string;
  date: string;
  createdAt: string;

  /** Protocol template. */
  templateId: string | null;
  protocolFormat: HIITProtocolFormat;
  machineType: HIITMachineType;
  machineProvider: HIITMachineProvider;

  /** Set-by-set data. */
  sets: HIITSetMetrics[];
  totalSets: number;
  workSets: number;
  restSets: number;

  /** Session totals. */
  totalDurationSeconds: number;
  totalCalories: number | null;
  totalWorkKj: number | null;
  avgWatts: number | null;
  peakWatts: number | null;
  avgHr: number | null;
  peakHr: number | null;

  /** Source metadata. */
  source: HIITMachineProvider;
  sourceRecordIds: string[];
  missingFields: string[];
}

/** Comparison against previous session of same template. */
export interface HIITProgressComparison {
  templateId: string;
  currentWorkoutId: string;
  previousWorkoutId: string | null;
  /** Per-set comparisons (work sets only). */
  setComparisons: Array<{
    setIndex: number;
    currentWatts: number | null;
    previousWatts: number | null;
    deltaWatts: number | null;
    currentHrAvg: number | null;
    previousHrAvg: number | null;
    deltaHr: number | null;
    currentCalories: number | null;
    previousCalories: number | null;
  }>;
  /** Session-level comparison. */
  avgWattsDelta: number | null;
  peakWattsDelta: number | null;
  avgHrDelta: number | null;
  totalCaloriesDelta: number | null;
  /** Fatigue: drop-off from first to last work set. */
  wattsDropOffPct: number | null;
  hrDriftPct: number | null;
}
