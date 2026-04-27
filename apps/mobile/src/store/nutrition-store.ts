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
import { syncNutritionToAiBackend } from '../services/ai-nutrition-sync';
import { useAuthStore } from './auth-store';
import type { OpenFoodFactsProduct } from '../services/openfoodfacts';

const STORAGE_KEY_TODAY = 'nutrition_today_v1';
const STORAGE_KEY_TARGETS = 'nutrition_targets_v1';
const STORAGE_KEY_FAVORITES = 'barcode_favorites_v1';
const STORAGE_KEY_HISTORY = 'nutrition_history_v1';

/** Max favorites kept in the MRU list — older items drop off. */
const MAX_FAVORITES = 12;

/**
 * Max rolling-window length for nutrition history.
 * 14 days gives enough signal for weekly trend rules without blowing up
 * the secureStorage entry size — each record is ~200 bytes, so the
 * whole history is a few KB worst-case.
 */
// Widened from 14 → 60 days so the in-store history actually
// supports trend analysis. Apple Health dietary backfill already
// writes up to 14 days on every sync; extending the cap lets repeat
// syncs (and future Railway re-hydration) accumulate a true trend
// window without hitting the cap mid-fetch. Each daily record is
// small (tens of bytes) so 60 days of nutrition totals is
// negligible even on low-storage devices.
const MAX_HISTORY_DAYS = 60;

/**
 * A barcode product the user has scanned and confirmed. We keep the full
 * OpenFoodFactsProduct payload (small, per-100g macros + metadata) so a
 * favorite tap goes directly to the review state with zero network — the
 * user can re-add a regular food instantly, offline-friendly.
 */
export interface StoredBarcodeFavorite {
  product: OpenFoodFactsProduct;
  /** ISO timestamp of the most recent add-to-today from this favorite. */
  last_used_at: string;
  /** Grams the user consumed on the most recent add, if any. Lets the
   *  UI pre-fill the serving input with a sensible default. */
  last_grams?: number;
}

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

async function persistFavoritesSafely(favorites: StoredBarcodeFavorite[]): Promise<void> {
  try {
    if (!favorites || favorites.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY_FAVORITES);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY_FAVORITES, JSON.stringify(favorites));
  } catch {
    // Intentionally swallowed — see helper doc comment.
  }
}

async function persistHistorySafely(history: NutritionRecord[]): Promise<void> {
  try {
    if (!history || history.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY_HISTORY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history));
  } catch {
    // Intentionally swallowed — see helper doc comment.
  }
}

/**
 * Merge a single NutritionRecord into a history array.
 * Dedupe by date (upsert), sort descending by date (newest first),
 * and trim to MAX_HISTORY_DAYS. Pure function — no I/O, no mutation
 * of the input array.
 */
function mergeIntoHistory(
  history: NutritionRecord[],
  record: NutritionRecord,
): NutritionRecord[] {
  const filtered = history.filter((h) => h.date !== record.date);
  const next = [record, ...filtered];
  next.sort((a, b) => b.date.localeCompare(a.date));
  return next.slice(0, MAX_HISTORY_DAYS);
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

  // ---------------------------------------------------------------------
  // Barcode favorites — MRU list of scanned products for quick re-add
  // ---------------------------------------------------------------------

  /**
   * MRU list of products the user has scanned and confirmed via the
   * barcode flow. Capped at MAX_FAVORITES, deduped by barcode, ordered
   * by last_used_at descending. Persisted to secureStorage so the list
   * survives app kill.
   */
  favorites: StoredBarcodeFavorite[];

  /**
   * Add a product to favorites (or update it if already present).
   * Dedupes by barcode, bumps the matching entry to the front of the
   * list with a fresh `last_used_at`, and drops the oldest entries
   * beyond MAX_FAVORITES. `grams` is the serving size the user just
   * confirmed so the next tap on this favorite pre-fills the same
   * amount. Called automatically from the NutritionCard barcode
   * confirm path — nothing else needs to call it directly.
   */
  addFavorite: (product: OpenFoodFactsProduct, grams?: number) => void;

  /** Remove a favorite by its barcode. No-op if not present. */
  removeFavorite: (barcode: string) => void;

  // ---------------------------------------------------------------------
  // Nutrition history — rolling window of past days for trend coaching
  // ---------------------------------------------------------------------

  /**
   * Rolling window of past nutrition records, newest first, deduped by
   * date, capped at MAX_HISTORY_DAYS. Does NOT include today — today
   * lives in `today`. On date rollover (next app launch on a new day),
   * the previous day's `today` is automatically moved into this array
   * by `hydrate()`.
   */
  historyDays: NutritionRecord[];

  /**
   * Manually snapshot the current `today` record into history without
   * waiting for the next date rollover. Useful for "commit partial
   * day" flows. After snapshot, today is preserved — the snapshot is
   * purely additive. Primary automatic snapshot path is `hydrate()`.
   */
  snapshotTodayToHistory: () => void;

  /** Wipe the full history array. Today and targets are untouched. */
  clearHistory: () => void;

  /**
   * Merge an Apple Health / Health Connect dietary daily-totals payload
   * into today's nutrition record. "Manual wins": fields already set
   * by the user are preserved; null/undefined fields are filled from
   * the hub. Provenance is explicit:
   *   - empty record + hub fills → source = 'apple_health' / 'health_connect'
   *   - user-sourced record + hub fills at least one gap → source = 'mixed'
   *   - user-sourced record + hub adds nothing → user source unchanged
   */
  mergeHubDailyTotals: (
    date: string,
    totals: Partial<Omit<NutritionRecord, 'date' | 'source' | 'updated_at'>>,
    hubSource: 'apple_health' | 'health_connect',
  ) => void;
}

export const useNutritionStore = create<NutritionState>((set, get) => ({
  today: null,
  targets: null,
  loading: false,
  error: null,
  hydrated: false,
  favorites: [],
  historyDays: [],

  hydrate: async () => {
    try {
      const [rawToday, rawTargets, rawFavorites, rawHistory] = await Promise.all([
        secureStorage.getItem(STORAGE_KEY_TODAY),
        secureStorage.getItem(STORAGE_KEY_TARGETS),
        secureStorage.getItem(STORAGE_KEY_FAVORITES),
        secureStorage.getItem(STORAGE_KEY_HISTORY),
      ]);

      // Load history first so we can fold a stale today into it
      // during the date-rollover branch below.
      let historyDays: NutritionRecord[] = [];
      if (rawHistory) {
        try {
          const parsed = JSON.parse(rawHistory);
          if (Array.isArray(parsed)) {
            historyDays = parsed
              .filter(
                (h: any) => h && typeof h.date === 'string' && h.date.length > 0,
              )
              .slice(0, MAX_HISTORY_DAYS);
            historyDays.sort((a, b) => b.date.localeCompare(a.date));
          }
        } catch {
          void secureStorage.removeItem(STORAGE_KEY_HISTORY);
        }
      }

      let today: NutritionRecord | null = null;
      if (rawToday) {
        try {
          const parsed = JSON.parse(rawToday) as NutritionRecord;
          // Date-aware: drop stale records from previous days so the
          // user starts fresh for the new day — but first, fold the
          // stale record into history so yesterday's numbers survive.
          if (parsed && parsed.date === todayIsoDate()) {
            today = parsed;
          } else {
            if (parsed && parsed.date) {
              historyDays = mergeIntoHistory(historyDays, parsed);
              void persistHistorySafely(historyDays);
            }
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

      let favorites: StoredBarcodeFavorite[] = [];
      if (rawFavorites) {
        try {
          const parsed = JSON.parse(rawFavorites);
          if (Array.isArray(parsed)) {
            // Defensive filter — drop anything that doesn't have at
            // least a product with a barcode (corrupt or old shape).
            favorites = parsed
              .filter(
                (f: any) =>
                  f &&
                  f.product &&
                  typeof f.product.barcode === 'string' &&
                  f.product.barcode.length > 0,
              )
              .slice(0, MAX_FAVORITES);
          }
        } catch {
          void secureStorage.removeItem(STORAGE_KEY_FAVORITES);
        }
      }

      set({ today, targets, favorites, historyDays, hydrated: true, error: null });
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
    // Fire-and-forget AI backend sync
        if (nextRecord) {
      const uid = useAuthStore.getState().user?.id;
      if (uid) void syncNutritionToAiBackend(uid, nextRecord).catch(() => {});
    }
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
        if (nextRecord) {
      const uid = useAuthStore.getState().user?.id;
      if (uid) void syncNutritionToAiBackend(uid, nextRecord).catch(() => {});
    }
  },

  setTargets: (targets) => {
    set({ targets });
    void persistTargetsSafely(targets);
  },

  clearToday: () => {
    set({ today: null });
    void persistTodaySafely(null);
  },

  addFavorite: (product, grams) => {
    let nextFavorites: StoredBarcodeFavorite[] = [];
    set((state) => {
      const now = new Date().toISOString();
      // Remove any existing entry for this barcode so the bump-to-front
      // dedupe is a single array rewrite.
      const filtered = state.favorites.filter(
        (f) => f.product.barcode !== product.barcode,
      );
      const fresh: StoredBarcodeFavorite = {
        product,
        last_used_at: now,
        last_grams: grams,
      };
      // Most-recent-first ordering, then cap.
      nextFavorites = [fresh, ...filtered].slice(0, MAX_FAVORITES);
      return { favorites: nextFavorites };
    });
    void persistFavoritesSafely(nextFavorites);
  },

  removeFavorite: (barcode) => {
    let nextFavorites: StoredBarcodeFavorite[] = [];
    set((state) => {
      nextFavorites = state.favorites.filter((f) => f.product.barcode !== barcode);
      return { favorites: nextFavorites };
    });
    void persistFavoritesSafely(nextFavorites);
  },

  snapshotTodayToHistory: () => {
    let nextHistory: NutritionRecord[] = [];
    set((state) => {
      if (!state.today) return {};
      nextHistory = mergeIntoHistory(state.historyDays, state.today);
      return { historyDays: nextHistory };
    });
    if (nextHistory.length > 0) {
      void persistHistorySafely(nextHistory);
    }
  },

  clearHistory: () => {
    set({ historyDays: [] });
    void persistHistorySafely([]);
  },

  mergeHubDailyTotals: (date, totals, hubSource) => {
    let nextRecord: NutritionRecord | null = null;
    set((state) => {
      if (state.today && state.today.date !== date) return {};
      const now = new Date().toISOString();
      const base: NutritionRecord = state.today ?? {
        date,
        source: hubSource,
        updated_at: now,
      };
      const fillIfEmpty = <T,>(existing: T | undefined, incoming: T | undefined): {
        value: T | undefined; filled: boolean;
      } => existing != null ? { value: existing, filled: false } : { value: incoming, filled: incoming != null };
      const cal = fillIfEmpty(base.calories_kcal, totals.calories_kcal);
      const pro = fillIfEmpty(base.protein_g, totals.protein_g);
      const carb = fillIfEmpty(base.carbs_g, totals.carbs_g);
      const fat = fillIfEmpty(base.fat_g, totals.fat_g);
      const fibre = fillIfEmpty(base.fibre_g, totals.fibre_g);
      const sugar = fillIfEmpty(base.sugar_g, totals.sugar_g);
      const sodium = fillIfEmpty(base.sodium_mg, totals.sodium_mg);
      const water = fillIfEmpty(base.water_ml, totals.water_ml);
      const hubFilledAny = [cal, pro, carb, fat, fibre, sugar, sodium, water].some((f) => f.filled);
      // Provenance: empty record → hub source. Existing user-sourced
      // record that the hub filled additional gaps in → 'mixed'.
      // Existing user-sourced record with no hub contribution → keep
      // user's source unchanged.
      const nextSource: NutritionRecord['source'] =
        !state.today ? hubSource
        : hubFilledAny && state.today.source !== hubSource ? 'mixed'
        : state.today.source;
      const next: NutritionRecord = {
        ...base,
        date,
        calories_kcal: cal.value,
        protein_g: pro.value,
        carbs_g: carb.value,
        fat_g: fat.value,
        fibre_g: fibre.value,
        sugar_g: sugar.value,
        sodium_mg: sodium.value,
        water_ml: water.value,
        source: nextSource,
        updated_at: now,
      };
      nextRecord = next;
      return { today: next };
    });
    if (nextRecord) void persistTodaySafely(nextRecord);
  },
}));
