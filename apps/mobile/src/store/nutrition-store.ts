/**
 * Nutrition store — first real mobile nutrition layer.
 *
 * Source today: manual entry only. The shape matches `NutritionRecord`
 * from `@lauburu/shared/types/nutrition` exactly so a future swap from
 * manual entry to a live Cronometer API client is a drop-in replacement
 * behind the same store surface.
 *
 * Persistence note: this store is in-memory Zustand, matching the
 * existing whoop-store / machine-store pattern in the app. Backend
 * persistence of nutrition records can land as a follow-up batch
 * without changing the store's surface area (same hooks, same shape).
 */
import { create } from 'zustand';
import type { NutritionRecord, NutritionTargets, NutritionSource } from '@lauburu/shared';

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

interface NutritionState {
  /** Today's nutrition record, or null when nothing has been logged. */
  today: NutritionRecord | null;
  /** Daily macro / calorie targets. Optional — renders fine without. */
  targets: NutritionTargets | null;
  /** True while any async operation is in flight (future-ready for API). */
  loading: boolean;
  /** Last error from an operation, if any. */
  error: string | null;

  /**
   * Partial update to today's record — REPLACE semantics. Values in
   * `partial` overwrite existing fields; missing fields are preserved.
   * Creates a new record on first call if none exists. `source` defaults
   * to 'manual' when a new record is created. Stamps `updated_at`
   * automatically.
   *
   * Use for "this is my total so far today" flows (manual entry).
   */
  updateToday: (
    partial: Partial<Omit<NutritionRecord, 'date' | 'source' | 'updated_at'>>,
    source?: NutritionSource,
  ) => void;

  /**
   * Additive update to today's record — ADD semantics. Each numeric
   * field in `partial` is added to the existing value (treating null
   * as 0). String/non-numeric fields follow the last-write semantics.
   * Creates a new record on first call if none exists.
   *
   * Use for "I just ate this, add it to today's total" flows — barcode
   * lookups, future AI photo estimates, imported meal entries.
   */
  addToToday: (
    partial: Partial<Omit<NutritionRecord, 'date' | 'source' | 'updated_at'>>,
    source?: NutritionSource,
  ) => void;

  /** Replace daily targets. Pass null to clear. */
  setTargets: (targets: NutritionTargets | null) => void;

  /** Wipe today's record. */
  clearToday: () => void;
}

export const useNutritionStore = create<NutritionState>((set) => ({
  today: null,
  targets: null,
  loading: false,
  error: null,

  updateToday: (partial, source) =>
    set((state) => {
      const now = new Date().toISOString();
      const base: NutritionRecord =
        state.today && state.today.date === todayIsoDate()
          ? state.today
          : {
              date: todayIsoDate(),
              source: source ?? 'manual',
              updated_at: now,
            };
      const next: NutritionRecord = {
        ...base,
        ...partial,
        source: source ?? base.source,
        updated_at: now,
      };
      return { today: next, error: null };
    }),

  addToToday: (partial, source) =>
    set((state) => {
      const now = new Date().toISOString();
      const base: NutritionRecord =
        state.today && state.today.date === todayIsoDate()
          ? state.today
          : {
              date: todayIsoDate(),
              source: source ?? 'manual',
              updated_at: now,
            };
      // Add each numeric field in `partial` to the existing value,
      // treating null/undefined as 0. Round to 1 decimal to keep the
      // store values clean (barcode lookups often come back with
      // arbitrary-precision floats from per-100g scaling).
      const addNum = (a: number | undefined, b: number | undefined): number | undefined => {
        if (a == null && b == null) return undefined;
        const sum = (a ?? 0) + (b ?? 0);
        return Math.round(sum * 10) / 10;
      };
      const next: NutritionRecord = {
        ...base,
        calories_kcal: addNum(base.calories_kcal, partial.calories_kcal),
        protein_g: addNum(base.protein_g, partial.protein_g),
        carbs_g: addNum(base.carbs_g, partial.carbs_g),
        fat_g: addNum(base.fat_g, partial.fat_g),
        fibre_g: addNum(base.fibre_g, partial.fibre_g),
        sugar_g: addNum(base.sugar_g, partial.sugar_g),
        sodium_mg: addNum(base.sodium_mg, partial.sodium_mg),
        water_ml: addNum(base.water_ml, partial.water_ml),
        source: source ?? base.source,
        updated_at: now,
      };
      return { today: next, error: null };
    }),

  setTargets: (targets) => set({ targets }),

  clearToday: () => set({ today: null }),
}));
