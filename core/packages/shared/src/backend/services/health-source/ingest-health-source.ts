/**
 * Generic health source ingestion — converts DailyMetrics from any
 * mobile health source (Apple Health, Health Connect, manual) into
 * the canonical HealthSourceDailyRecord for Layer 1 storage.
 *
 * Also normalizes into NormalizedDailyMetrics for Layer 2.
 * Pure functions. No network calls.
 */

import type { HealthSourceDailyRecord, HealthSourceProvider } from '../../contracts/health-source-raw.types';
import type { NormalizedDailyMetrics, NormalizationCompleteness } from '../../contracts/normalized-daily.types';
import type { SourceRef } from '../../contracts/whoop-raw.types';

const DERIVATION_VERSION = 'health_source_v1';

const EXPECTED_FIELDS = [
  'recoveryScore', 'hrvMs', 'restingHrBpm',
  'totalSleepHours', 'deepSleepHours', 'remSleepHours',
  'activeCaloriesKcal', 'dailyStrain',
] as const;

/** Input payload from mobile health sync. */
export interface HealthSourceIngestPayload {
  date: string;
  provider: HealthSourceProvider;
  recovery_score?: number | null;
  hrv_ms?: number | null;
  resting_hr?: number | null;
  sleep_hours?: number | null;
  deep_sleep_hours?: number | null;
  rem_sleep_hours?: number | null;
  active_calories?: number | null;
  step_count?: number | null;
  daily_strain?: number | null;
  workout_count?: number;
  workout_minutes_total?: number | null;
  grappling_session_count?: number;
  source_record_ids?: string[];
  source_updated_at?: string | null;
  /**
   * Upstream app/provider detected from raw records — e.g. the Health
   * Connect `dataOrigin` package name (`com.polar.polarflow`) or a
   * friendly string ("Polar Flow"). Propagated to the raw record for
   * provenance and surfaced in source-health for truthful Coach
   * answers. Only set when the ingest path actually detected a
   * specific upstream app; never invented.
   */
  source_app?: string | null;
  source_package?: string | null;
  /**
   * For provider=`polar_via_health_connect`: which domains on this day
   * genuinely came from a Polar-origin record. Used to build per-domain
   * coverage without conflating Polar with other HC-writing apps.
   */
  domains_from_polar?: string[];
}

let _idCounter = 0;
function generateId(prefix: string, date: string): string {
  return `${prefix}_${date}_${Date.now()}_${++_idCounter}`;
}

/** Ingest a single health source record into Layer 1 shape. */
export function ingestHealthSourceDay(
  payload: HealthSourceIngestPayload,
  athleteId: string,
): HealthSourceDailyRecord {
  const now = new Date().toISOString();
  return {
    id: generateId('hs_raw', payload.date),
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId,
    date: payload.date,
    provider: payload.provider,
    recoveryScore: payload.recovery_score ?? null,
    hrvMs: payload.hrv_ms ?? null,
    restingHrBpm: payload.resting_hr ?? null,
    totalSleepHours: payload.sleep_hours ?? null,
    deepSleepHours: payload.deep_sleep_hours ?? null,
    remSleepHours: payload.rem_sleep_hours ?? null,
    activeCaloriesKcal: payload.active_calories ?? null,
    stepCount: payload.step_count ?? null,
    dailyStrain: payload.daily_strain ?? null,
    workoutCount: payload.workout_count ?? 0,
    workoutMinutesTotal: payload.workout_minutes_total ?? null,
    grapplingSessionCount: payload.grappling_session_count ?? 0,
    sourceUpdatedAt: payload.source_updated_at ?? null,
    sourceRecordIds: payload.source_record_ids ?? [],
    sourceApp: payload.source_app ?? null,
    sourcePackage: payload.source_package ?? null,
    domainsFromPolar: payload.domains_from_polar ?? [],
  };
}

/** Normalize a health source record into Layer 2 NormalizedDailyMetrics. */
export function normalizeHealthSourceDay(
  raw: HealthSourceDailyRecord,
): NormalizedDailyMetrics {
  const now = new Date().toISOString();

  const fieldMap: Record<string, unknown> = {
    recoveryScore: raw.recoveryScore,
    hrvMs: raw.hrvMs,
    restingHrBpm: raw.restingHrBpm,
    totalSleepHours: raw.totalSleepHours,
    deepSleepHours: raw.deepSleepHours,
    remSleepHours: raw.remSleepHours,
    activeCaloriesKcal: raw.activeCaloriesKcal,
    dailyStrain: raw.dailyStrain,
  };

  const presentFields: string[] = [];
  const missingFields: string[] = [];
  for (const field of EXPECTED_FIELDS) {
    if (fieldMap[field] != null) presentFields.push(field);
    else missingFields.push(field);
  }

  const completeness: NormalizationCompleteness =
    missingFields.length === 0 ? 'complete'
      : presentFields.length >= EXPECTED_FIELDS.length * 0.5 ? 'partial'
        : 'minimal';

  const sourceAgeHours = raw.sourceUpdatedAt
    ? Math.max(0, (Date.now() - new Date(raw.sourceUpdatedAt).getTime()) / 3600_000)
    : null;

  const sourceRefs: SourceRef[] = [{
    layer: 'raw',
    recordId: raw.id,
    fieldPath: null,
    date: raw.date,
  }];

  return {
    id: generateId('norm_hs', raw.date),
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    derivationVersion: DERIVATION_VERSION,
    athleteId: raw.athleteId,
    date: raw.date,
    recoveryScore: raw.recoveryScore,
    hrvMs: raw.hrvMs,
    restingHrBpm: raw.restingHrBpm,
    spo2Pct: null,
    skinTempCelsius: null,
    respiratoryRate: null,
    totalSleepHours: raw.totalSleepHours,
    deepSleepHours: raw.deepSleepHours,
    remSleepHours: raw.remSleepHours,
    lightSleepHours: null,
    awakeHours: null,
    sleepEfficiencyPct: null,
    sleepDebtHours: null,
    dailyStrain: raw.dailyStrain,
    activeCaloriesKcal: raw.activeCaloriesKcal,
    totalCaloriesKj: null,
    workoutCount: raw.workoutCount,
    workoutMinutesTotal: raw.workoutMinutesTotal,
    workoutStrainTotal: null,
    grapplingSessionCount: raw.grapplingSessionCount,
    workoutSportNames: [],
    nutritionCalories: null,
    nutritionProteinGrams: null,
    nutritionCarbGrams: null,
    nutritionFatGrams: null,
    nutritionCoverage: 'none',
    presentFields,
    missingFields,
    completeness,
    sourceAgeHours: sourceAgeHours != null ? Math.round(sourceAgeHours * 10) / 10 : null,
    sourceRecordIds: [raw.id],
    sourceRefs,
    provider: raw.provider,
  };
}
