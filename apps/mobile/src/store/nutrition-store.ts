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
   * Partial update to today's record. Creates a new record on first call
   * if none exists. `source` defaults to 'manual' when a new record is
   * created. Stamps `updated_at` automatically.
   */
  updateToday: (
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

  setTargets: (targets) => set({ targets }),

  clearToday: () => set({ today: null }),
}));
