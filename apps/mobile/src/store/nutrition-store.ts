/**
 * Nutrition store — first real mobile nutrition layer, with local
 * persistence so today's manual entries + barcode scans + daily targets
 * survive app kill.
 *
 * Sources today: manual entry + barcode (Open Food Facts). The shape
 * matches `NutritionRecord` from `@lauburu/shared/types/nutrition` exactly
 * so a future Cronometer API swap or a Supabase cross-device sync
 * layer can land as a drop-in replacement behind the same store surface.
 *
 * Persistence: backed by `secureStorage` from `./secure-storage`, which
 * wraps `expo-secure-store` (iOS Keychain / Android Keystore) with an
 * in-memory fallback for Expo Go. Same adapter the auth session already
 * uses. Two keys: `nutrition_today_v1` (JSON NutritionRecord, stale
 * records from previous days are dropped on hydrate) and
 * `nutrition_targets_v1` (JSON NutritionTargets).
 *
 * Cross-device sync via Supabase is a deliberate follow-up — the
 * existing surface + v1 keys give a clean extension point where a
 * background sync can read/write without touching any UI.
 */
import { create } from 'zustand';
import type { NutritionRecord, NutritionTargets, NutritionSource } from '@lauburu/shared';
import { secureStorage } from './secure-storage';

const STORAGE_KEY_TODAY = 'nutrition_today_v1';
const STORAGE_KEY_TARGETS = 'nutrition_targets_v1';

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Fire-and-forget persistence helpers. These swallow their own errors
 * and log nothing — a failed secureStorage write must never crash the
 * UI or surface an error banner, because the store is the primary
 * source of truth in memory and the user just entered data they expect
 * to see. On the next hydrate cycle, a missing persisted record simply
 * means "start fresh", not "the app is broken".
 */
async function persistTodaySafely(record: NutritionRecord | null): Promise<void> {
  try {
    if (record == null) {
      await secureStorage.removeItem(STORAGE_KEY_TODAY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY_TODAY, JSON.stringify(record));
  } catch {
    // Intentionally swallowed — see helper doc comment.
  }
}

async function persistTargetsSafely(targets: NutritionTargets | null): Promise<void> {
  try {
    if (targets == null) {
      await secureStorage.removeItem(STORAGE_KEY_TARGETS);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY_TARGETS, JSON.stringify(targets));
  } catch {
    // Intentionally swallowed — see helper doc comment.
  }
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
  /** True once the first hydrate attempt has completed (success OR empty). */
  hydrated: boolean;

  /**
   * Load persisted nutrition state from secureStorage. Should be called
   * once on app launch from `_layout.tsx` before the rest of the UI
   * mounts the Health tab. Date-aware: if the persisted today record
   * is from a previous date, it's discarded and the user starts fresh
   * for the new day. Targets have no date and are always restored.
   * Error-resilient — a failed load simply leaves the state empty.
   */
  hydrate: () => Promise<void>;

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

export const useNutritionStore = create<NutritionState>((set, get) => ({
  today: null,
  targets: null,
  loading: false,
  error: null,
  hydrated: false,

  hydrate: async () => {
    try {
      const [rawToday, rawTargets] = await Promise.all([
        secureStorage.getItem(STORAGE_KEY_TODAY),
        secureStorage.getItem(STORAGE_KEY_TARGETS),
      ]);

      let today: NutritionRecord | null = null;
      if (rawToday) {
        try {
          const parsed = JSON.parse(rawToday) as NutritionRecord;
          // Date-aware: drop stale records from previous days so the
          // user starts fresh for the new day.
          if (parsed && parsed.date === todayIsoDate()) {
            today = parsed;
          } else {
            // Clean up stale data eagerly so the keychain doesn't
            // accumulate old-day records forever.
            void secureStorage.removeItem(STORAGE_KEY_TODAY);
          }
        } catch {
          // Corrupt JSON — drop it.
          void secureStorage.removeItem(STORAGE_KEY_TODAY);
        }
      }

      let targets: NutritionTargets | null = null;
      if (rawTargets) {
        try {
          targets = JSON.parse(rawTargets) as NutritionTargets;
        } catch {
          void secureStorage.removeItem(STORAGE_KEY_TARGETS);
        }
      }

      set({ today, targets, hydrated: true, error: null });
    } catch {
      // Any unexpected failure — leave state empty, mark hydrated so
      // the UI stops waiting.
      set({ hydrated: true });
    }
  },

  updateToday: (partial, source) => {
    let nextRecord: NutritionRecord | null = null;
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
      nextRecord = next;
      return { today: next, error: null };
    });
    // Fire-and-forget persist after the state update — failures are
    // silently swallowed and the in-memory store remains authoritative.
    void persistTodaySafely(nextRecord);
  },

  addToToday: (partial, source) => {
    let nextRecord: NutritionRecord | null = null;
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
      nextRecord = next;
      return { today: next, error: null };
    });
    void persistTodaySafely(nextRecord);
  },

  setTargets: (targets) => {
    set({ targets });
    void persistTargetsSafely(targets);
  },

  clearToday: () => {
    set({ today: null });
    void persistTodaySafely(null);
  },
}));
