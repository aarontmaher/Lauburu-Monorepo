/**
 * AI nutrition sync — posts mobile nutrition data to the canonical
 * backend AI ingestion path after each nutrition update.
 *
 * Fire-and-forget: failures are logged but never block nutrition entry.
 * Preserves source, sourceState, confirmed, missingFields, sourceDependencies.
 */

import type { NutritionRecord } from '@lauburu/shared';
import { AI_INTERNAL_BASE, AI_INTERNAL_TOKEN } from './ai-backend-config';

const TIMEOUT_MS = 8000;

/**
 * Post a NutritionRecord to the backend AI nutrition ingest.
 * Returns true on success, false on failure. Never throws.
 */
export async function syncNutritionToAiBackend(
  athleteId: string,
  record: NutritionRecord,
  opts?: {
    source?: string;
    sourceState?: string;
    confirmed?: boolean;
    evidenceIds?: string[];
    sourceDependencies?: string[];
  },
): Promise<boolean> {
  if (!AI_INTERNAL_TOKEN || !record.date) return false;

  const source = opts?.source ?? (record as any).source ?? 'manual';

  // Compute missingFields from the record
  const missingFields: string[] = [];
  if (record.calories_kcal == null) missingFields.push('calories');
  if (record.protein_g == null) missingFields.push('protein');
  if (record.carbs_g == null) missingFields.push('carbs');
  if (record.fat_g == null) missingFields.push('fat');

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const resp = await fetch(`${AI_INTERNAL_BASE}/ingest/nutrition/daily`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'x-internal-token': AI_INTERNAL_TOKEN,
      },
      body: JSON.stringify({
        athleteId,
        day: {
          date: record.date,
          source,
          sourceState: opts?.sourceState ?? (source === 'cronometer' ? 'live' : 'manual'),
          confirmed: opts?.confirmed ?? (source === 'manual' || source === 'cronometer'),
          calories_kcal: record.calories_kcal ?? null,
          protein_g: record.protein_g ?? null,
          carbs_g: record.carbs_g ?? null,
          fat_g: record.fat_g ?? null,
          fibre_g: record.fibre_g ?? null,
          sugar_g: record.sugar_g ?? null,
          sodium_mg: record.sodium_mg ?? null,
          water_ml: record.water_ml ?? null,
          body_weight_kg: (record as any).body_weight_kg ?? null,
          missingFields,
          sourceDependencies: opts?.sourceDependencies ?? [source],
          evidenceIds: opts?.evidenceIds ?? [],
        },
      }),
    });

    clearTimeout(timer);
    return resp.ok;
  } catch {
    return false;
  }
}
