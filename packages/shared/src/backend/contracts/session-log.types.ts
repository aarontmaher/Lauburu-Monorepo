/**
 * Session log ingest contracts — raw + normalized session records
 * for HIIT workouts, training sessions, and future machine-synced data.
 *
 * Supports manual HIIT now. Machine-sync adapters can land later
 * without changing this contract — they just produce richer per-set data.
 */

import type { HIITMachineType, HIITProtocolFormat, HIITMachineProvider, HIITSetMetrics } from '../../types/hiit-workout';

export type SessionLogSource = 'manual' | 'concept2' | 'bluetooth_ftms' | 'apple_health_workout' | 'whoop_workout';

/** Per-set metrics with HR recovery tracking. */
export interface SessionSetMetrics extends HIITSetMetrics {
  /** HR at start of this set (for recovery tracking between sets). */
  hrAtStart: number | null;
  /** HR at end of this set. */
  hrAtEnd: number | null;
  /** HR range during this set (max - min). */
  hrRange: number | null;
  /** HR recovery from previous set (previous hrAtEnd - this hrAtStart). Null for first set. */
  hrRecoveryFromPrevious: number | null;
}

/** Raw session log — what the mobile app or machine adapter sends. */
export interface SessionLogIngestPayload {
  /** Unique session ID (generated client-side). */
  sessionId: string;
  athleteId: string;
  date: string;
  createdAt: string;

  /** Protocol info. */
  templateId: string | null;
  protocolFormat: HIITProtocolFormat | string;
  machineType: HIITMachineType;
  machineProvider: HIITMachineProvider;
  source: SessionLogSource;

  /** Per-set data. */
  sets: SessionSetMetrics[];
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
  sourceRecordIds: string[];
  missingFields: string[];
}

/** Stored raw session record (Layer 1). */
export interface SessionLogRaw {
  id: string;
  schemaVersion: 1;
  createdAt: string;
  updatedAt: string;
  athleteId: string;
  date: string;
  payload: SessionLogIngestPayload;
}

/** Normalized session summary (Layer 2) — deterministic, no interpretation. */
export interface NormalizedSessionSummary {
  id: string;
  schemaVersion: 1;
  createdAt: string;
  athleteId: string;
  date: string;
  sessionId: string;

  /** Protocol. */
  templateId: string | null;
  protocolFormat: string;
  machineType: HIITMachineType;
  machineProvider: HIITMachineProvider;
  source: SessionLogSource;

  /** Totals. */
  totalSets: number;
  workSets: number;
  restSets: number;
  totalDurationSeconds: number;
  totalCalories: number | null;
  avgWatts: number | null;
  peakWatts: number | null;
  avgHr: number | null;
  peakHr: number | null;

  /** Fatigue indicators (deterministic, not interpreted). */
  wattsDropOffPct: number | null;
  hrDriftPct: number | null;
  avgHrRecoveryBpm: number | null;

  /** Data quality. */
  hasPerSetWatts: boolean;
  hasPerSetHr: boolean;
  missingFields: string[];

  /** Machine connectivity truth. */
  machineConnected: boolean;
}

/**
 * Build a normalized session summary from a raw session log.
 * Pure function. No network, no side effects.
 */
export function normalizeSessionLog(raw: SessionLogIngestPayload): Omit<NormalizedSessionSummary, 'id' | 'schemaVersion' | 'createdAt'> {
  const workSets = raw.sets.filter((s) => s.type === 'work');

  // Fatigue: watts drop-off from first to last work set
  const firstWatts = workSets[0]?.avgWatts;
  const lastWatts = workSets[workSets.length - 1]?.avgWatts;
  const wattsDropOffPct = firstWatts != null && lastWatts != null && firstWatts > 0
    ? Math.round(((lastWatts - firstWatts) / firstWatts) * 100)
    : null;

  // HR drift: increase from first to last work set
  const firstHr = workSets[0]?.hrAvg;
  const lastHr = workSets[workSets.length - 1]?.hrAvg;
  const hrDriftPct = firstHr != null && lastHr != null && firstHr > 0
    ? Math.round(((lastHr - firstHr) / firstHr) * 100)
    : null;

  // Average HR recovery between sets
  const recoveries = raw.sets
    .filter((s): s is SessionSetMetrics => 'hrRecoveryFromPrevious' in s && s.hrRecoveryFromPrevious != null)
    .map((s) => s.hrRecoveryFromPrevious!);
  const avgHrRecoveryBpm = recoveries.length > 0
    ? Math.round(recoveries.reduce((a, b) => a + b, 0) / recoveries.length)
    : null;

  const hasPerSetWatts = workSets.some((s) => s.avgWatts != null);
  const hasPerSetHr = workSets.some((s) => s.hrAvg != null);

  return {
    athleteId: raw.athleteId,
    date: raw.date,
    sessionId: raw.sessionId,
    templateId: raw.templateId,
    protocolFormat: raw.protocolFormat,
    machineType: raw.machineType,
    machineProvider: raw.machineProvider,
    source: raw.source,
    totalSets: raw.totalSets,
    workSets: raw.workSets,
    restSets: raw.restSets,
    totalDurationSeconds: raw.totalDurationSeconds,
    totalCalories: raw.totalCalories,
    avgWatts: raw.avgWatts,
    peakWatts: raw.peakWatts,
    avgHr: raw.avgHr,
    peakHr: raw.peakHr,
    wattsDropOffPct,
    hrDriftPct,
    avgHrRecoveryBpm,
    hasPerSetWatts,
    hasPerSetHr,
    missingFields: raw.missingFields,
    machineConnected: raw.source !== 'manual',
  };
}
