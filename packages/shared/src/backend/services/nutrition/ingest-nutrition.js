"use strict";
/**
 * Nutrition raw ingestion — converts NutritionRecord inputs
 * (from Cronometer export, mobile manual entry, or barcode scans)
 * into typed NutritionDailyMetricsRaw records for Layer 1 storage.
 *
 * Pure function. No network calls. No interpretation.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ingestNutritionDay = ingestNutritionDay;
exports.ingestNutritionBatch = ingestNutritionBatch;
let _idCounter = 0;
function generateId(date) {
    return `nutr_raw_${date}_${Date.now()}_${++_idCounter}`;
}
/** Ingest a single nutrition record. */
function ingestNutritionDay(payload, athleteId) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _j, _k;
    const now = new Date().toISOString();
    return {
        id: generateId(payload.date),
        schemaVersion: 1,
        createdAt: now,
        updatedAt: now,
        athleteId,
        date: payload.date,
        source: (_a = payload.source) !== null && _a !== void 0 ? _a : 'manual',
        caloriesKcal: (_b = payload.calories_kcal) !== null && _b !== void 0 ? _b : null,
        proteinGrams: (_c = payload.protein_g) !== null && _c !== void 0 ? _c : null,
        carbGrams: (_d = payload.carbs_g) !== null && _d !== void 0 ? _d : null,
        fatGrams: (_e = payload.fat_g) !== null && _e !== void 0 ? _e : null,
        fibreGrams: (_f = payload.fibre_g) !== null && _f !== void 0 ? _f : null,
        sugarGrams: (_g = payload.sugar_g) !== null && _g !== void 0 ? _g : null,
        sodiumMg: (_h = payload.sodium_mg) !== null && _h !== void 0 ? _h : null,
        waterMl: (_j = payload.water_ml) !== null && _j !== void 0 ? _j : null,
        sourceUpdatedAt: (_k = payload.updated_at) !== null && _k !== void 0 ? _k : null,
    };
}
/** Ingest a batch of nutrition records. */
function ingestNutritionBatch(payloads, athleteId) {
    return payloads
        .map((p) => ingestNutritionDay(p, athleteId))
        .sort((a, b) => a.date.localeCompare(b.date));
}
