/**
 * iOS HealthKit implementation of IHealthService.
 * Uses @kingstinct/react-native-healthkit.
 *
 * REQUIRES: expo prebuild + Xcode HealthKit capability enabled.
 * SIMULATOR: HealthKit is available but has no real data. Add sample data in
 *   Health app > Browse > category > Add Data.
 * DEVICE: Full HealthKit access with real wearable data.
 */
import {
  isHealthDataAvailable,
  requestAuthorization,
  getRequestStatusForAuthorization,
  queryQuantitySamples,
  queryCategorySamples,
  queryWorkoutSamples,
  AuthorizationRequestStatus,
  WorkoutActivityType,
} from '@kingstinct/react-native-healthkit';
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

/** HealthKit quantity type identifier strings */
const QTY = {
  restingHeartRate: 'HKQuantityTypeIdentifierRestingHeartRate' as const,
  hrv: 'HKQuantityTypeIdentifierHeartRateVariabilitySDNN' as const,
  stepCount: 'HKQuantityTypeIdentifierStepCount' as const,
  activeEnergy: 'HKQuantityTypeIdentifierActiveEnergyBurned' as const,
  heartRate: 'HKQuantityTypeIdentifierHeartRate' as const,
};

const SLEEP_ID = 'HKCategoryTypeIdentifierSleepAnalysis' as const;

/** Map our metric types to HealthKit identifiers */
const METRIC_TO_QTY: Partial<Record<HealthMetricType, string>> = {
  resting_heart_rate: QTY.restingHeartRate,
  hrv: QTY.hrv,
  steps: QTY.stepCount,
  active_calories: QTY.activeEnergy,
  heart_rate: QTY.heartRate,
};

/** All types we request read access for */
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
      return await isHealthDataAvailable();
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
      const status = await getRequestStatusForAuthorization({
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
      await requestAuthorization({ toRead: [...READ_TYPES] });
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
      const results = await queryQuantitySamples(identifier as any, {
        limit: 0, // 0 = no limit
        filter: {
          date: { startDate: range.start, endDate: range.end },
        },
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
      const results = await queryWorkoutSamples({
        limit: 0,
        filter: {
          date: { startDate: range.start, endDate: range.end },
        },
      });

      return results.map((w: any) => {
        const startMs = new Date(w.startDate).getTime();
        const endMs = new Date(w.endDate).getTime();
        return {
          type: String(w.workoutActivityType ?? 'unknown'),
          name: workoutTypeName(w.workoutActivityType),
          duration_min: Math.round((endMs - startMs) / 60_000),
          calories: w.totalEnergyBurned?.quantity,
          distance_m: w.totalDistance?.quantity
            ? Math.round(w.totalDistance.quantity * 1000) // km → m
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
      const results = await queryCategorySamples(SLEEP_ID, {
        limit: 0,
        filter: {
          date: { startDate: range.start, endDate: range.end },
        },
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

// --- Helpers ---

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

function workoutTypeName(type?: number): string {
  if (type == null) return 'Unknown';
  const names: Partial<Record<number, string>> = {
    [WorkoutActivityType.martialArts]: 'Martial Arts',
    [WorkoutActivityType.wrestling]: 'Wrestling',
    [WorkoutActivityType.running]: 'Running',
    [WorkoutActivityType.cycling]: 'Cycling',
    [WorkoutActivityType.swimming]: 'Swimming',
    [WorkoutActivityType.yoga]: 'Yoga',
    [WorkoutActivityType.functionalStrengthTraining]: 'Strength Training',
    [WorkoutActivityType.traditionalStrengthTraining]: 'Strength Training',
    [WorkoutActivityType.walking]: 'Walking',
    [WorkoutActivityType.hiking]: 'Hiking',
  };
  return names[type] ?? `Workout (${type})`;
}
