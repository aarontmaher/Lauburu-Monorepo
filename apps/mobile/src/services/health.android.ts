/**
 * Android Health Connect implementation of IHealthService.
 * Uses react-native-health-connect.
 *
 * REQUIRES: expo prebuild + Health Connect app installed on device.
 * EMULATOR: Health Connect available on Android 14+ emulators. Add sample data
 *   in Health Connect app > Data and access > Browse data.
 * DEVICE: Full Health Connect access. On Android <14, user must install HC from Play Store.
 *
 * WARNING: If user denies permissions twice, app is permanently locked out.
 * Handle denial gracefully and explain before re-requesting.
 */
import {
  initialize,
  requestPermission,
  readRecords,
  getSdkStatus,
  SdkAvailabilityStatus,
} from 'react-native-health-connect';
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

/** Permissions we need from Health Connect */
const HC_PERMISSIONS = [
  { accessType: 'read' as const, recordType: 'RestingHeartRate' as const },
  { accessType: 'read' as const, recordType: 'HeartRateVariabilityRmssd' as const },
  { accessType: 'read' as const, recordType: 'Steps' as const },
  { accessType: 'read' as const, recordType: 'ActiveCaloriesBurned' as const },
  { accessType: 'read' as const, recordType: 'HeartRate' as const },
  { accessType: 'read' as const, recordType: 'SleepSession' as const },
  { accessType: 'read' as const, recordType: 'ExerciseSession' as const },
];

export class HealthConnectService implements IHealthService {
  private initialized = false;

  private async ensureInit(): Promise<boolean> {
    if (this.initialized) return true;
    try {
      const result = await initialize();
      this.initialized = result;
      return result;
    } catch {
      return false;
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      const status = await getSdkStatus();
      return status === SdkAvailabilityStatus.SDK_AVAILABLE;
    } catch {
      return false;
    }
  }

  async checkPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }

    // Health Connect doesn't have a "check without request" API in the RN lib.
    // We return not_determined and let the request flow handle it.
    return { available: true, permissions: makeAllStatus('not_determined') };
  }

  async requestPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }

    await this.ensureInit();

    try {
      const granted = await requestPermission(HC_PERMISSIONS);
      // Map granted permissions to our metric types
      const result = makeAllStatus('denied');
      for (const p of granted) {
        const metric = recordTypeToMetric(p.recordType);
        if (metric) result[metric] = 'authorized';
      }
      return { available: true, permissions: result };
    } catch {
      return { available: true, permissions: makeAllStatus('denied') };
    }
  }

  async fetchSamples(
    metric: HealthMetricType,
    range: DateRange,
  ): Promise<RawHealthSample[]> {
    await this.ensureInit();
    const recordType = metricToRecordType(metric);
    if (!recordType) return [];

    try {
      const { records } = await readRecords(recordType as any, {
        timeRangeFilter: {
          operator: 'between',
          startTime: range.start.toISOString(),
          endTime: range.end.toISOString(),
        },
      });

      return (records as any[]).map((r) => ({
        metric,
        value: extractValue(r, metric),
        unit: extractUnit(metric),
        startDate: r.startTime ?? r.time ?? range.start.toISOString(),
        endDate: r.endTime ?? r.time ?? range.end.toISOString(),
        source: r.metadata?.dataOrigin,
      }));
    } catch {
      return [];
    }
  }

  async fetchWorkouts(range: DateRange): Promise<RawWorkoutSample[]> {
    await this.ensureInit();

    try {
      const { records } = await readRecords('ExerciseSession', {
        timeRangeFilter: {
          operator: 'between',
          startTime: range.start.toISOString(),
          endTime: range.end.toISOString(),
        },
      });

      return (records as any[]).map((r) => {
        const startMs = new Date(r.startTime).getTime();
        const endMs = new Date(r.endTime).getTime();
        return {
          type: String(r.exerciseType ?? 'unknown'),
          name: r.title ?? exerciseTypeName(r.exerciseType),
          duration_min: Math.round((endMs - startMs) / 60_000),
          distance_m: r.segments?.[0]?.distance?.inMeters,
          startDate: r.startTime,
          endDate: r.endTime,
          source: r.metadata?.dataOrigin,
          source_id: r.metadata?.id,
        };
      });
    } catch {
      return [];
    }
  }

  async fetchSleep(range: DateRange): Promise<RawSleepSample[]> {
    await this.ensureInit();

    try {
      const { records } = await readRecords('SleepSession', {
        timeRangeFilter: {
          operator: 'between',
          startTime: range.start.toISOString(),
          endTime: range.end.toISOString(),
        },
      });

      const samples: RawSleepSample[] = [];
      for (const session of records as any[]) {
        // Health Connect sleep sessions contain stages
        if (session.stages && Array.isArray(session.stages)) {
          for (const stage of session.stages) {
            samples.push({
              stage: mapHCStage(stage.stage),
              startDate: stage.startTime,
              endDate: stage.endTime,
              source: session.metadata?.dataOrigin,
            });
          }
        } else {
          // No stage detail — treat entire session as asleep
          samples.push({
            stage: 'asleep',
            startDate: session.startTime,
            endDate: session.endTime,
            source: session.metadata?.dataOrigin,
          });
        }
      }
      return samples;
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

function metricToRecordType(metric: HealthMetricType): string | null {
  const map: Record<string, string> = {
    resting_heart_rate: 'RestingHeartRate',
    hrv: 'HeartRateVariabilityRmssd',
    steps: 'Steps',
    active_calories: 'ActiveCaloriesBurned',
    heart_rate: 'HeartRate',
  };
  return map[metric] ?? null;
}

function recordTypeToMetric(recordType: string): HealthMetricType | null {
  const map: Record<string, HealthMetricType> = {
    RestingHeartRate: 'resting_heart_rate',
    HeartRateVariabilityRmssd: 'hrv',
    Steps: 'steps',
    ActiveCaloriesBurned: 'active_calories',
    HeartRate: 'heart_rate',
    SleepSession: 'sleep',
    ExerciseSession: 'workouts',
  };
  return map[recordType] ?? null;
}

function extractValue(record: any, metric: HealthMetricType): number {
  switch (metric) {
    case 'resting_heart_rate':
    case 'heart_rate':
      return record.beatsPerMinute ?? record.bpm ?? 0;
    case 'hrv':
      return record.heartRateVariabilityMillis ?? 0;
    case 'steps':
      return record.count ?? 0;
    case 'active_calories':
      return record.energy?.inKilocalories ?? 0;
    default:
      return 0;
  }
}

function extractUnit(metric: HealthMetricType): string {
  switch (metric) {
    case 'resting_heart_rate':
    case 'heart_rate':
      return 'bpm';
    case 'hrv':
      return 'ms';
    case 'steps':
      return 'count';
    case 'active_calories':
      return 'kcal';
    default:
      return '';
  }
}

function mapHCStage(stage: number | string): string {
  const stageMap: Record<string, string> = {
    '1': 'awake',
    '2': 'asleep', // sleeping
    '3': 'light',  // out_of_bed → light (approximate)
    '4': 'light',
    '5': 'deep',
    '6': 'rem',
    '7': 'awake', // awake_in_bed
  };
  return stageMap[String(stage)] ?? 'asleep';
}

function exerciseTypeName(type?: number): string {
  if (type == null) return 'Unknown';
  const names: Record<number, string> = {
    2: 'Badminton', 29: 'Martial Arts', 56: 'Running',
    61: 'Strength Training', 75: 'Swimming', 79: 'Walking',
    80: 'Cycling', 76: 'Wrestling',
  };
  return names[type] ?? `Exercise (${type})`;
}
