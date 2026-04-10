/**
 * Nutrition types — first-slice scaffolding for Cronometer (and future
 * FatSecret / MyFitnessPal / manual / AI) integrations.
 *
 * ARCHITECTURE
 *
 * Explicit layering — each layer has one job, and they don't compete.
 * Order matters: higher layers = higher accuracy / higher trust.
 *
 *   Cronometer      → canonical structured nutrition source of truth.
 *                     When live, this is the authoritative daily record.
 *                     The app does NOT try to outgrow Cronometer — it
 *                     builds on top of it.
 *
 *   Manual          → the first usable in-app layer, shipped today.
 *                     Fast fallback entry when the user is away from
 *                     Cronometer or just wants to log one number quickly.
 *
 *   Label scan      → OCR read straight off a package's nutrition label.
 *                     As accurate as the package print itself for
 *                     packaged foods. Ranks ABOVE photo AI for packaged
 *                     items — photo AI is not the default truth source.
 *
 *   Barcode         → barcode → product database lookup. Accurate for
 *                     well-known products, constrained by the database.
 *                     Ranks ABOVE photo AI for packaged items.
 *
 *   AI corrected    → an AI estimate the user has reviewed/edited. Higher
 *                     trust than raw AI but still distinct from manual so
 *                     provenance is auditable.
 *
 *   AI estimate     → convenience layer for unpackaged / restaurant /
 *                     ambiguous meals. Photo-based macro estimate,
 *                     voice-to-macros, meal description parsing.
 *                     Always marked as 'ai_estimate' so coaching can
 *                     weight it lowest. NEVER the sole source of truth.
 *
 *   Targets         → the coaching usefulness layer on top of any of the
 *                     above. Lives in NutritionTargets, unrelated to source.
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
 * know if a number was hand-entered vs read off an actual package
 * vs estimated by AI vs corrected by the user after an AI estimate.
 *
 * ACCURACY HIERARCHY (highest trust first):
 *
 *   cronometer           → tracked, structured, canonical source of truth
 *   manual               → user-asserted, usually deliberate
 *   nutrition_label_scan → OCR read straight off the package label.
 *                          As accurate as the package print itself for
 *                          packaged foods. Preferred over photo AI for
 *                          anything with a real nutrition label.
 *   barcode              → barcode → product database lookup. Accurate
 *                          for well-known products, only as current as
 *                          the database. Preferred over photo AI.
 *   ai_corrected         → AI estimate the user reviewed and accepted/
 *                          edited. Provenance preserved so coaching can
 *                          still weight it lower than direct sources.
 *   imported             → generic file / export import
 *   myfitnesspal         → tracked third party
 *   fatsecret            → tracked third party
 *   ai_estimate          → raw AI estimate (photo, voice, meal description
 *                          parsing). Lowest auto-trust. NEVER the sole
 *                          source of truth — always a convenience layer.
 *
 * Key product rule: label scan and barcode ALWAYS rank above photo AI
 * in the accuracy hierarchy for packaged foods. Photo AI is a fallback
 * convenience layer for unpackaged / restaurant / ambiguous meals only.
 */
export type NutritionSource =
  | 'cronometer' // Pulled from Cronometer (future, canonical target)
  | 'manual' // User typed it into the app (today's default)
  | 'nutrition_label_scan' // OCR from a real package label (future)
  | 'barcode' // Barcode lookup against a product database (future)
  | 'ai_corrected' // AI estimate the user reviewed + accepted/edited (future)
  | 'imported' // Generic file / export import (future)
  | 'myfitnesspal' // Pulled from MyFitnessPal (future)
  | 'fatsecret' // Pulled from FatSecret (future)
  | 'ai_estimate'; // Raw AI estimate (photo, voice, description) (future)

export const NUTRITION_SOURCE_LABELS: Record<NutritionSource, string> = {
  cronometer: 'Cronometer',
  manual: 'Manual',
  nutrition_label_scan: 'Label scan',
  barcode: 'Barcode',
  ai_corrected: 'AI (corrected)',
  imported: 'Imported',
  myfitnesspal: 'MyFitnessPal',
  fatsecret: 'FatSecret',
  ai_estimate: 'AI photo',
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
