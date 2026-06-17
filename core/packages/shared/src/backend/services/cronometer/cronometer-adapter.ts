/**
 * Cronometer adapter — backend-side provider boundary.
 *
 * Implements CronometerAdapter with environment-aware connection checking.
 * If CRONOMETER_API_KEY or CRONOMETER_CLIENT_ID are set, attempts real
 * connection. Otherwise returns truthful not_connected status.
 *
 * External blocker: Cronometer does not currently offer a public
 * third-party API. When access becomes available, only the fetchDaily()
 * implementation needs to change. Everything else (normalization, ingest,
 * source-health, Coach consumption) is already wired.
 */

import type {
  CronometerAdapter,
  CronometerConnectionState,
  CronometerDailyRaw,
} from '../../contracts/cronometer.types';
import { getDefaultCronometerState } from '../../contracts/cronometer.types';

/**
 * Check if Cronometer credentials are available from environment.
 */
function hasCredentials(): boolean {
  return !!(
    (typeof process !== 'undefined' && process.env) &&
    (process.env.CRONOMETER_API_KEY || process.env.CRONOMETER_CLIENT_ID)
  );
}

/**
 * Concrete Cronometer adapter.
 * Returns honest connection state based on actual credential availability.
 */
export class DefaultCronometerAdapter implements CronometerAdapter {
  async checkConnection(): Promise<CronometerConnectionState> {
    if (!hasCredentials()) {
      return getDefaultCronometerState();
    }

    // Credentials exist — attempt connection check.
    // When the Cronometer API becomes available, this is where the
    // real health-check call goes.
    return {
      status: 'auth_required',
      lastSyncAt: null,
      reason: 'Cronometer credentials found but API access is not yet available.',
      hasCredentials: true,
      actionRequired: 'Cronometer API access pending. Credentials are configured but the API endpoint is not yet operational.',
    };
  }

  async fetchDaily(date: string): Promise<CronometerDailyRaw | null> {
    if (!hasCredentials()) {
      return null;
    }

    // When real API access exists, this fetches the day's nutrition.
    // For now, return null — the ingest route handles this gracefully.
    return null;
  }

  async disconnect(): Promise<void> {
    // No-op until real credentials are stored.
  }
}

/**
 * Normalize a Cronometer daily response into a NutritionIngestPayload.
 * Pure function — converts raw Cronometer shape into the standard ingest shape.
 */
export function normalizeCronometerDaily(raw: CronometerDailyRaw): {
  date: string;
  source: 'cronometer';
  sourceState: 'live';
  confirmed: true;
  calories_kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fibre_g: number | null;
  sugar_g: number | null;
  sodium_mg: number | null;
  water_ml: number | null;
  missingFields: string[];
  sourceDependencies: string[];
} {
  return {
    date: raw.date,
    source: 'cronometer',
    sourceState: 'live',
    confirmed: true, // Cronometer data is always implicitly confirmed
    calories_kcal: raw.caloriesKcal,
    protein_g: raw.proteinGrams,
    carbs_g: raw.carbGrams,
    fat_g: raw.fatGrams,
    fibre_g: raw.fiberGrams,
    sugar_g: raw.sugarGrams,
    sodium_mg: raw.sodiumMg,
    water_ml: raw.waterMl,
    missingFields: raw.missingFields,
    sourceDependencies: ['cronometer'],
  };
}
