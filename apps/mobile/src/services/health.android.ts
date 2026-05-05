/**
 * Android Health Connect implementation of IHealthService.
 *
 * ALL native imports are lazy (inside methods) to prevent Expo Go crash.
 * react-native-health-connect crashes at import time in Expo Go.
 *
 * REQUIRES: expo prebuild + Health Connect app on device.
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

/** Lazy-load the native module */
function hc() {
  return require('react-native-health-connect');
}

const HC_PERMISSIONS = [
  { accessType: 'read' as const, recordType: 'RestingHeartRate' as const },
  { accessType: 'read' as const, recordType: 'HeartRateVariabilityRmssd' as const },
  { accessType: 'read' as const, recordType: 'Steps' as const },
  { accessType: 'read' as const, recordType: 'ActiveCaloriesBurned' as const },
  { accessType: 'read' as const, recordType: 'HeartRate' as const },
  { accessType: 'read' as const, recordType: 'SleepSession' as const },
  { accessType: 'read' as const, recordType: 'ExerciseSession' as const },
];

/**
 * Health Connect history access on Android 14+.
 *
 * Default Health Connect read access is limited to ~30 days. The
 * `PERMISSION_READ_HEALTH_DATA_HISTORY` permission unlocks full
 * history reads. It's a runtime permission the user must explicitly
 * grant — we cannot silently upgrade.
 *
 * On Android 13 and below, Health Connect may be the standalone app
 * and this permission may not exist — we catch gracefully.
 */
const HC_HISTORY_PERMISSION_NAME = 'android.permission.health.READ_HEALTH_DATA_HISTORY';

export class HealthConnectService implements IHealthService {
  private initialized = false;
  /** Whether full-history permission was granted (Android 14+). */
  private historyPermissionGranted = false;

  private async ensureInit(): Promise<boolean> {
    if (this.initialized) return true;
    try {
      const result = await hc().initialize();
      this.initialized = result;
      return result;
    } catch {
      return false;
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      const { SdkAvailabilityStatus } = hc();
      const status = await hc().getSdkStatus();
      return status === SdkAvailabilityStatus.SDK_AVAILABLE;
    } catch {
      return false;
    }
  }

  /**
   * Detailed availability probe so the UI can route to the right
   * install/update hint instead of saying "unavailable" generically.
   * Returns a stable string code that the SamsungHealthCard /
   * Health Connect surface keys off:
   *
   *   - 'available'                    → SDK ready, proceed normally
   *   - 'provider_update_required'     → Health Connect installed
   *                                      but APK version too old;
   *                                      route user to Play Store
   *                                      to update
   *   - 'sdk_unavailable'              → not installed at all on
   *                                      Android 13 and below; route
   *                                      to install Health Connect
   *   - 'unknown'                      → probe threw / native module
   *                                      not linked
   */
  async getAvailabilityDetail(): Promise<{
    code: 'available' | 'provider_update_required' | 'sdk_unavailable' | 'unknown';
    rawStatus?: string | null;
  }> {
    try {
      const { SdkAvailabilityStatus } = hc();
      const status = await hc().getSdkStatus();
      // react-native-health-connect exposes the same constant set
      // as the Android Health Connect SDK. Map to our stable codes.
      if (status === SdkAvailabilityStatus.SDK_AVAILABLE) return { code: 'available', rawStatus: 'SDK_AVAILABLE' };
      if (status === SdkAvailabilityStatus.SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED) {
        return { code: 'provider_update_required', rawStatus: 'SDK_UNAVAILABLE_PROVIDER_UPDATE_REQUIRED' };
      }
      if (status === SdkAvailabilityStatus.SDK_UNAVAILABLE) return { code: 'sdk_unavailable', rawStatus: 'SDK_UNAVAILABLE' };
      return { code: 'unknown', rawStatus: typeof status === 'string' ? status : null };
    } catch {
      return { code: 'unknown', rawStatus: null };
    }
  }

  async checkPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }
    // Actually check which permissions are currently granted.
    // react-native-health-connect exposes getGrantedPermissions()
    // which returns the list of already-granted record types.
    await this.ensureInit();
    try {
      const granted = await hc().getGrantedPermissions();
      if (!granted || !Array.isArray(granted) || granted.length === 0) {
        return { available: true, permissions: makeAllStatus('not_determined') };
      }
      const result = makeAllStatus('denied');
      for (const p of granted) {
        const metric = recordTypeToMetric(p.recordType);
        if (metric && p.accessType === 'read') result[metric] = 'authorized';
      }
      return { available: true, permissions: result };
    } catch {
      // Fallback: can't determine — report not_determined
      return { available: true, permissions: makeAllStatus('not_determined') };
    }
  }

  async requestPermissions(): Promise<HealthPermissions> {
    const available = await this.isAvailable();
    if (!available) {
      return { available: false, permissions: makeAllStatus('unavailable') };
    }
    await this.ensureInit();
    try {
      const granted = await hc().requestPermission(HC_PERMISSIONS);
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

  /**
   * Request the background/history permission that unlocks reads
   * beyond the default ~30-day window. Android 14+ only.
   *
   * Returns true if the permission was granted, false otherwise.
   * On Android 13 and below this always returns false gracefully
   * (the permission doesn't exist in the manifest).
   */
  async requestHistoryPermission(): Promise<boolean> {
    try {
      await this.ensureInit();
      // react-native-health-connect exposes requestPermission for
      // standard record types. For the special history permission,
      // we try to request it via the same API surface. If the
      // library version doesn't support it, we fall back to PermissionsAndroid.
      try {
        const { PermissionsAndroid, Platform } = require('react-native');
        if (Platform.Version < 34) {
          // Android 13 and below: history permission doesn't exist.
          this.historyPermissionGranted = false;
          return false;
        }
        const result = await PermissionsAndroid.request(HC_HISTORY_PERMISSION_NAME);
        this.historyPermissionGranted = result === PermissionsAndroid.RESULTS.GRANTED;
        return this.historyPermissionGranted;
      } catch {
        this.historyPermissionGranted = false;
        return false;
      }
    } catch {
      this.historyPermissionGranted = false;
      return false;
    }
  }

  /**
   * Check (without requesting) whether history permission is granted.
   */
  async checkHistoryPermission(): Promise<boolean> {
    try {
      const { PermissionsAndroid, Platform } = require('react-native');
      if (Platform.Version < 34) return false;
      const result = await PermissionsAndroid.check(HC_HISTORY_PERMISSION_NAME);
      this.historyPermissionGranted = result;
      return result;
    } catch {
      return false;
    }
  }

  /** Whether the last check/request found history permission granted. */
  hasHistoryPermission(): boolean {
    return this.historyPermissionGranted;
  }

  /**
   * Maximum days back this service can read, based on history
   * permission state. 30 is the safe default; 90 when history
   * permission is granted (arbitrary upper bound for the backlog
   * analysis — Health Connect itself may have data going further).
   */
  getMaxHistoryDays(): number {
    return this.historyPermissionGranted ? 90 : 30;
  }

  async fetchSamples(
    metric: HealthMetricType,
    range: DateRange,
  ): Promise<RawHealthSample[]> {
    await this.ensureInit();
    const recordType = metricToRecordType(metric);
    if (!recordType) return [];
    try {
      const { records } = await hc().readRecords(recordType as any, {
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
      const { records } = await hc().readRecords('ExerciseSession', {
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
      const { records } = await hc().readRecords('SleepSession', {
        timeRangeFilter: {
          operator: 'between',
          startTime: range.start.toISOString(),
          endTime: range.end.toISOString(),
        },
      });
      const samples: RawSleepSample[] = [];
      for (const session of records as any[]) {
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
    '1': 'awake', '2': 'asleep', '3': 'light',
    '4': 'light', '5': 'deep', '6': 'rem', '7': 'awake',
  };
  return stageMap[String(stage)] ?? 'asleep';
}

function exerciseTypeName(type?: number): string {
  if (type == null) return 'Workout';
  // Health Connect exerciseType enum — the most common values.
  // No numeric fallback labels (those leaked as "Exercise (62)" in UI);
  // unknown types degrade to a generic "Workout" string.
  const names: Record<number, string> = {
    2: 'Badminton',
    7: 'Boxing',
    8: 'Calisthenics',
    13: 'Cross training',
    14: 'Cycling',
    24: 'HIIT',
    25: 'Hiking',
    28: 'Indoor bike',
    29: 'Martial arts',
    34: 'Paddleboarding',
    37: 'Rowing',
    48: 'Rugby',
    56: 'Running',
    60: 'Strength training',
    61: 'Strength training',
    62: 'Stretching',
    65: 'Surfing',
    75: 'Swimming',
    76: 'Wrestling',
    79: 'Walking',
    80: 'Cycling',
    81: 'Yoga',
  };
  return names[type] ?? 'Workout';
}
