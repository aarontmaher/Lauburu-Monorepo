/**
 * iOS HealthKit implementation of IHealthService.
 *
 * Native module (@kingstinct/react-native-healthkit) loads via Nitro.
 * The require() itself can throw at module-load time when Nitro's
 * CoreModule HybridObject registration fails. That error used to be
 * swallowed by a bare try/catch, which made the runtime indistinguishable
 * from "HealthKit not linked". We now capture the real error and expose
 * it via getHealthKitNativeDebug() so the UI can show it on-device.
 *
 * REQUIRES: expo prebuild --platform ios --clean after any config change,
 * plus an EAS iOS build (OTA cannot re-link native frameworks).
 */
import type {
  IHealthService,
  HealthPermissions,
  HealthMetricType,
  RawHealthSample,
  RawWorkoutSample,
  RawSleepSample,
  DateRange,
  PermissionStatus,
} from '@lauburu/shared';

type HkModule = any;

let _hk: HkModule | null = null;
let _requireError: string | null = null;
let _availabilityError: string | null = null;
let _isHealthDataAvailableResult: boolean | null = null;
let _lastCallError: string | null = null;
let _lastAuthRequestAt: string | null = null;
let _lastAuthRequestOk: boolean | null = null;
let _lastAuthRequestReturn: string | null = null;
let _lastAuthRequestError: string | null = null;
let _lastCanaryReadCount: number | null = null;
let _lastRequestedReadTypes: string[] = [];

function loadHk(): HkModule | null {
  if (_hk) return _hk;
  if (_requireError) return null;
  try {
    // Literal string so Metro bundles it.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    _hk = require('@kingstinct/react-native-healthkit');
    return _hk;
  } catch (e: any) {
    _requireError =
      e?.message || e?.toString?.() || 'require("@kingstinct/react-native-healthkit") failed';
    // eslint-disable-next-line no-console
    console.error('[HealthKit] require failed:', _requireError);
    return null;
  }
}

function describe(e: unknown): string {
  if (!e) return 'unknown';
  if (typeof e === 'string') return e;
  if (typeof e === 'object' && e !== null) {
    const err = e as { message?: string; name?: string; toString?: () => string };
    return err.message ?? err.name ?? err.toString?.() ?? 'unknown';
  }
  return String(e);
}

/** Read-only diagnostic snapshot for the tester debug panel. */
export interface HealthKitNativeDebug {
  platform: string;
  moduleLoaded: boolean;
  moduleKeys: string[];
  hasIsHealthDataAvailable: boolean;
  isHealthDataAvailableResult: boolean | null;
  isHealthDataAvailableRawError: string | null;
  requireError: string | null;
  availabilityError: string | null;
  lastCallError: string | null;
  requestAuthorizationAttempted: boolean;
  lastAuthRequestAt: string | null;
  lastAuthRequestOk: boolean | null;
  lastAuthRequestReturn: string | null;
  lastAuthRequestError: string | null;
  lastCanaryReadCount: number | null;
  requestedReadTypes: string[];
}

export function getHealthKitNativeDebug(): HealthKitNativeDebug {
  const { Platform } = require('react-native');
  const hk = loadHk();
  const moduleLoaded = hk != null;
  const moduleKeys = moduleLoaded
    ? Object.keys(hk ?? {})
        .filter((k) => !k.startsWith('_'))
        .slice(0, 40)
    : [];
  const hasIsHealthDataAvailable =
    moduleLoaded && typeof hk?.isHealthDataAvailable === 'function';

  let isHealthDataAvailableResult: boolean | null = null;
  let isHealthDataAvailableRawError: string | null = null;
  if (hasIsHealthDataAvailable) {
    try {
      const v = hk.isHealthDataAvailable();
      isHealthDataAvailableResult = typeof v === 'boolean' ? v : Boolean(v);
      _isHealthDataAvailableResult = isHealthDataAvailableResult;
      _availabilityError = null;
    } catch (e) {
      isHealthDataAvailableRawError = describe(e);
      _availabilityError = isHealthDataAvailableRawError;
    }
  }

  return {
    platform: Platform.OS,
    moduleLoaded,
    moduleKeys,
    hasIsHealthDataAvailable,
    isHealthDataAvailableResult,
    isHealthDataAvailableRawError,
    requireError: _requireError,
    availabilityError: _availabilityError,
    lastCallError: _lastCallError,
    requestAuthorizationAttempted: _lastAuthRequestAt != null,
    lastAuthRequestAt: _lastAuthRequestAt,
    lastAuthRequestOk: _lastAuthRequestOk,
    lastAuthRequestReturn: _lastAuthRequestReturn,
    lastAuthRequestError: _lastAuthRequestError,
    lastCanaryReadCount: _lastCanaryReadCount,
    requestedReadTypes: _lastRequestedReadTypes,
  };
}

const QTY = {
  restingHeartRate: 'HKQuantityTypeIdentifierRestingHeartRate' as const,
  hrv: 'HKQuantityTypeIdentifierHeartRateVariabilitySDNN' as const,
  stepCount: 'HKQuantityTypeIdentifierStepCount' as const,
  activeEnergy: 'HKQuantityTypeIdentifierActiveEnergyBurned' as const,
  heartRate: 'HKQuantityTypeIdentifierHeartRate' as const,
};

const SLEEP_ID = 'HKCategoryTypeIdentifierSleepAnalysis' as const;

const METRIC_TO_QTY: Partial<Record<HealthMetricType, string>> = {
  resting_heart_rate: QTY.restingHeartRate,
  hrv: QTY.hrv,
  steps: QTY.stepCount,
  active_calories: QTY.activeEnergy,
  heart_rate: QTY.heartRate,
};

const READ_TYPES = [
  QTY.restingHeartRate,
  QTY.hrv,
  QTY.stepCount,
  QTY.activeEnergy,
  QTY.heartRate,
  'HKQuantityTypeIdentifierDistanceWalkingRunning',
  'HKQuantityTypeIdentifierBodyMass',
  // Dietary nutrition types — readable from Apple Health when any
  // source (Cronometer-exported, MyFitnessPal, manual HealthKit entry)
  // is writing them. If granted, these flow into the mobile Nutrition
  // card as an ingested source so Cronometer direct isn't required.
  'HKQuantityTypeIdentifierDietaryEnergyConsumed',
  'HKQuantityTypeIdentifierDietaryProtein',
  'HKQuantityTypeIdentifierDietaryCarbohydrates',
  'HKQuantityTypeIdentifierDietaryFatTotal',
  'HKQuantityTypeIdentifierDietaryFiber',
  'HKQuantityTypeIdentifierDietarySugar',
  'HKQuantityTypeIdentifierDietaryWater',
  'HKQuantityTypeIdentifierDietarySodium',
  SLEEP_ID,
  'HKWorkoutTypeIdentifier',
] as const;

/**
 * Sum dietary samples in a date range into a single day's macro totals.
 * HealthKit stores each food item as a separate sample, so we aggregate
 * per identifier. Returns null when the underlying query fails so the
 * caller can distinguish "no data" (empty object) from "query failed".
 */
export async function fetchDietaryDailyTotals(
  range: { start: Date; end: Date },
): Promise<{
  calories_kcal?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
  fibre_g?: number;
  sugar_g?: number;
  water_ml?: number;
  sodium_mg?: number;
  // Aligned with NutritionRecord.body_weight_kg (previously emitted
  // body_mass_kg which the nutrition store ignored).
  body_weight_kg?: number;
  // Meal-timing proxy: count of distinct dietary-energy samples in
  // the range. Apple Health writes one sample per meal log, so this
  // is a reasonable "meals logged today" signal.
  meal_count?: number;
  first_meal_at?: string;
  last_meal_at?: string;
} | null> {
  const hk = loadHk();
  if (!hk) return null;
  // Filter out zero/negative + dedup identical ts+qty to guard against
  // duplicate app writes (e.g. a third-party nutrition tracker that
  // writes the same sample twice when syncing to Apple Health).
  async function sumSamples(id: string): Promise<number> {
    try {
      const samples = await hk.queryQuantitySamples(id, {
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      if (!Array.isArray(samples)) return 0;
      const seen = new Set<string>();
      let total = 0;
      for (const s of samples) {
        const q = typeof s?.quantity === 'number' ? s.quantity : 0;
        if (!(q > 0)) continue;
        const key = `${s?.startDate ?? ''}|${q}`;
        if (seen.has(key)) continue;
        seen.add(key);
        total += q;
      }
      return total;
    } catch { return 0; }
  }
  async function latestValue(id: string): Promise<number | undefined> {
    try {
      const samples = await hk.queryQuantitySamples(id, {
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      if (!Array.isArray(samples) || samples.length === 0) return undefined;
      // Sort by endDate descending and take the most recent valid value
      const sorted = [...samples].sort((a: any, b: any) => {
        const ta = new Date(a?.endDate ?? a?.startDate ?? 0).getTime();
        const tb = new Date(b?.endDate ?? b?.startDate ?? 0).getTime();
        return tb - ta;
      });
      const s: any = sorted[0];
      return typeof s?.quantity === 'number' ? s.quantity : undefined;
    } catch { return undefined; }
  }
  async function countAndWindow(id: string): Promise<{ count: number; first: string | null; last: string | null }> {
    try {
      const samples = await hk.queryQuantitySamples(id, {
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      if (!Array.isArray(samples) || samples.length === 0) return { count: 0, first: null, last: null };
      const dates = samples
        .map((s: any) => s?.startDate)
        .filter((d: any) => typeof d === 'string' && d.length > 0)
        .sort();
      return {
        count: samples.length,
        first: dates[0] ?? null,
        last: dates[dates.length - 1] ?? null,
      };
    } catch { return { count: 0, first: null, last: null }; }
  }
  try {
    const [cal, pro, carb, fat, fibre, sugar, water, sodium, mass, mealInfo] = await Promise.all([
      sumSamples('HKQuantityTypeIdentifierDietaryEnergyConsumed'),
      sumSamples('HKQuantityTypeIdentifierDietaryProtein'),
      sumSamples('HKQuantityTypeIdentifierDietaryCarbohydrates'),
      sumSamples('HKQuantityTypeIdentifierDietaryFatTotal'),
      sumSamples('HKQuantityTypeIdentifierDietaryFiber'),
      sumSamples('HKQuantityTypeIdentifierDietarySugar'),
      sumSamples('HKQuantityTypeIdentifierDietaryWater'),
      sumSamples('HKQuantityTypeIdentifierDietarySodium'),
      latestValue('HKQuantityTypeIdentifierBodyMass'),
      countAndWindow('HKQuantityTypeIdentifierDietaryEnergyConsumed'),
    ]);
    return {
      calories_kcal: cal > 0 ? Math.round(cal) : undefined,
      protein_g: pro > 0 ? Math.round(pro * 10) / 10 : undefined,
      carbs_g: carb > 0 ? Math.round(carb * 10) / 10 : undefined,
      fat_g: fat > 0 ? Math.round(fat * 10) / 10 : undefined,
      fibre_g: fibre > 0 ? Math.round(fibre * 10) / 10 : undefined,
      sugar_g: sugar > 0 ? Math.round(sugar * 10) / 10 : undefined,
      // Apple Health's DietaryWater returns liters via the Kingstinct
      // wrapper — multiply to ml. Guard: if the value is already > 100
      // (probably ml), keep as-is.
      water_ml: water > 0 ? (water < 100 ? Math.round(water * 1000) : Math.round(water)) : undefined,
      sodium_mg: sodium > 0 ? (sodium < 10 ? Math.round(sodium * 1000) : Math.round(sodium)) : undefined,
      body_weight_kg: mass != null ? Math.round(mass * 10) / 10 : undefined,
      meal_count: mealInfo.count > 0 ? mealInfo.count : undefined,
      first_meal_at: mealInfo.first ?? undefined,
      last_meal_at: mealInfo.last ?? undefined,
    };
  } catch {
    return null;
  }
}

export class HealthKitService implements IHealthService {
  async isAvailable(): Promise<boolean> {
    const hk = loadHk();
    if (!hk) return false;
    try {
      if (typeof hk.isHealthDataAvailable === 'function') {
        const v = hk.isHealthDataAvailable();
        return typeof v === 'boolean' ? v : Boolean(v);
      }
      if (typeof hk.isHealthDataAvailableAsync === 'function') {
        return Boolean(await hk.isHealthDataAvailableAsync());
      }
      _availabilityError = 'isHealthDataAvailable not exported from module';
      return false;
    } catch (e) {
      _availabilityError = describe(e);
      // eslint-disable-next-line no-console
      console.error('[HealthKit] isHealthDataAvailable threw:', _availabilityError);
      return false;
    }
  }

  async checkPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }
    try {
      const hk = loadHk()!;
      const { AuthorizationRequestStatus } = hk;
      const status = await hk.getRequestStatusForAuthorization({
        toRead: [...READ_TYPES],
      });
      const granted = status === AuthorizationRequestStatus.unnecessary;
      return {
        available: true,
        permissions: makeAllStatus(granted ? 'authorized' : 'not_determined'),
      };
    } catch (e) {
      _lastCallError = describe(e);
      return { available: true, permissions: makeAllStatus('not_determined') };
    }
  }

  async requestPermissions(): Promise<HealthPermissions> {
    // KEY CHANGE: we no longer block on isAvailable() returning false.
    // If the native module loaded, we attempt requestAuthorization and
    // capture whatever iOS returns/throws. The user's instruction:
    // "If module is present, DO NOT block on isHealthDataAvailable=false".
    const hk = loadHk();
    _lastAuthRequestAt = new Date().toISOString();
    _lastAuthRequestOk = null;
    _lastAuthRequestReturn = null;
    _lastAuthRequestError = null;
    _lastCanaryReadCount = null;
    _lastRequestedReadTypes = [...READ_TYPES];

    if (!hk) {
      // Truly no module — nothing we can do at runtime.
      _lastAuthRequestOk = false;
      _lastAuthRequestError = _requireError ?? 'native module not loaded';
      return { available: false, permissions: makeAllStatus('unavailable') };
    }

    // Run the availability probe separately — purely informational.
    // The decision to attempt auth is based on module presence only.
    try {
      if (typeof hk.isHealthDataAvailable === 'function') {
        const v = hk.isHealthDataAvailable();
        _isHealthDataAvailableResult = typeof v === 'boolean' ? v : Boolean(v);
      }
    } catch (e) {
      _availabilityError = describe(e);
    }

    try {
      const result = await hk.requestAuthorization({ toRead: [...READ_TYPES] });
      _lastAuthRequestOk = true;
      _lastAuthRequestReturn = typeof result === 'boolean' ? String(result) : describe(result);
    } catch (e) {
      _lastAuthRequestOk = false;
      _lastAuthRequestError = describe(e);
      _lastCallError = `requestAuthorization: ${_lastAuthRequestError}`;
      // eslint-disable-next-line no-console
      console.error('[HealthKit] requestAuthorization threw:', _lastAuthRequestError);
      // We still return available=true here so the store doesn't block
      // a subsequent canary-read attempt. Permissions are 'denied'
      // until user grants + a successful read returns data.
      return { available: true, permissions: makeAllStatus('denied') };
    }

    // Canary read: last 7 days of steps. If this returns samples, user
    // granted at least one read permission; we optimistically mark all
    // as authorized. If 0 or throws, we mark not_determined.
    try {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      const samples = await hk.queryQuantitySamples(QTY.stepCount, {
        limit: 10,
        filter: { date: { startDate: start, endDate: end } },
      });
      _lastCanaryReadCount = Array.isArray(samples) ? samples.length : 0;
    } catch (e) {
      _lastCanaryReadCount = 0;
      _lastCallError = `canary-read: ${describe(e)}`;
    }

    const canaryGranted = (_lastCanaryReadCount ?? 0) > 0;
    return {
      available: true,
      permissions: makeAllStatus(canaryGranted ? 'authorized' : 'not_determined'),
    };
  }

  async fetchSamples(
    metric: HealthMetricType,
    range: DateRange,
  ): Promise<RawHealthSample[]> {
    const identifier = METRIC_TO_QTY[metric];
    if (!identifier) return [];
    const hk = loadHk();
    if (!hk) return [];
    try {
      const results = await hk.queryQuantitySamples(identifier as any, {
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      return results.map((sample: any) => ({
        metric,
        value: sample.quantity,
        unit: sample.unit ?? '',
        startDate: new Date(sample.startDate).toISOString(),
        endDate: new Date(sample.endDate).toISOString(),
        source: sample.sourceRevision?.source?.name,
      }));
    } catch (e) {
      _lastCallError = describe(e);
      return [];
    }
  }

  async fetchWorkouts(range: DateRange): Promise<RawWorkoutSample[]> {
    const hk = loadHk();
    if (!hk) return [];
    try {
      const { WorkoutActivityType } = hk;
      const results = await hk.queryWorkoutSamples({
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      return results.map((w: any) => {
        const startMs = new Date(w.startDate).getTime();
        const endMs = new Date(w.endDate).getTime();
        return {
          type: String(w.workoutActivityType ?? 'unknown'),
          name: workoutTypeName(w.workoutActivityType, WorkoutActivityType),
          duration_min: Math.round((endMs - startMs) / 60_000),
          calories: w.totalEnergyBurned?.quantity,
          distance_m: w.totalDistance?.quantity
            ? Math.round(w.totalDistance.quantity * 1000)
            : undefined,
          startDate: new Date(w.startDate).toISOString(),
          endDate: new Date(w.endDate).toISOString(),
          source: w.sourceRevision?.source?.name,
          source_id: w.uuid,
        };
      });
    } catch (e) {
      _lastCallError = describe(e);
      return [];
    }
  }

  async fetchSleep(range: DateRange): Promise<RawSleepSample[]> {
    const hk = loadHk();
    if (!hk) return [];
    try {
      const results = await hk.queryCategorySamples(SLEEP_ID, {
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      return results.map((s: any) => ({
        stage: mapSleepValue(s.value),
        startDate: new Date(s.startDate).toISOString(),
        endDate: new Date(s.endDate).toISOString(),
        source: s.sourceRevision?.source?.name,
      }));
    } catch (e) {
      _lastCallError = describe(e);
      return [];
    }
  }
}

function makeAllStatus(
  status: PermissionStatus,
): Record<HealthMetricType, PermissionStatus> {
  return {
    heart_rate: status,
    resting_heart_rate: status,
    hrv: status,
    sleep: status,
    steps: status,
    active_calories: status,
    workouts: status,
  };
}

function mapSleepValue(value: number): string {
  switch (value) {
    case 0: return 'in_bed';
    case 1: return 'asleep';
    case 2: return 'awake';
    case 3: return 'deep';
    case 4: return 'light';
    case 5: return 'rem';
    default: return 'asleep';
  }
}

function workoutTypeName(type: number | undefined, WAT: any): string {
  if (type == null) return 'Workout';
  // Map every activity type we care about. HealthKit's enum numbers
  // are stable, so fall back to a numeric lookup when the JS enum is
  // not exposed by the native bridge. Source: Apple HKWorkoutActivityType.
  const NUMERIC: Record<number, string> = {
    12: 'Boxing',
    13: 'Indoor bike',    // cycling — most often "assault bike" or spin in practice
    15: 'Elliptical',
    24: 'Functional strength',
    28: 'HIIT',
    30: 'Martial arts',
    31: 'Mind & body',
    34: 'Paddle sports',
    37: 'Cross training',
    44: 'Rowing',
    46: 'Skating',
    53: 'Strength training',
    57: 'Swimming',
    58: 'Strength training',
    59: 'Mixed cardio',
    63: 'Walking',
    72: 'Hiking',
    74: 'HIIT',
    79: 'Yoga',
    83: 'Running',
    88: 'Wrestling',
    95: 'Climbing',
    3000: 'Other workout',
  };
  if (NUMERIC[type]) return NUMERIC[type];
  const viaEnum: Partial<Record<number, string>> = WAT ? {
    [WAT.martialArts]: 'Martial arts',
    [WAT.wrestling]: 'Wrestling',
    [WAT.running]: 'Running',
    [WAT.cycling]: 'Indoor bike',
    [WAT.swimming]: 'Swimming',
    [WAT.yoga]: 'Yoga',
    [WAT.functionalStrengthTraining]: 'Strength training',
    [WAT.traditionalStrengthTraining]: 'Strength training',
    [WAT.walking]: 'Walking',
    [WAT.hiking]: 'Hiking',
    [WAT.highIntensityIntervalTraining]: 'HIIT',
    [WAT.mixedCardio]: 'Mixed cardio',
    [WAT.crossTraining]: 'Cross training',
    [WAT.rowing]: 'Rowing',
    [WAT.elliptical]: 'Elliptical',
    [WAT.kickboxing]: 'Kickboxing',
    [WAT.boxing]: 'Boxing',
    [WAT.climbing]: 'Climbing',
    [WAT.other]: 'Other workout',
  } : {};
  // Drop the raw numeric code entirely — it was showing as "Workout (3000)"
  return viaEnum[type] ?? 'Workout';
}
