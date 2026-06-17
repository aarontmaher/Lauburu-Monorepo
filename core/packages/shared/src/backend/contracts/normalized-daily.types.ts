/**
 * Normalized daily metrics — Layer 2 (deterministic transforms).
 *
 * Transforms raw source records into a uniform shape.
 * Allowed transforms: unit conversion, daily rollups,
 * completeness assessment, source-age calculation.
 *
 * STRICTLY NO interpretation that depends on athlete memory:
 *   NO baseline comparison flags
 *   NO readiness classification
 *   NO coaching recommendations
 *   NO pattern detection
 * Those belong in Layer 3 (daily_refresh_artifact).
 */

import type { SourceRef } from './whoop-raw.types';

export type NormalizationCompleteness = 'complete' | 'partial' | 'minimal';

/** A single normalized daily record. Source-agnostic shape. */
export interface NormalizedDailyMetrics {
  /** Unique immutable record ID. */
  id: string;
  /** Schema version. */
  schemaVersion: 1;
  /** When first stored. */
  createdAt: string;
  /** When last recomputed. */
  updatedAt: string;
  /** Which version of the normalization pipeline produced this. */
  derivationVersion: string;

  athleteId: string;
  /** Local date (YYYY-MM-DD). */
  date: string;

  // ── Recovery metrics (unit-converted, not interpreted) ──────
  recoveryScore: number | null;
  hrvMs: number | null;
  restingHrBpm: number | null;
  spo2Pct: number | null;
  skinTempCelsius: number | null;
  respiratoryRate: number | null;

  // ── Sleep metrics (hours, no interpretation) ────────────────
  totalSleepHours: number | null;
  deepSleepHours: number | null;
  remSleepHours: number | null;
  lightSleepHours: number | null;
  awakeHours: number | null;
  sleepEfficiencyPct: number | null;
  sleepDebtHours: number | null;

  // ── Strain / activity (daily rollup) ────────────────────────
  dailyStrain: number | null;
  activeCaloriesKcal: number | null;
  totalCaloriesKj: number | null;

  // ── Workout rollup (counts and totals, not classified) ──────
  workoutCount: number;
  workoutMinutesTotal: number | null;
  workoutStrainTotal: number | null;
  grapplingSessionCount: number;
  workoutSportNames: string[];

  // ── Nutrition (deterministic, no interpretation) ──────────────
  /** Total calories consumed (kcal). Null if no nutrition data. */
  nutritionCalories: number | null;
  /** Protein in grams. */
  nutritionProteinGrams: number | null;
  /** Carbohydrates in grams. */
  nutritionCarbGrams: number | null;
  /** Fat in grams. */
  nutritionFatGrams: number | null;
  /**
   * Coverage level for nutrition data. Deterministic — not athlete-relative.
   *   'full'    — all macros present
   *   'partial' — some macros present
   *   'none'    — no nutrition data at all
   */
  nutritionCoverage: 'full' | 'partial' | 'none';

  // ── Completeness (deterministic, not athlete-dependent) ─────
  /** Which fields have non-null data. */
  presentFields: string[];
  /** Which expected fields are null. */
  missingFields: string[];
  /** Overall completeness. */
  completeness: NormalizationCompleteness;
  /** Hours since the source last provided this day's data. */
  sourceAgeHours: number | null;

  // ── Provenance ──────────────────────────────────────────────
  /** Which raw records this was derived from. */
  sourceRecordIds: string[];
  /** Structured provenance refs. */
  sourceRefs: SourceRef[];
  /** Source provider (e.g. 'whoop', 'apple_health'). */
  provider: string;
}
