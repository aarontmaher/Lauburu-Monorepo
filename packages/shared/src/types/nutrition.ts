/**
 * Nutrition types — first-slice scaffolding for Cronometer (and future
 * FatSecret / MyFitnessPal / manual / AI) integrations.
 *
 * ARCHITECTURE
 *
 * Explicit layering — each layer has one job, and they don't compete:
 *
 *   Cronometer  → canonical structured nutrition source of truth.
 *                 When live, this is the authoritative daily record.
 *                 The app does NOT try to outgrow Cronometer — it
 *                 builds on top of it.
 *
 *   Manual      → the first usable in-app layer, shipped today.
 *                 Fast fallback entry when the user is away from
 *                 Cronometer or just wants to log one number quickly.
 *
 *   AI estimate → future convenience layer. Photo-based macro estimate,
 *                 voice-to-macros, barcode lookups, meal description
 *                 parsing, etc. Always marked as 'ai_estimate' so the
 *                 coaching layer can weight it lower than manual or
 *                 cronometer data. NEVER the source of truth on its own.
 *
 *   AI corrected → an AI estimate the user has reviewed/edited. Higher
 *                 trust than raw AI but still distinct from manual so
 *                 provenance is auditable.
 *
 *   Targets     → the coaching usefulness layer on top of any of the
 *                 above. Lives in NutritionTargets, unrelated to source.
 *
 * Status as of 2026-04-10: manual entry is live via the mobile
 * nutrition-store; all other sources are scaffolded but not wired.
 * The type union above is the stable contract — adding live paths
 * later (Cronometer API client, AI estimator, file import, etc.)
 * is additive and does not touch the NutritionRecord shape or any
 * UI that already reads through useNutritionStore.
 */

/**
 * Where nutrition data came from. Explicit provenance mirrors the
 * WorkoutSource pattern in training.ts — coaching decisions need to
 * know if a number was hand-entered vs pulled from a tracked source
 * vs estimated by AI vs corrected by the user after an AI estimate.
 *
 * Ordered by "trust for coaching", highest first:
 *   cronometer    → tracked, structured, canonical
 *   manual        → user-asserted, lower freshness risk
 *   ai_corrected  → AI estimate the user reviewed and accepted/edited
 *   imported      → generic file/export import
 *   myfitnesspal  → tracked third party
 *   fatsecret     → tracked third party
 *   ai_estimate   → raw AI estimate, lowest auto-trust
 */
export type NutritionSource =
  | 'cronometer' // Pulled from Cronometer (future, canonical target)
  | 'manual' // User typed it into the app (today's default)
  | 'ai_corrected' // AI estimate the user reviewed + accepted/edited (future)
  | 'imported' // Generic file / export import (future)
  | 'myfitnesspal' // Pulled from MyFitnessPal (future)
  | 'fatsecret' // Pulled from FatSecret (future)
  | 'ai_estimate'; // Raw AI estimate (photo, voice, parsed description) (future)

export const NUTRITION_SOURCE_LABELS: Record<NutritionSource, string> = {
  cronometer: 'Cronometer',
  manual: 'Manual',
  ai_corrected: 'AI (corrected)',
  imported: 'Imported',
  myfitnesspal: 'MyFitnessPal',
  fatsecret: 'FatSecret',
  ai_estimate: 'AI estimate',
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
