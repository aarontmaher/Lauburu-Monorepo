/**
 * Raw nutrition ingest types — Layer 1 (raw source facts).
 *
 * Accepts nutrition records from Cronometer export, manual entry,
 * or barcode scan. Preserved as received. No interpretation.
 */

import type { SourceRef } from './whoop-raw.types';

/** A single raw nutrition daily record. */
export interface NutritionDailyMetricsRaw {
  id: string;
  schemaVersion: 1;
  createdAt: string;
  updatedAt: string;
  athleteId: string;
  /** Local date (YYYY-MM-DD). */
  date: string;
  /** Source of the nutrition data. */
  source: 'cronometer' | 'manual' | 'barcode' | 'ai_photo' | 'mixed';
  /** Source state: live (API), manual (user entry), estimated (AI), mixed. */
  sourceState?: 'live' | 'manual' | 'estimated' | 'mixed';
  /** Whether the user confirmed this entry. Unconfirmed entries are proposals only. */
  confirmed?: boolean;
  /** Total calories consumed (kcal). */
  caloriesKcal: number | null;
  /** Total protein (grams). */
  proteinGrams: number | null;
  /** Total carbohydrates (grams). */
  carbGrams: number | null;
  /** Total fat (grams). */
  fatGrams: number | null;
  /** Total fibre (grams). */
  fibreGrams: number | null;
  /** Total sugar (grams). */
  sugarGrams: number | null;
  /** Total sodium (mg). */
  sodiumMg: number | null;
  /** Water intake (ml). */
  waterMl: number | null;
  /** When this record was last updated at source. */
  sourceUpdatedAt: string | null;

  // ── Provenance ──────────────────────────────────────────────
  /** Which macro fields are missing from this record. */
  missingFields?: string[];
  /** What upstream sources contributed (e.g. ['cronometer'], ['manual', 'barcode']). */
  sourceDependencies?: string[];
  /** IDs of evidence items that contributed (barcode scans, photo proposals). */
  evidenceIds?: string[];
  /** IDs of other raw records merged into this one. */
  sourceRecordIds?: string[];
}
