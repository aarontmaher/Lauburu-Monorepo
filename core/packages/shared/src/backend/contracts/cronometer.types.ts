/**
 * Cronometer adapter contracts — shared types for the Cronometer
 * nutrition data provider boundary.
 *
 * States are explicit so the Coach, ai-context, and mobile UI can
 * all surface honest connection status without guessing.
 *
 * External blocker: Cronometer does not currently offer a public
 * OAuth or REST API for third-party apps. This contract is ready
 * for when access becomes available (API key, OAuth, CSV import,
 * or web bridge).
 */

export type CronometerConnectionStatus =
  | 'connected'        // Live API access, actively syncing
  | 'not_connected'    // No credentials configured
  | 'auth_required'    // Credentials missing or never set up
  | 'auth_expired'     // Was connected, token/session expired
  | 'unavailable'      // API unreachable or rate-limited
  | 'partial'          // Connected but only some data available
  | 'stale'            // Connected but last sync is old
  | 'error';           // Unexpected failure

export interface CronometerConnectionState {
  status: CronometerConnectionStatus;
  lastSyncAt: string | null;
  /** Human-readable reason for the current status. */
  reason: string | null;
  /** Whether the app has ever been authorized with Cronometer. */
  hasCredentials: boolean;
  /** What the user should do next. */
  actionRequired: string | null;
}

/** Cronometer nutrition domains with per-field availability. */
export const CRONOMETER_NUTRITION_DOMAINS = [
  'calories',
  'protein',
  'carbs',
  'fat',
  'fiber',
  'water',
  'sodium',
  'meal_timestamps',
  'body_mass',
] as const;

export type CronometerNutritionDomain = typeof CRONOMETER_NUTRITION_DOMAINS[number];

/** Per-domain coverage from a Cronometer sync. */
export interface CronometerDomainCoverage {
  domain: CronometerNutritionDomain;
  available: boolean;
  value: number | null;
  unit: string;
}

/** Raw Cronometer daily response — preserved as received. */
export interface CronometerDailyRaw {
  date: string;
  fetchedAt: string;
  /** How the data was obtained. */
  fetchMethod: 'api' | 'csv_import' | 'manual_bridge';
  caloriesKcal: number | null;
  proteinGrams: number | null;
  carbGrams: number | null;
  fatGrams: number | null;
  fiberGrams: number | null;
  sugarGrams: number | null;
  sodiumMg: number | null;
  waterMl: number | null;
  bodyMassKg: number | null;
  /** Meal timestamps if available (ISO strings). */
  mealTimestamps: string[];
  /** Which fields were present in the source. */
  presentFields: string[];
  /** Which expected fields were missing. */
  missingFields: string[];
}

/**
 * Cronometer provider adapter interface.
 * The concrete implementation depends on available access method.
 */
export interface CronometerAdapter {
  /** Check current connection status. */
  checkConnection(): Promise<CronometerConnectionState>;
  /** Fetch daily nutrition for a date. Returns null if not connected. */
  fetchDaily(date: string): Promise<CronometerDailyRaw | null>;
  /** Disconnect / revoke credentials if supported. */
  disconnect(): Promise<void>;
}

/**
 * Build domain coverage from a Cronometer daily response.
 */
export function buildCronometerCoverage(raw: CronometerDailyRaw): CronometerDomainCoverage[] {
  return [
    { domain: 'calories', available: raw.caloriesKcal != null, value: raw.caloriesKcal, unit: 'kcal' },
    { domain: 'protein', available: raw.proteinGrams != null, value: raw.proteinGrams, unit: 'g' },
    { domain: 'carbs', available: raw.carbGrams != null, value: raw.carbGrams, unit: 'g' },
    { domain: 'fat', available: raw.fatGrams != null, value: raw.fatGrams, unit: 'g' },
    { domain: 'fiber', available: raw.fiberGrams != null, value: raw.fiberGrams, unit: 'g' },
    { domain: 'water', available: raw.waterMl != null, value: raw.waterMl, unit: 'ml' },
    { domain: 'sodium', available: raw.sodiumMg != null, value: raw.sodiumMg, unit: 'mg' },
    { domain: 'meal_timestamps', available: raw.mealTimestamps.length > 0, value: raw.mealTimestamps.length, unit: 'meals' },
    { domain: 'body_mass', available: raw.bodyMassKg != null, value: raw.bodyMassKg, unit: 'kg' },
  ];
}

/**
 * Default connection state — returned when no credentials exist.
 */
export function getDefaultCronometerState(): CronometerConnectionState {
  return {
    status: 'not_connected',
    lastSyncAt: null,
    reason: 'Cronometer does not currently offer a public API for third-party apps.',
    hasCredentials: false,
    actionRequired: 'Use manual nutrition entry, barcode scanning, or AI photo logging as alternatives.',
  };
}
