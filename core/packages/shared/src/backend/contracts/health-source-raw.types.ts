/**
 * Generic health source raw ingest types — Layer 1.
 *
 * Accepts health records from Apple Health, Health Connect,
 * WHOOP-via-Apple, or manual entries. Source-agnostic shape
 * that normalizes into the same NormalizedDailyMetrics.
 *
 * Not WHOOP-specific — this is the bridge for all non-WHOOP
 * health sources to enter the canonical AI store.
 */

export type HealthSourceProvider =
  | 'apple_health'
  | 'health_connect'
  | 'whoop_via_apple'
  | 'whoop_direct'
  | 'manual'
  | 'polar'
  | 'polar_via_health_connect'
  | 'direct_polar'
  | 'samsung_health_via_health_connect'
  | 'samsung_health_direct'
  | 'concept2_logbook'
  | 'ergdata_health_connect'
  | 'garmin';

export interface HealthSourceDailyRecord {
  id: string;
  schemaVersion: 1;
  createdAt: string;
  updatedAt: string;
  athleteId: string;
  date: string;
  provider: HealthSourceProvider;

  // Recovery / readiness (may be null from many sources)
  recoveryScore: number | null;
  hrvMs: number | null;
  restingHrBpm: number | null;

  // Sleep
  totalSleepHours: number | null;
  deepSleepHours: number | null;
  remSleepHours: number | null;

  // Activity
  activeCaloriesKcal: number | null;
  stepCount: number | null;
  dailyStrain: number | null;

  // Workouts
  workoutCount: number;
  workoutMinutesTotal: number | null;
  grapplingSessionCount: number;

  // Provenance
  sourceUpdatedAt: string | null;
  sourceRecordIds: string[];
  /**
   * Upstream app/provider detected from the raw records — e.g. the Health
   * Connect `dataOrigin` package name. For Android Health Connect this is
   * how we distinguish Polar Flow (`com.polar.polarflow`) from Samsung
   * Health, Garmin Connect, etc. Optional: not every ingest path
   * populates this (e.g. manual, whoop bridge).
   */
  sourceApp?: string | null;
  sourcePackage?: string | null;
  /**
   * Per-domain provenance: which domains on this day actually came from a
   * Polar-origin record. Only populated when provider is
   * `polar_via_health_connect`. Empty array = no Polar data for that
   * domain on that day even if the Health Connect record contains data
   * from another app.
   */
  domainsFromPolar?: string[];
}
