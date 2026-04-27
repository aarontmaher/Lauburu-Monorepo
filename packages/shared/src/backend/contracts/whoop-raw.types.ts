/**
 * Raw WHOOP ingest types — Layer 1 (raw source facts).
 *
 * Preserved exactly as received from the WHOOP MCP.
 * No interpretation, no baseline comparison, no coaching flags.
 * Missing stays missing (null, not zero).
 * Source timestamps required on every record.
 */

/** Immutable provenance pointer — structured, not free-form string. */
export interface SourceRef {
  layer: 'raw' | 'normalized' | 'artifact' | 'stable_memory';
  recordId: string;
  fieldPath: string | null;
  date: string;
}

/** A single raw WHOOP daily record as ingested from the MCP. */
export interface WhoopDailyMetricsRaw {
  /** Unique immutable record ID. */
  id: string;
  /** Schema version for this record shape. */
  schemaVersion: 1;
  /** When this record was first stored. */
  createdAt: string;
  /** When this record was last updated (re-ingest overwrites). */
  updatedAt: string;

  /** Athlete this record belongs to. */
  athleteId: string;
  /** Local date (YYYY-MM-DD) in the athlete's timezone. */
  localDate: string;
  /** IANA timezone at time of recording. */
  timezone: string;

  // ── Recovery ────────────────────────────────────────────────
  recoveryScore: number | null;
  hrvMs: number | null;
  rhrBpm: number | null;
  spo2Pct: number | null;
  skinTempCelsius: number | null;

  // ── Sleep ───────────────────────────────────────────────────
  sleepPerformancePct: number | null;
  sleepEfficiencyPct: number | null;
  totalSleepHours: number | null;
  swsHours: number | null;
  remHours: number | null;
  lightSleepHours: number | null;
  awakeHours: number | null;
  inBedHours: number | null;
  respiratoryRate: number | null;
  sleepDebtHours: number | null;
  sleepNeededBaselineHours: number | null;
  sleepConsistencyPct: number | null;

  // ── Strain / activity ───────────────────────────────────────
  dayStrain: number | null;
  dayKilojoules: number | null;
  dayAvgHr: number | null;
  dayMaxHr: number | null;

  // ── Workouts ────────────────────────────────────────────────
  workoutCount: number;
  workoutStrainTotal: number | null;
  workoutMinutesTotal: number | null;
  workoutDetails: WhoopRawWorkout[];

  // ── Source metadata ─────────────────────────────────────────
  /** When the WHOOP API last provided this data. */
  sourceUpdatedAt: string | null;
  /** Upstream cycle/sleep/recovery IDs for dedup. */
  sourceRecordIds: {
    cycleId: number | null;
    sleepId: string | null;
    recoveryCycleId: number | null;
  };
}

/** Raw workout as returned by WHOOP — no interpretation. */
export interface WhoopRawWorkout {
  id: string;
  sportId: number;
  sportName: string;
  strain: number;
  avgHr: number;
  maxHr: number;
  kilojoules: number;
  caloriesKcal: number | null;
  startIso: string;
  endIso: string;
  durationMin: number;
  percentRecorded: number | null;
  hrZones: WhoopRawHrZone[];
}

export interface WhoopRawHrZone {
  zoneIndex: number;
  durationMilli: number;
  percentOfWorkout: number;
}
