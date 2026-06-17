/**
 * Merge nutrition data into an existing NormalizedDailyMetrics record.
 *
 * Deterministic. No interpretation. No coaching conclusions.
 * Coverage is computed from which macros are present.
 */

import type { NutritionDailyMetricsRaw } from '../../contracts/nutrition-raw.types';
import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';

/**
 * Apply nutrition data to an existing normalized record.
 * Returns a new record with nutrition fields populated.
 * Does NOT modify the input — returns a copy.
 */
export function applyNutritionToNormalized(
  normalized: NormalizedDailyMetrics,
  nutrition: NutritionDailyMetricsRaw,
): NormalizedDailyMetrics {
  const hasCalories = nutrition.caloriesKcal != null;
  const hasProtein = nutrition.proteinGrams != null;
  const hasCarbs = nutrition.carbGrams != null;
  const hasFat = nutrition.fatGrams != null;

  const macroCount = [hasCalories, hasProtein, hasCarbs, hasFat].filter(Boolean).length;
  const coverage: NormalizedDailyMetrics['nutritionCoverage'] =
    macroCount === 4 ? 'full' : macroCount > 0 ? 'partial' : 'none';

  return {
    ...normalized,
    nutritionCalories: nutrition.caloriesKcal,
    nutritionProteinGrams: nutrition.proteinGrams,
    nutritionCarbGrams: nutrition.carbGrams,
    nutritionFatGrams: nutrition.fatGrams,
    nutritionCoverage: coverage,
    updatedAt: new Date().toISOString(),
  };
}
