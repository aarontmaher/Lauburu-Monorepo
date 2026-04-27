/**
 * Nutrition raw ingestion — converts NutritionRecord inputs
 * (from Cronometer export, mobile manual entry, barcode scans,
 * or AI photo estimates) into typed NutritionDailyMetricsRaw
 * records for Layer 1 storage.
 *
 * Non-negotiable: unconfirmed barcode/photo proposals are stored
 * as raw evidence but NEVER enter normalized nutrition.
 *
 * Pure function. No network calls. No interpretation.
 */

import type { NutritionDailyMetricsRaw } from '../../contracts/nutrition-raw.types';

/** Input shape from mobile or Cronometer export. */
export interface NutritionIngestPayload {
  date: string;
  source?: 'cronometer' | 'manual' | 'barcode' | 'ai_photo' | 'mixed';
  /** Source state for provenance. */
  sourceState?: 'live' | 'manual' | 'estimated' | 'mixed';
  /** Whether this entry has been confirmed by the user. Defaults to true for manual. */
  confirmed?: boolean;
  calories_kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fibre_g?: number | null;
  sugar_g?: number | null;
  sodium_mg?: number | null;
  water_ml?: number | null;
  updated_at?: string | null;
  /** Evidence item IDs that contributed (for audit). */
  evidenceIds?: string[];
  /** Source dependencies for provenance tracking. */
  sourceDependencies?: string[];
  /** Which fields are missing. */
  missingFields?: string[];
}

/**
 * Check whether a nutrition ingest payload is allowed to enter
 * normalized nutrition. Unconfirmed barcode/photo proposals are blocked.
 * Manual and cronometer entries are implicitly confirmed.
 */
export function isNutritionIngestConfirmed(payload: NutritionIngestPayload): boolean {
  // Manual and cronometer are implicitly confirmed
  if (!payload.source || payload.source === 'manual' || payload.source === 'cronometer') {
    return true;
  }
  // Barcode and AI photo require explicit confirmation
  return payload.confirmed === true;
}

let _idCounter = 0;
function generateId(date: string): string {
  return `nutr_raw_${date}_${Date.now()}_${++_idCounter}`;
}

/** Ingest a single nutrition record. */
export function ingestNutritionDay(
  payload: NutritionIngestPayload,
  athleteId: string,
): NutritionDailyMetricsRaw {
  const now = new Date().toISOString();
  const source = payload.source ?? 'manual';

  // Compute missing macro fields
  const missingFields: string[] = payload.missingFields ?? [];
  if (missingFields.length === 0) {
    if (payload.calories_kcal == null) missingFields.push('calories');
    if (payload.protein_g == null) missingFields.push('protein');
    if (payload.carbs_g == null) missingFields.push('carbs');
    if (payload.fat_g == null) missingFields.push('fat');
  }

  return {
    id: generateId(payload.date),
    schemaVersion: 1,
    createdAt: now,
    updatedAt: now,
    athleteId,
    date: payload.date,
    source,
    sourceState: payload.sourceState ?? (source === 'cronometer' ? 'live' : 'manual'),
    confirmed: isNutritionIngestConfirmed(payload),
    caloriesKcal: payload.calories_kcal ?? null,
    proteinGrams: payload.protein_g ?? null,
    carbGrams: payload.carbs_g ?? null,
    fatGrams: payload.fat_g ?? null,
    fibreGrams: payload.fibre_g ?? null,
    sugarGrams: payload.sugar_g ?? null,
    sodiumMg: payload.sodium_mg ?? null,
    waterMl: payload.water_ml ?? null,
    sourceUpdatedAt: payload.updated_at ?? null,
    missingFields,
    sourceDependencies: payload.sourceDependencies ?? [source],
    evidenceIds: payload.evidenceIds ?? [],
    sourceRecordIds: [],
  };
}

/** Ingest a batch of nutrition records. */
export function ingestNutritionBatch(
  payloads: NutritionIngestPayload[],
  athleteId: string,
): NutritionDailyMetricsRaw[] {
  return payloads
    .map((p) => ingestNutritionDay(p, athleteId))
    .sort((a, b) => a.date.localeCompare(b.date));
}
