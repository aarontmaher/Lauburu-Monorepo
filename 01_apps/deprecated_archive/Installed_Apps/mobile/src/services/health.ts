/**
 * Platform-agnostic health service factory.
 *
 * EXPO GO SAFETY:
 * This file is the ONLY entry point for health services.
 * It NEVER directly requires native modules at the top level.
 *
 * In Expo Go: returns the STUB immediately. The native files
 * (health.ios.ts, health.android.ts) are never loaded.
 *
 * In dev builds: lazily loads native modules via require().
 */
import { Platform } from 'react-native';
import { isExpoGo } from './expo-detect';
import type { IHealthService } from '@lauburu/shared';

let _instance: IHealthService | null = null;
let _isStub = true;

export function getHealthService(): IHealthService {
  // Never keep a cached STUB: if loadNative once returned the fallback
  // STUB (e.g. because Metro hadn't finished resolving the native
  // module on the first call), subsequent calls should retry the real
  // native service. Only a real HealthKitService/HealthConnectService
  // is permanently cached.
  if (_instance && !_isStub) return _instance;

  if (isExpoGo()) {
    _instance = STUB;
    _isStub = true;
    return _instance;
  }

  const next = loadNative();
  _instance = next;
  _isStub = next === STUB;
  return _instance;
}

/**
 * Drop the cached instance. Used by diagnostics when the UI can prove
 * HealthKit is actually available (native debug probe) but the cached
 * service is still STUB — forces a fresh loadNative() on next call.
 */
export function resetHealthServiceCache(): void {
  _instance = null;
  _isStub = true;
}

/**
 * What kind of service is currently active. Visible to testers in the
 * diagnostics panel so "service unavailable" vs "service stubbed" vs
 * "real HealthKit" is unambiguous.
 */
export function getHealthServiceKind(): 'apple_health' | 'health_connect' | 'stub' | 'unknown' {
  if (!_instance) return 'unknown';
  if (_isStub) return 'stub';
  if (Platform.OS === 'ios') return 'apple_health';
  if (Platform.OS === 'android') return 'health_connect';
  return 'unknown';
}

function loadNative(): IHealthService {
  try {
    if (Platform.OS === 'ios') {
      // 1) Preferred: the wrapper class from health.ios.ts.
      try {
        const mod = require('./health.ios');
        const HealthKitService = mod?.HealthKitService;
        if (typeof HealthKitService === 'function') {
          return new HealthKitService();
        }
      } catch { /* fall through to raw-native */ }
      // 2) Raw-native fallback. On some builds the require('./health.ios')
      // path returns a module object without the class, even though
      // @kingstinct/react-native-healthkit itself is perfectly linked
      // (HealthKitDebugCard + HealthActionsPanel's direct bypass both
      // prove this on the same device). Create an inline IHealthService
      // that talks to the native module directly so the rest of the
      // store machinery (checkPermissions, syncData, fetchSamples, …)
      // actually ingests data instead of silently landing on STUB.
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const hk = require('@kingstinct/react-native-healthkit');
        if (hk && typeof hk.isHealthDataAvailable === 'function' && typeof hk.requestAuthorization === 'function') {
          return makeInlineHealthKitService(hk);
        }
      } catch { /* fall through to stub */ }
      // eslint-disable-next-line no-console
      console.warn('[health] iOS HealthKit paths unavailable; using STUB');
      return STUB;
    }
    if (Platform.OS === 'android') {
      const mod = require('./health.android');
      const HealthConnectService = mod?.HealthConnectService;
      if (typeof HealthConnectService !== 'function') {
        // eslint-disable-next-line no-console
        console.warn('[health] HealthConnectService export missing from health.android');
        return STUB;
      }
      return new HealthConnectService();
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('[health] Native health module unavailable:', e);
  }
  return STUB;
}

/**
 * Minimal IHealthService built directly on top of
 * `@kingstinct/react-native-healthkit`. Mirrors the shape of the
 * wrapper class in health.ios.ts but requires zero extra module
 * indirection — it's the safety net when that wrapper module isn't
 * resolving the class correctly at runtime.
 */
function makeInlineHealthKitService(hk: any): IHealthService {
  const QTY: Record<string, string> = {
    resting_heart_rate: 'HKQuantityTypeIdentifierRestingHeartRate',
    hrv: 'HKQuantityTypeIdentifierHeartRateVariabilitySDNN',
    steps: 'HKQuantityTypeIdentifierStepCount',
    active_calories: 'HKQuantityTypeIdentifierActiveEnergyBurned',
    heart_rate: 'HKQuantityTypeIdentifierHeartRate',
  };
  const SLEEP = 'HKCategoryTypeIdentifierSleepAnalysis';
  const READ = [
    QTY.resting_heart_rate,
    QTY.hrv,
    QTY.steps,
    QTY.active_calories,
    QTY.heart_rate,
    'HKQuantityTypeIdentifierDistanceWalkingRunning',
    'HKQuantityTypeIdentifierBodyMass',
    SLEEP,
    'HKWorkoutTypeIdentifier',
  ];
  const allAuthorized = {
    heart_rate: 'authorized' as const,
    resting_heart_rate: 'authorized' as const,
    hrv: 'authorized' as const,
    sleep: 'authorized' as const,
    steps: 'authorized' as const,
    active_calories: 'authorized' as const,
    workouts: 'authorized' as const,
  };
  const notDetermined = {
    heart_rate: 'not_determined' as const,
    resting_heart_rate: 'not_determined' as const,
    hrv: 'not_determined' as const,
    sleep: 'not_determined' as const,
    steps: 'not_determined' as const,
    active_calories: 'not_determined' as const,
    workouts: 'not_determined' as const,
  };
  async function canaryHasData(): Promise<boolean> {
    try {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      const s = await hk.queryQuantitySamples(QTY.steps, { limit: 1, filter: { date: { startDate: start, endDate: end } } });
      return Array.isArray(s) && s.length > 0;
    } catch { return false; }
  }
  return {
    async isAvailable() {
      try { return Boolean(hk.isHealthDataAvailable()); } catch { return false; }
    },
    async checkPermissions() {
      const available = (() => { try { return Boolean(hk.isHealthDataAvailable()); } catch { return false; } })();
      if (!available) return { available: false, permissions: notDetermined };
      // Optimistic: if a 7-day canary read returns any step samples,
      // the user has granted at least the basics.
      return { available: true, permissions: (await canaryHasData()) ? allAuthorized : notDetermined };
    },
    async requestPermissions() {
      try { await hk.requestAuthorization({ toRead: READ }); } catch { /* ignore */ }
      return { available: true, permissions: (await canaryHasData()) ? allAuthorized : notDetermined };
    },
    async fetchSamples(metric, range) {
      const id = QTY[metric];
      if (!id) return [];
      try {
        const results = await hk.queryQuantitySamples(id, { limit: 0, filter: { date: { startDate: range.start, endDate: range.end } } });
        return (results ?? []).map((s: any) => ({
          metric,
          value: s.quantity,
          unit: s.unit ?? '',
          startDate: new Date(s.startDate).toISOString(),
          endDate: new Date(s.endDate).toISOString(),
          source: s.sourceRevision?.source?.name,
        }));
      } catch { return []; }
    },
    async fetchWorkouts(range) {
      try {
        const results = await hk.queryWorkoutSamples({ limit: 0, filter: { date: { startDate: range.start, endDate: range.end } } });
        return (results ?? []).map((w: any) => {
          const startMs = new Date(w.startDate).getTime();
          const endMs = new Date(w.endDate).getTime();
          return {
            type: String(w.workoutActivityType ?? 'unknown'),
            name: String(w.workoutActivityType ?? 'workout'),
            duration_min: Math.round((endMs - startMs) / 60_000),
            calories: w.totalEnergyBurned?.quantity,
            distance_m: w.totalDistance?.quantity ? Math.round(w.totalDistance.quantity * 1000) : undefined,
            startDate: new Date(w.startDate).toISOString(),
            endDate: new Date(w.endDate).toISOString(),
            source: w.sourceRevision?.source?.name,
            source_id: w.uuid,
          };
        });
      } catch { return []; }
    },
    async fetchSleep(range) {
      try {
        const results = await hk.queryCategorySamples(SLEEP, { limit: 0, filter: { date: { startDate: range.start, endDate: range.end } } });
        return (results ?? []).map((s: any) => ({
          stage: String(s.value ?? 'asleep'),
          startDate: new Date(s.startDate).toISOString(),
          endDate: new Date(s.endDate).toISOString(),
          source: s.sourceRevision?.source?.name,
        }));
      } catch { return []; }
    },
  };
}

/** Safe stub — works everywhere, returns "unavailable" for all metrics */
const STUB: IHealthService = {
  isAvailable: async () => false,
  checkPermissions: async () => ({
    available: false,
    permissions: {
      heart_rate: 'unavailable' as const,
      resting_heart_rate: 'unavailable' as const,
      hrv: 'unavailable' as const,
      sleep: 'unavailable' as const,
      steps: 'unavailable' as const,
      active_calories: 'unavailable' as const,
      workouts: 'unavailable' as const,
    },
  }),
  requestPermissions: async () => ({
    available: false,
    permissions: {
      heart_rate: 'unavailable' as const,
      resting_heart_rate: 'unavailable' as const,
      hrv: 'unavailable' as const,
      sleep: 'unavailable' as const,
      steps: 'unavailable' as const,
      active_calories: 'unavailable' as const,
      workouts: 'unavailable' as const,
    },
  }),
  fetchSamples: async () => [],
  fetchWorkouts: async () => [],
  fetchSleep: async () => [],
};
