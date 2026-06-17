"use strict";
/**
 * Merge nutrition data into an existing NormalizedDailyMetrics record.
 *
 * Deterministic. No interpretation. No coaching conclusions.
 * Coverage is computed from which macros are present.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.applyNutritionToNormalized = applyNutritionToNormalized;
/**
 * Apply nutrition data to an existing normalized record.
 * Returns a new record with nutrition fields populated.
 * Does NOT modify the input — returns a copy.
 */
function applyNutritionToNormalized(normalized, nutrition) {
    const hasCalories = nutrition.caloriesKcal != null;
    const hasProtein = nutrition.proteinGrams != null;
    const hasCarbs = nutrition.carbGrams != null;
    const hasFat = nutrition.fatGrams != null;
    const macroCount = [hasCalories, hasProtein, hasCarbs, hasFat].filter(Boolean).length;
    const coverage = macroCount === 4 ? 'full' : macroCount > 0 ? 'partial' : 'none';
    return Object.assign(Object.assign({}, normalized), { nutritionCalories: nutrition.caloriesKcal, nutritionProteinGrams: nutrition.proteinGrams, nutritionCarbGrams: nutrition.carbGrams, nutritionFatGrams: nutrition.fatGrams, nutritionCoverage: coverage, updatedAt: new Date().toISOString() });
}
