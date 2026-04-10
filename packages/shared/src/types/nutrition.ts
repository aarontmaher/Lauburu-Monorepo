/**
 * Nutrition types — first-slice scaffolding for Cronometer (and future
 * FatSecret / MyFitnessPal / manual) integrations.
 *
 * Status as of 2026-04-10: NO live ingestion. These types exist so the
 * mobile app has a stable contract for the next batch to fill in. Nothing
 * in the current coaching pipeline reads from them yet, so adding fields
 * or flipping sources later is additive and safe.
 */

/**
 * Where nutrition data came from. Explicit provenance mirrors the
 * WorkoutSource pattern in training.ts — coaching decisions need to
 * know if a number was hand-entered vs pulled from a tracked source.
 */
export type NutritionSource =
  | 'manual' // User typed it into the app
  | 'cronometer' // Pulled from Cronometer (future)
  | 'myfitnesspal' // Pulled from MyFitnessPal (future)
  | 'fatsecret' // Pulled from FatSecret (future)
  | 'imported'; // Generic file import (future)

export const NUTRITION_SOURCE_LABELS: Record<NutritionSource, string> = {
  manual: 'Manual',
  cronometer: 'Cronometer',
  myfitnesspal: 'MyFitnessPal',
  fatsecret: 'FatSecret',
  imported: 'Imported',
};

/**
 * Whole-day nutrition summary. Every field is optional because different
 * sources expose different subsets and the user may only care about a
 * subset. No field is synthesised.
 *
 * This shape intentionally mirrors what Cronometer's day summary exposes
 * so the future integration is a near-1:1 write path.
 */
export interface NutritionRecord {
  /** Local date (YYYY-MM-DD). */
  date: string;
  /** Total calories consumed (kcal). */
  calories_kcal?: number;
  /** Total protein (grams). */
  protein_g?: number;
  /** Total carbs (grams). */
  carbs_g?: number;
  /** Total fat (grams). */
  fat_g?: number;
  /** Total fibre (grams). */
  fibre_g?: number;
  /** Total sugar (grams). */
  sugar_g?: number;
  /** Total sodium (mg). */
  sodium_mg?: number;
  /** Total water intake (ml). */
  water_ml?: number;
  /** Provenance flag — defaults to 'manual' at the call site. */
  source: NutritionSource;
  /** When the record was last updated (client-local ISO). */
  updated_at: string;
}

/**
 * Thin nutrition target spec — calories + macros goals per day.
 * Used by a future coaching layer to interpret intake vs goal.
 */
export interface NutritionTargets {
  calories_kcal?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
}
