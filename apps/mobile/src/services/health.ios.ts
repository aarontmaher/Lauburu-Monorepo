/**
 * iOS HealthKit implementation of IHealthService.
 *
 * ALL native imports are lazy (inside methods) to prevent Expo Go crash.
 * @kingstinct/react-native-healthkit uses NitroModules which crash at
 * import time in Expo Go. By deferring require() to method calls,
 * the module is never loaded unless actually used in a dev build.
 *
 * REQUIRES: expo prebuild + Xcode HealthKit capability enabled.
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

/** Lazy-load the native module. Only called in dev builds, never in Expo Go. */
function hk() {
  return require('@kingstinct/react-native-healthkit');
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
  SLEEP_ID,
  'HKWorkoutTypeIdentifier',
] as const;

export class HealthKitService implements IHealthService {
  async isAvailable(): Promise<boolean> {
    try {
      return await hk().isHealthDataAvailable();
    } catch {
      return false;
    }
  }

  async checkPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }
    try {
      const { AuthorizationRequestStatus } = hk();
      const status = await hk().getRequestStatusForAuthorization({
        toRead: [...READ_TYPES],
      });
      const granted = status === AuthorizationRequestStatus.unnecessary;
      return {
        available: true,
        permissions: makeAllStatus(granted ? 'authorized' : 'not_determined'),
      };
    } catch {
      return { available: true, permissions: makeAllStatus('not_determined') };
    }
  }

  async requestPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }
    try {
      await hk().requestAuthorization({ toRead: [...READ_TYPES] });
      return this.checkPermissions();
    } catch {
      return { available: true, permissions: makeAllStatus('denied') };
    }
  }

  async fetchSamples(
    metric: HealthMetricType,
    range: DateRange,
  ): Promise<RawHealthSample[]> {
    const identifier = METRIC_TO_QTY[metric];
    if (!identifier) return [];
    try {
      const results = await hk().queryQuantitySamples(identifier as any, {
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
    } catch {
      return [];
    }
  }

  async fetchWorkouts(range: DateRange): Promise<RawWorkoutSample[]> {
    try {
      const { WorkoutActivityType } = hk();
      const results = await hk().queryWorkoutSamples({
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
    } catch {
      return [];
    }
  }

  async fetchSleep(range: DateRange): Promise<RawSleepSample[]> {
    try {
      const results = await hk().queryCategorySamples(SLEEP_ID, {
        limit: 0,
        filter: { date: { startDate: range.start, endDate: range.end } },
      });
      return results.map((s: any) => ({
        stage: mapSleepValue(s.value),
        startDate: new Date(s.startDate).toISOString(),
        endDate: new Date(s.endDate).toISOString(),
        source: s.sourceRevision?.source?.name,
      }));
    } catch {
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
  if (type == null) return 'Unknown';
  const names: Partial<Record<number, string>> = {
    [WAT.martialArts]: 'Martial Arts',
    [WAT.wrestling]: 'Wrestling',
    [WAT.running]: 'Running',
    [WAT.cycling]: 'Cycling',
    [WAT.swimming]: 'Swimming',
    [WAT.yoga]: 'Yoga',
    [WAT.functionalStrengthTraining]: 'Strength Training',
    [WAT.traditionalStrengthTraining]: 'Strength Training',
    [WAT.walking]: 'Walking',
    [WAT.hiking]: 'Hiking',
  };
  return names[type] ?? `Workout (${type})`;
}
