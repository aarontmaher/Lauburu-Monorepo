/**
 * Health data store — manages permissions, sync, backend persistence,
 * and derived features. Connects native health services through the
 * shared normalization and feature derivation layers.
 */
import { Platform } from 'react-native';
import { create } from 'zustand';
import { syncHealthToAiBackend, isPolarSource, friendlyPolarSourceApp, isSamsungHealthSource, friendlySamsungHealthSourceApp } from '../services/ai-health-sync';
import {
  HealthProvider,
  normalizeHealthData,
  deriveFeatures,
  computeFlags,
  toBackendPayload,
  buildAIHealthContext,
  generateInsights,
  exportAIPayload,
  generateCoaching,
  mergeTrainingSessions,
  SUPABASE_FUNCTIONS_URL,
} from '@lauburu/shared';
import type {
  DailyMetrics,
  DerivedFeatures,
  HealthPermissions,
  AIHealthContext,
  TrainingInsight,
  AIPayload,
  CoachingResponse,
} from '@lauburu/shared';
import type { HealthFlag } from '@lauburu/shared';
// IMPORTANT: import from `health-factory`, NOT `../services/health`.
// Metro's platform resolver picks `health.ios.ts` over `health.ts` on
// iOS (and `health.android.ts` on Android), so
// `import { getHealthService } from '../services/health'` was silently
// resolving to the platform-specific file, which does NOT export the
// factory. safeGetHealthService() would call `undefined()`, throw,
// return null, and syncData would throw "Health service unavailable"
// — exactly what the device kept reporting. The factory file is now
// renamed to a platform-neutral path to break the resolver collision.
import { getHealthService } from '../services/health-factory';
function safeGetHealthService() {
  try {
    return getHealthService();
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[HealthStore] getHealthService threw:', e);
    return null;
  }
}
import { useAuthStore } from './auth-store';
import { useTrainingStore } from './training-store';
import { usePreferencesStore } from './preferences-store';
import { useTierStore } from './tier-store';
import {
  readStoredJson,
  writeStoredJson,
  removeStoredJson,
} from './secure-storage';

const META_STORAGE_KEY = 'health_sync_meta_v1';
const DAYS_STORAGE_KEY = 'health_days_v1';
// 365 days of normalized DailyMetrics is ~240-480 KB — still trivial
// on secureStorage, covers a full year of trend analysis. Lifted
// from 90 so reinstall/cold-boot surfaces the full backlog the
// backend + Coach now consume.
const DAYS_CACHE_CAP = 365;

interface PersistedHealthMeta {
  lastSyncAt: string | null;
  lastPersistedAt: string | null;
  lastPersistResult: { recordCount: number; dateRange: string } | null;
}

async function persistDaysSafely(days: DailyMetrics[]): Promise<void> {
  try {
    if (!Array.isArray(days) || days.length === 0) {
      await removeStoredJson(DAYS_STORAGE_KEY);
      return;
    }
    const sorted = [...days].sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''));
    const capped = sorted.slice(0, DAYS_CACHE_CAP);
    await writeStoredJson(DAYS_STORAGE_KEY, capped);
  } catch { /* non-fatal */ }
}

function sanitizeCachedDays(value: unknown): DailyMetrics[] {
  if (!Array.isArray(value)) return [];
  return value.filter((d): d is DailyMetrics =>
    !!d && typeof d === 'object' && typeof (d as any).date === 'string',
  ) as DailyMetrics[];
}

/**
 * Persist the sync/persist metadata only. Raw native days, derived
 * features, coaching responses, and AI payloads are deliberately
 * NOT persisted — they're rebuilt from the native health source
 * (HealthKit / Health Connect) on every sync, and persisting them
 * would risk showing stale readiness to the user on cold start.
 * The small three-field meta blob is safe because it describes
 * WHEN data was last touched, not what the data contained.
 */
async function persistMetaSafely(meta: PersistedHealthMeta): Promise<void> {
  const isEmpty =
    meta.lastSyncAt === null &&
    meta.lastPersistedAt === null &&
    meta.lastPersistResult === null;
  if (isEmpty) {
    await removeStoredJson(META_STORAGE_KEY);
    return;
  }
  await writeStoredJson(META_STORAGE_KEY, meta);
}

function sanitizeMeta(value: unknown): PersistedHealthMeta | null {
  if (!value || typeof value !== 'object') return null;
  const parsed = value as Partial<PersistedHealthMeta>;
  const lastSyncAt =
    typeof parsed.lastSyncAt === 'string' ? parsed.lastSyncAt : null;
  const lastPersistedAt =
    typeof parsed.lastPersistedAt === 'string' ? parsed.lastPersistedAt : null;
  let lastPersistResult: PersistedHealthMeta['lastPersistResult'] = null;
  if (parsed.lastPersistResult && typeof parsed.lastPersistResult === 'object') {
    const r = parsed.lastPersistResult as Partial<{
      recordCount: number;
      dateRange: string;
    }>;
    if (typeof r.recordCount === 'number' && typeof r.dateRange === 'string') {
      lastPersistResult = { recordCount: r.recordCount, dateRange: r.dateRange };
    }
  }
  return { lastSyncAt, lastPersistedAt, lastPersistResult };
}

interface HealthState {
  /** Raw native health days before manual training is merged in */
  nativeDays: DailyMetrics[];

  /** Current permission state */
  permissions: HealthPermissions | null;

  /** Whether a sync is in progress */
  syncing: boolean;

  /** Whether a backend persist is in progress */
  persisting: boolean;

  /** Last successful native sync timestamp */
  lastSyncAt: string | null;

  /** Last successful backend persist timestamp */
  lastPersistedAt: string | null;

  /** Backend persist result summary */
  lastPersistResult: { recordCount: number; dateRange: string } | null;

  /** Normalized daily metrics from native health source */
  days: DailyMetrics[];

  /** Today's metrics (convenience accessor) */
  today: DailyMetrics | null;

  /** AI-ready derived features computed from days[] */
  features: DerivedFeatures | null;

  /** Notable flags / conditions for UI display */
  flags: HealthFlag[];

  /** Compact AI health context (for future MCP/AI consumption) */
  aiContext: AIHealthContext | null;

  /** Rules-based training insights */
  insights: TrainingInsight | null;

  /** Exportable AI payload for MCP/coaching consumption */
  aiPayload: AIPayload | null;

  /** Structured coaching response */
  coaching: CoachingResponse | null;

  /**
   * Polar-via-Health-Connect provenance snapshot for the most recent
   * sync. Null until a sync runs. Only meaningful on Android; on iOS
   * it will almost always be null unless the user has Polar writing
   * to HealthKit. UI should use this to decide whether to show the
   * "Polar via Health Connect detected" state on the Polar card.
   */
  polarViaHc: {
    detected: boolean;
    sourceApp: string | null;
    domains: string[];
    daysWithRecords: number;
    lastSeenAt: string | null;
  } | null;

  /**
   * Samsung Health provenance — same pattern as polarViaHc. Detected
   * from Health Connect dataOrigin matching Samsung Health packages.
   */
  samsungHealthViaHc: {
    detected: boolean;
    sourceApp: string | null;
    domains: string[];
    daysWithRecords: number;
    lastSeenAt: string | null;
  } | null;

  /**
   * Health Connect history access state (Android 14+ only).
   * 'unknown' = not checked yet; 'granted' = full history reads;
   * 'denied' = limited to ~30 days; 'unavailable' = pre-Android-14.
   */
  historyAccess: 'unknown' | 'granted' | 'denied' | 'unavailable';

  /** Check + request Health Connect history permission. */
  requestHistoryAccess: () => Promise<boolean>;

  /**
   * Diagnostics from the last sync — lets testers see exactly what
   * happened without exposing raw health data or tokens.
   */
  lastSyncDiagnostics: {
    timestamp: string;
    recordCounts: {
      restingHr: number;
      hrv: number;
      steps: number;
      activeCal: number;
      heartRate: number;
      workouts: number;
      sleep: number;
    };
    provenanceDetected: string[];
    daysBack: number;
    normalizedDays: number;
    backendSyncAttempted: boolean;
    error: string | null;
  } | null;

  /** Error from last operation */
  error: string | null;

  /** Check permissions without requesting */
  checkPermissions: () => Promise<void>;

  /** Request health permissions from user */
  requestPermissions: () => Promise<boolean>;

  /** Sync health data for the last N days from native source.
   *  Default window is 365 days so the AI layer has a real baseline
   *  rather than one week of noise. Pass a smaller value when a quick
   *  refresh is wanted; pass a larger value (or use `backfillData`) to
   *  pull deeper history. */
  syncData: (userId: string, daysBack?: number) => Promise<void>;

  /** Deep historical backfill — pulls as much authorized HealthKit /
   *  Health Connect history as the platform allows (we request ~5y).
   *  Sets `lastBackfillAt` on success so we don't silently re-backfill
   *  every app launch. */
  backfillData: (userId: string) => Promise<void>;

  /** Width in days of the most recent successful sync window. Separate
   *  from `lastSyncDiagnostics.daysBack` so the UI can display the
   *  current authorized history window without conflating it with the
   *  per-sync record counts. */
  historyWindowDays: number | null;

  /** ISO timestamp of the last successful deep backfill. */
  lastBackfillAt: string | null;

  /** Persist current days[] to Supabase backend */
  persistToBackend: () => Promise<boolean>;

  /** Recompute merged health/coaching state from native days + local stores */
  recomputeDerived: () => void;

  /** Whether persisted sync metadata has been loaded */
  metaHydrated: boolean;

  /** Hydrate last-sync / last-persist metadata from secureStorage */
  hydrateMeta: () => Promise<void>;
}

const todayStr = () => new Date().toISOString().slice(0, 10);

function buildDerivedState(nativeDays: DailyMetrics[], lastPersistedAt: string | null) {
  const trainingSessions = useTrainingStore.getState().sessions;
  const days = mergeTrainingSessions(nativeDays, trainingSessions);
  const today = days.find((d) => d.date === todayStr()) ?? null;
  const features = deriveFeatures(days);
  const flags = computeFlags(features, today);
  const aiContext = buildAIHealthContext(days, features, flags);
  const insights = generateInsights(aiContext);
  const generatedAt = new Date().toISOString();
  const aiPayload = exportAIPayload(
    days,
    features,
    flags,
    insights,
    aiContext,
    generatedAt,
    lastPersistedAt,
  );
  const prefs = usePreferencesStore.getState().preferences;
  const coaching = generateCoaching(aiPayload, prefs);

  return {
    days,
    today,
    features,
    flags,
    aiContext,
    insights,
    aiPayload,
    coaching,
  };
}

export const useHealthStore = create<HealthState>((set, get) => ({
  nativeDays: [],
  permissions: null,
  syncing: false,
  persisting: false,
  lastSyncAt: null,
  lastPersistedAt: null,
  lastPersistResult: null,
  metaHydrated: false,
  historyWindowDays: null,
  lastBackfillAt: null,

  hydrateMeta: async () => {
    const parsed = await readStoredJson<unknown>(META_STORAGE_KEY);
    const next = sanitizeMeta(parsed);
    // Rehydrate cached days in parallel so cold-boot / reinstall /
    // app-switch returns don't show a blank state until the next sync
    // lands. The cache is authoritative for display only; any sync
    // that follows overwrites it.
    let cachedDays: DailyMetrics[] = [];
    try {
      const rawDays = await readStoredJson<unknown>(DAYS_STORAGE_KEY);
      cachedDays = sanitizeCachedDays(rawDays);
    } catch { /* non-fatal */ }
    // If we have cached days, recompute the full derived bundle
    // (today, features, flags, aiContext, insights, aiPayload,
    // coaching) so Recent Days / TodayCard / InsightsCard light up
    // on cold start instead of waiting for the next manual sync.
    const derived = cachedDays.length > 0
      ? buildDerivedState(cachedDays, next?.lastPersistedAt ?? null)
      : null;
    if (!next) {
      set({
        metaHydrated: true,
        days: cachedDays,
        ...(derived ? { ...derived } : {}),
      });
      return;
    }
    set({
      lastSyncAt: next.lastSyncAt,
      lastPersistedAt: next.lastPersistedAt,
      lastPersistResult: next.lastPersistResult,
      metaHydrated: true,
      days: cachedDays,
      ...(derived ? { ...derived } : {}),
    });
  },
  days: [],
  today: null,
  features: null,
  flags: [],
  aiContext: null,
  insights: null,
  aiPayload: null,
  coaching: null,
  polarViaHc: null,
  samsungHealthViaHc: null,
  lastSyncDiagnostics: null,
  historyAccess: 'unknown',

  requestHistoryAccess: async () => {
    try {
      const service = safeGetHealthService();
      if (!service || typeof (service as any).requestHistoryPermission !== 'function') {
        set({ historyAccess: 'unavailable' });
        return false;
      }
      const granted = await (service as any).requestHistoryPermission();
      set({ historyAccess: granted ? 'granted' : 'denied' });
      return granted;
    } catch {
      set({ historyAccess: 'unavailable' });
      return false;
    }
  },

  error: null,

  checkPermissions: async () => {
    try {
      const service = safeGetHealthService(); if (!service) { set({ error: "Health service unavailable" }); return; }
      const perms = await service.checkPermissions();
      set({ permissions: perms, error: null });
    } catch (e: any) {
      set({ error: e?.message ?? 'Permission check failed' });
    }
  },

  requestPermissions: async () => {
    try {
      const service = safeGetHealthService(); if (!service) { set({ error: "Health service unavailable" }); return false; }
      const perms = await service.requestPermissions();
      set({ permissions: perms, error: null });
      const anyAuthorized = Object.values(perms.permissions).some(
        (s) => s === 'authorized',
      );
      return anyAuthorized;
    } catch (e: any) {
      set({ error: e?.message ?? 'Permission request failed' });
      return false;
    }
  },

  syncData: async (userId, daysBack = 365) => {
    // Default window is 365 days so the AI layer has a real baseline.
    // Pass a smaller value when a quick refresh is wanted, or call
    // `backfillData` to pull maximum authorized history in one pass.
    set({ syncing: true, error: null });

    try {
      const service = safeGetHealthService();
      if (!service) {
        throw new Error('Health service unavailable');
      }
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - daysBack);
      const range = { start, end };

      // Continuous heart-rate samples can be 500k+ rows per year on
      // Apple Watch users. A 5-year unlimited pull through the
      // HealthKit bridge crashes the app — the JS heap blows up
      // holding arrays of hundreds of thousands of sample objects.
      // Heart-rate here is ONLY used for Polar / Samsung provenance
      // detection (not for normalized daily metrics), so cap to the
      // most recent 30 days regardless of how deep the rest of the
      // backfill goes. Provenance only needs a current-state signal,
      // not years of HR timeseries.
      const HR_DAYS_CAP = 30;
      const hrRange = (() => {
        if (daysBack <= HR_DAYS_CAP) return range;
        const hrStart = new Date();
        hrStart.setDate(hrStart.getDate() - HR_DAYS_CAP);
        return { start: hrStart, end };
      })();

      // Fetch all metric types in parallel
      const [restingHr, hrv, steps, activeCal, heartRate, workouts, sleep] =
        await Promise.all([
          service.fetchSamples('resting_heart_rate', range),
          service.fetchSamples('hrv', range),
          service.fetchSamples('steps', range),
          service.fetchSamples('active_calories', range),
          service.fetchSamples('heart_rate', hrRange),
          service.fetchWorkouts(range),
          service.fetchSleep(range),
        ]);

      const allSamples = [...restingHr, ...hrv, ...steps, ...activeCal];

      const provider =
        Platform.OS === 'ios'
          ? HealthProvider.APPLE_HEALTH
          : HealthProvider.HEALTH_CONNECT;

      // Normalize through shared layer
      const nativeDays = normalizeHealthData(
        userId,
        provider,
        allSamples,
        workouts,
        sleep,
      );

      // Pre-compute Polar-via-Health-Connect provenance for this sync so
      // the UI can immediately reflect whether Polar Flow is routing
      // data through HC — even if the backend POST below fails. This
      // never leaks WHOOP state and never infers Polar from shape.
      const polarSamples = [...restingHr, ...hrv, ...steps, ...activeCal, ...heartRate]
        .filter((s) => isPolarSource(s.source));
      const polarWorkouts = workouts.filter((w) => isPolarSource(w.source));
      const polarSleep = sleep.filter((s) => isPolarSource(s.source));
      const polarDetected = polarSamples.length > 0 || polarWorkouts.length > 0 || polarSleep.length > 0;
      let polarViaHc: HealthState['polarViaHc'] = null;
      if (polarDetected) {
        const domains = new Set<string>();
        for (const s of polarSamples) {
          if (s.metric === 'hrv') domains.add('hrv');
          else if (s.metric === 'resting_heart_rate') domains.add('resting_hr');
          else if (s.metric === 'steps') domains.add('steps');
          else if (s.metric === 'active_calories') domains.add('active_calories');
          else if (s.metric === 'heart_rate') domains.add('heart_rate_samples');
        }
        if (polarWorkouts.length > 0) domains.add('workouts');
        if (polarSleep.length > 0) domains.add('sleep');
        const firstSource = polarSamples[0]?.source ?? polarWorkouts[0]?.source ?? polarSleep[0]?.source;
        const daySet = new Set<string>();
        for (const s of polarSamples) daySet.add(s.startDate.slice(0, 10));
        for (const w of polarWorkouts) daySet.add(w.startDate.slice(0, 10));
        for (const s of polarSleep) daySet.add((s.endDate ?? s.startDate).slice(0, 10));
        const lastSeen = [...polarSamples.map((s) => s.endDate), ...polarWorkouts.map((w) => w.endDate), ...polarSleep.map((s) => s.endDate)]
          .filter((x): x is string => typeof x === 'string')
          .sort()
          .pop() ?? null;
        polarViaHc = {
          detected: true,
          sourceApp: friendlyPolarSourceApp(firstSource),
          domains: Array.from(domains),
          daysWithRecords: daySet.size,
          lastSeenAt: lastSeen,
        };
      }

      // Samsung Health provenance — same pattern as Polar.
      const samsungSamples = [...restingHr, ...hrv, ...steps, ...activeCal, ...heartRate]
        .filter((s) => isSamsungHealthSource(s.source));
      const samsungWorkouts = workouts.filter((w) => isSamsungHealthSource(w.source));
      const samsungSleep = sleep.filter((s) => isSamsungHealthSource(s.source));
      const samsungDetected = samsungSamples.length > 0 || samsungWorkouts.length > 0 || samsungSleep.length > 0;
      let samsungHealthViaHc: HealthState['samsungHealthViaHc'] = null;
      if (samsungDetected) {
        const domains = new Set<string>();
        for (const s of samsungSamples) {
          if (s.metric === 'hrv') domains.add('hrv');
          else if (s.metric === 'resting_heart_rate') domains.add('resting_hr');
          else if (s.metric === 'steps') domains.add('steps');
          else if (s.metric === 'active_calories') domains.add('active_calories');
          else if (s.metric === 'heart_rate') domains.add('heart_rate_samples');
        }
        if (samsungWorkouts.length > 0) domains.add('workouts');
        if (samsungSleep.length > 0) domains.add('sleep');
        const firstSource = samsungSamples[0]?.source ?? samsungWorkouts[0]?.source ?? samsungSleep[0]?.source;
        const daySet = new Set<string>();
        for (const s of samsungSamples) daySet.add(s.startDate.slice(0, 10));
        for (const w of samsungWorkouts) daySet.add(w.startDate.slice(0, 10));
        for (const s of samsungSleep) daySet.add((s.endDate ?? s.startDate).slice(0, 10));
        const lastSeen = [...samsungSamples.map((s) => s.endDate), ...samsungWorkouts.map((w) => w.endDate), ...samsungSleep.map((s) => s.endDate)]
          .filter((x): x is string => typeof x === 'string').sort().pop() ?? null;
        samsungHealthViaHc = {
          detected: true,
          sourceApp: friendlySamsungHealthSourceApp(firstSource),
          domains: Array.from(domains),
          daysWithRecords: daySet.size,
          lastSeenAt: lastSeen,
        };
      }

      const now = new Date().toISOString();
      const { lastPersistedAt } = get();
      const derived = buildDerivedState(nativeDays, lastPersistedAt);

      // Build diagnostics for tester visibility.
      const allRawSources = [
        ...restingHr.map((s) => s.source),
        ...hrv.map((s) => s.source),
        ...steps.map((s) => s.source),
        ...activeCal.map((s) => s.source),
        ...heartRate.map((s) => s.source),
        ...workouts.map((w) => w.source),
        ...sleep.map((s) => s.source),
      ].filter((s): s is string => typeof s === 'string' && s.length > 0);
      const uniqueSources = [...new Set(allRawSources)];

      const lastSyncDiagnostics: HealthState['lastSyncDiagnostics'] = {
        timestamp: now,
        recordCounts: {
          restingHr: restingHr.length,
          hrv: hrv.length,
          steps: steps.length,
          activeCal: activeCal.length,
          heartRate: heartRate.length,
          workouts: workouts.length,
          sleep: sleep.length,
        },
        provenanceDetected: uniqueSources,
        daysBack,
        normalizedDays: nativeDays.length,
        backendSyncAttempted: true,
        error: null,
      };

      set((s) => {
        void persistMetaSafely({
          lastSyncAt: now,
          lastPersistedAt: s.lastPersistedAt,
          lastPersistResult: s.lastPersistResult,
        });
        // Persist the normalized days so cold-boot / app-reopen shows
        // backlog immediately. Previously only metadata was cached,
        // leaving days[] empty until the next sync ran — which is why
        // the user saw "only 2 days" after reopen: syncData was
        // defaulting to a small recent window on second mount.
        void persistDaysSafely((derived as any).days ?? s.days);
        return {
          nativeDays,
          ...derived,
          syncing: false,
          lastSyncAt: now,
          polarViaHc,
          samsungHealthViaHc,
          lastSyncDiagnostics,
          historyWindowDays: daysBack,
          error: null,
        };
      });

      // Fire-and-forget: post health data to canonical AI backend.
      // Failures are logged but never block the mobile sync.
      // Raw samples are passed so Polar-via-HC provenance is posted
      // as a second ingest per affected day.
      void syncHealthToAiBackend(userId, nativeDays, {
        restingHr,
        hrv,
        steps,
        activeCal,
        heartRate,
        workouts,
        sleep,
      }).catch(() => {});

      // Ingest dietary totals from Apple Health / Health Connect into
      // the nutrition store so the Nutrition card shows real data
      // without Cronometer direct. Manual-wins merge preserves the
      // user's own entries; hub fills gaps. Fire-and-forget — failures
      // never block the health sync.
      if (Platform.OS === 'ios') {
        void (async () => {
          try {
            // eslint-disable-next-line @typescript-eslint/no-require-imports
            const hkMod = require('../services/health.ios');
            if (typeof hkMod?.fetchDietaryDailyTotals === 'function') {
              // Backfill dietary totals for the last 14 days so the
              // nutrition history + Railway AI learning path see more
              // than just today. Earlier builds only merged today,
              // which made Coach blind to weekly patterns even when
              // Apple Health had weeks of third-party tracker data.
              const HISTORY_DAYS = 14;
              const authMod = require('./auth-store');
              const uidForHistory = authMod?.useAuthStore?.getState?.()?.user?.id;
              // eslint-disable-next-line @typescript-eslint/no-require-imports
              const syncMod = require('../services/ai-nutrition-sync');
              for (let lag = HISTORY_DAYS - 1; lag > 0; lag -= 1) {
                const ds = new Date(now); ds.setDate(ds.getDate() - lag); ds.setHours(0, 0, 0, 0);
                const de = new Date(ds); de.setHours(23, 59, 59, 999);
                try {
                  const t = await hkMod.fetchDietaryDailyTotals({ start: ds, end: de });
                  if (!t) continue;
                  if (!t.calories_kcal && !t.protein_g) continue;
                  const key = ds.toISOString().slice(0, 10);
                  if (uidForHistory && typeof syncMod?.syncNutritionToAiBackend === 'function') {
                    const { meal_count: _mc, first_meal_at: _fm, last_meal_at: _lm, ...rec } = t;
                    void syncMod.syncNutritionToAiBackend(uidForHistory, {
                      date: key, ...rec, source: 'apple_health', updated_at: new Date().toISOString(),
                    }, {
                      source: 'apple_health', sourceState: 'live',
                      sourceDependencies: ['apple_health_dietary_backfill'], evidenceIds: [],
                    }).catch(() => {});
                  }
                } catch { /* ignore one-day failure */ }
              }
              const todayStart = new Date(now);
              todayStart.setHours(0, 0, 0, 0);
              const todayEnd = new Date(now);
              todayEnd.setHours(23, 59, 59, 999);
              const totals = await hkMod.fetchDietaryDailyTotals({ start: todayStart, end: todayEnd });
              if (totals) {
                // Strip meal-count metadata before merging — those
                // keys don't belong on NutritionRecord; they're used
                // for the backend ingest payload only.
                const { meal_count: _mc, first_meal_at: _fm, last_meal_at: _lm, ...recordTotals } = totals;
                // eslint-disable-next-line @typescript-eslint/no-require-imports
                const ns = require('./nutrition-store');
                const merge = ns?.useNutritionStore?.getState?.()?.mergeHubDailyTotals;
                if (typeof merge === 'function') {
                  merge(now.slice(0, 10), recordTotals, 'apple_health');
                }
                // Send the full payload (incl. meal_count/first/last)
                // to the backend so the AI can learn from meal-timing
                // context without bloating the per-day store record.
                try {
                  const authMod = require('./auth-store');
                  const uid = authMod?.useAuthStore?.getState?.()?.user?.id;
                  if (uid) {
                    // eslint-disable-next-line @typescript-eslint/no-require-imports
                    const syncMod = require('../services/ai-nutrition-sync');
                    if (typeof syncMod?.syncNutritionToAiBackend === 'function') {
                      const synthetic = {
                        date: now.slice(0, 10),
                        ...recordTotals,
                        source: 'apple_health' as const,
                        updated_at: new Date().toISOString(),
                      };
                      void syncMod.syncNutritionToAiBackend(uid, synthetic, {
                        source: 'apple_health',
                        sourceState: 'live',
                        sourceDependencies: ['apple_health_dietary'],
                        evidenceIds: [],
                      }).catch(() => {});
                    }
                  }
                } catch { /* ignore */ }
              }
            }
          } catch { /* ignore */ }
        })();
      }
    } catch (e: any) {
      set({
        syncing: false,
        error: e?.message ?? 'Health sync failed',
      });
    }
  },

  backfillData: async (userId: string) => {
    // Deep historical pull. Walk back in 1-year windows so each call
    // is a bounded-memory syncData; the HR cap inside syncData keeps
    // the heaviest metric (continuous heart rate) out of long-window
    // pulls entirely. Yield between windows so the JS event loop
    // breathes — this stops the UI from freezing and gives GC a
    // chance to reclaim the previous window's sample arrays before
    // the next query starts.
    const WINDOWS = [365, 730, 1095, 1460, 1825];
    for (const w of WINDOWS) {
      await get().syncData(userId, w);
      if (get().error) break; // stop on first failure; caller sees error
      // Breath between windows — 250ms is enough for RN's JS thread
      // to handle any pending UI work and let the bridge's sample
      // arrays be dropped before we kick the next query.
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    if (!get().error) {
      set({ lastBackfillAt: new Date().toISOString(), historyWindowDays: 1825 });
    }
  },

  persistToBackend: async () => {
    // Tier gate: backend persistence requires low_cost+
    if (!useTierStore.getState().can('backend_persistence')) {
      set({ error: 'Cloud sync requires Starter plan or higher' });
      return false;
    }
    // Pre-flight ES256-rejection check removed: under the new
    // Supabase JWT Signing Keys model (Project Settings → JWT Keys),
    // edge functions verify tokens via JWKS regardless of the
    // underlying signing algorithm name (HS256 / RS256 / ES256 are
    // all valid). The legacy "flip algorithm to HS256" path doesn't
    // exist in the dashboard anymore. Let the real request through
    // and surface the actual edge-function response if it fails.

    // `days[]` lives in memory only (nativeDays + trainingSessions
    // merge) — it's empty on a cold-start launch until Sync Apple
    // Health re-populates it. Previous behaviour bailed with
    // "No health data to persist" and the user had to manually tap
    // Sync Apple Health first. Do it automatically so Save to
    // Account is a single tap.
    let days = get().days;
    if (days.length === 0) {
      const uid = useAuthStore.getState().user?.id;
      if (uid) {
        try { await get().syncData(uid); } catch { /* ignore */ }
        days = get().days;
      }
    }
    if (days.length === 0) {
      set({
        error: 'No health data to persist. Tap Sync Apple Health first, or grant HealthKit access if not yet granted.',
      });
      return false;
    }

    const getToken = useAuthStore.getState().getAccessToken;
    const token = await getToken();
    if (!token) {
      set({ error: 'Sign in to save health data to your account' });
      return false;
    }

    set({ persisting: true, error: null });

    try {
      const provider =
        Platform.OS === 'ios' ? 'apple_health' : 'health_connect';

      const payload = toBackendPayload(days);

      // Direct fetch so we can surface the real HTTP status / body on
      // failure. The shared apiFetch returns null for any non-OK
      // response, which hid the actual 4xx/5xx reason (payload too
      // large, schema mismatch, tier gate, etc.) under an opaque
      // "Backend import failed" message.
      let httpStatus = 0;
      let bodyText = '';
      let parsed: any = null;
      try {
        const resp = await fetch(`${SUPABASE_FUNCTIONS_URL}/health-import`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            provider,
            import_mode: 'native_sync',
            raw_payload: payload,
          }),
        });
        httpStatus = resp.status;
        bodyText = await resp.text().catch(() => '');
        try { parsed = bodyText ? JSON.parse(bodyText) : null; } catch { /* keep text */ }
      } catch (netErr: any) {
        set({
          persisting: false,
          error: `Backend network error: ${netErr?.message ?? 'unknown'}`,
        });
        return false;
      }

      if (httpStatus >= 200 && httpStatus < 300 && parsed?.ok) {
        const dateRange = parsed.date_range
          ? `${parsed.date_range.start} → ${parsed.date_range.end}`
          : '';
        const lastPersistedAt = new Date().toISOString();
        const lastPersistResult = {
          recordCount: parsed.record_count ?? 0,
          dateRange,
        };
        set((s) => {
          void persistMetaSafely({
            lastSyncAt: s.lastSyncAt,
            lastPersistedAt,
            lastPersistResult,
          });
          return {
            persisting: false,
            lastPersistedAt,
            lastPersistResult,
            error: null,
          };
        });
        return true;
      }

      // Detailed, truthful error so the Alert shows the real reason.
      const reason =
        parsed?.error ??
        parsed?.message ??
        (bodyText ? bodyText.slice(0, 160) : '') ??
        '';
      const sizeKb = Math.round(JSON.stringify(payload).length / 1024);
      const tooLargeHint = httpStatus === 413 || sizeKb > 900
        ? ` (payload ${sizeKb}KB — may exceed edge function limit; try Sync Apple Health without a deep backfill, or we can chunk)`
        : '';
      // JWT-rejection hint under the new Supabase JWT Signing Keys
      // model: if the edge function rejects the token, the operator
      // path is Project Settings → JWT Keys → review the active /
      // standby keys (rotate to a new standby and revoke if needed).
      // The legacy "flip algorithm to HS256" toggle no longer exists
      // in the dashboard. This can't be fixed from the mobile client.
      const jwtHint = /jwt|signing|algorithm|unauthor/i.test(reason) || httpStatus === 401
        ? '\n\nSupabase JWT signing keys may need attention. Open Project Settings → JWT Keys: confirm an active signing key is in place; if it was recently rotated, sign out + sign back in on this device so the next access-token uses the new key. Until resolved, the Supabase mirror is the only blocked path — Railway /ingest still works.'
        : '';
      set({
        persisting: false,
        error: `Backend import HTTP ${httpStatus || '?'}${reason ? `: ${reason}` : ''}${tooLargeHint}${jwtHint}`,
      });
      return false;
    } catch (e: any) {
      set({
        persisting: false,
        error: e?.message ?? 'Backend persist failed',
      });
      return false;
    }
  },

  recomputeDerived: () => {
    const { nativeDays, lastPersistedAt } = get();
    const derived = buildDerivedState(nativeDays, lastPersistedAt);
    set(derived);
  },
}));

useTrainingStore.subscribe((state, previous) => {
  if (state.sessions !== previous.sessions) {
    useHealthStore.getState().recomputeDerived();
  }
});

usePreferencesStore.subscribe((state, previous) => {
  if (state.preferences !== previous.preferences) {
    useHealthStore.getState().recomputeDerived();
  }
});
