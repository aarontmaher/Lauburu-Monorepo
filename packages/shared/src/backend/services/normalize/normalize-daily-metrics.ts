/**
 * Normalize raw WHOOP records into the interpretation-free
 * NormalizedDailyMetrics shape (Layer 2).
 *
 * Allowed transforms:
 *   - unit conversion (kJ → kcal)
 *   - daily rollups (workout counts, totals)
 *   - completeness assessment (which fields are present/missing)
 *   - source age calculation
 *   - grappling detection from sport names
 *
 * STRICTLY NO athlete-baseline-dependent interpretation:
 *   NO recovery_below_baseline_flag
 *   NO readiness classification
 *   NO coaching recommendations
 *   NO pattern detection
 *
 * Those belong in the daily_refresh_artifact (Layer 3).
 */

import type { WhoopDailyMetricsRaw } from '../../contracts/whoop-raw.types';
import type { SourceRef } from '../../contracts/whoop-raw.types';
import type {
  NormalizedDailyMetrics,
  NormalizationCompleteness,
} from '../../contracts/normalized-daily.types';

const DERIVATION_VERSION = 'normalize_v1';

const GRAPPLING_SPORTS = new Set([
  'jiu-jitsu', 'brazilian-jiu-jitsu', 'bjj',
  'wrestling', 'judo', 'grappling', 'martial-arts',
]);

const EXPECTED_FIELDS = [
  'recoveryScore', 'hrvMs', 'restingHrBpm', 'spo2Pct',
  'totalSleepHours', 'deepSleepHours', 'remSleepHours',
  'sleepEfficiencyPct', 'dailyStrain', 'respiratoryRate',
] as const;

let _normIdCounter = 0;
function generateNormId(date: string): string {
  return `norm_${date}_${Date.now()}_${++_normIdCounter}`;
}

/**
 * Normalize a single raw WHOOP record.
 * Pure, deterministic (except for id/timestamp generation).
 */
export function normalizeWhoopDay(
  raw: WhoopDailyMetricsRaw,
): NormalizedDailyMetrics {
  const now = new Date().toISOString();

  // Unit conversion: kJ → kcal
  const activeCaloriesKcal = raw.dayKilojoules != null
    ? Math.round(raw.dayKilojoules / 4.184)
    : null;

  // Grappling detection from sport names
  const grapplingCount = raw.workoutDetails.filter(
    (w) => GRAPPLING_SPORTS.has(w.sportName.toLowerCase()),
  ).length;

  const sportNames = [...new Set(raw.workoutDetails.map((w) => w.sportName))];

  // Completeness assessment — strictly deterministic, no baselines
  const presentFields: string[] = [];
  const missingFields: string[] = [];

  const fieldMap: Record<string, unknown> = {
    recoveryScore: raw.recoveryScore,
    hrvMs: raw.hrvMs,
    restingHrBpm: raw.rhrBpm,
    spo2Pct: raw.spo2Pct,
    totalSleepHours: raw.totalSleepHours,
    deepSleepHours: raw.swsHours,
    remSleepHours: raw.remHours,
    sleepEfficiencyPct: raw.sleepEfficiencyPct,
    dailyStrain: raw.dayStrain,
    respiratoryRate: raw.respiratoryRate,
  };

  for (const field of EXPECTED_FIELDS) {
    if (fieldMap[field] != null) {
      presentFields.push(field);
    } else {
      missingFields.push(field);
    }
  }

  const completeness: NormalizationCompleteness =
    missingFields.length === 0 ? 'complete'
      : presentFields.length >= EXPECTED_FIELDS.length * 0.6 ? 'partial'
        : 'minimal';

  // Source age
  const sourceAgeHours = raw.sourceUpdatedAt
    ? Math.max(0, (Date.now() - new Date(raw.sourceUpdatedAt).getTime()) / 3600_000)
    : null;

  // Provenance
  const sourceRefs: SourceRef[] = [{
    layer: 'raw',
    recordId: raw.id,
    fieldPath: null,
    date: raw.localDate,
  }];

  return {
    id: generateNormId(raw.localDate),
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    derivationVersion: DERIVATION_VERSION,
    athleteId: raw.athleteId,
    date: raw.localDate,

    recoveryScore: raw.recoveryScore,
    hrvMs: raw.hrvMs,
    restingHrBpm: raw.rhrBpm,
    spo2Pct: raw.spo2Pct,
    skinTempCelsius: raw.skinTempCelsius,
    respiratoryRate: raw.respiratoryRate,

    totalSleepHours: raw.totalSleepHours,
    deepSleepHours: raw.swsHours,
    remSleepHours: raw.remHours,
    lightSleepHours: raw.lightSleepHours,
    awakeHours: raw.awakeHours,
    sleepEfficiencyPct: raw.sleepEfficiencyPct,
    sleepDebtHours: raw.sleepDebtHours,

    dailyStrain: raw.dayStrain,
    activeCaloriesKcal,
    totalCaloriesKj: raw.dayKilojoules,

    workoutCount: raw.workoutCount,
    workoutMinutesTotal: raw.workoutMinutesTotal,
    workoutStrainTotal: raw.workoutStrainTotal,
    grapplingSessionCount: grapplingCount,
    workoutSportNames: sportNames,

    // Nutrition — null from WHOOP (nutrition comes from Cronometer/manual)
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
    provider: 'whoop',
  };
}

/**
 * Normalize a batch of raw WHOOP records.
 * Returns normalized records sorted by date ascending.
 */
export function normalizeWhoopBatch(
  rawRecords: WhoopDailyMetricsRaw[],
): NormalizedDailyMetrics[] {
  return rawRecords
    .map(normalizeWhoopDay)
    .sort((a, b) => a.date.localeCompare(b.date));
}
