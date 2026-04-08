/**
 * Normalize raw native health data into the canonical DailyMetrics shape.
 * Matches website's fromAppleHealth() and normalization patterns exactly.
 *
 * This is the single point where platform-specific raw data becomes
 * the unified shape that both the backend (Supabase) and AI layer consume.
 */
import { HealthProvider } from '../constants/enums';
import type {
  DailyMetrics,
  RawHealthSample,
  RawWorkoutSample,
  RawSleepSample,
  Workout,
} from '../types/health';

/** Grappling workout type detection — matches website logic */
const GRAPPLING_KEYWORDS = ['martial', 'wrestling', 'grappling', 'bjj', 'jiu'];

function isGrapplingWorkout(name: string): boolean {
  const lower = name.toLowerCase();
  return GRAPPLING_KEYWORDS.some((kw) => lower.includes(kw));
}

/** Format a Date to YYYY-MM-DD */
function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Group samples by date */
function groupByDate<T extends { startDate: string }>(
  samples: T[],
): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const s of samples) {
    const date = s.startDate.slice(0, 10);
    const arr = map.get(date) ?? [];
    arr.push(s);
    map.set(date, arr);
  }
  return map;
}

/** Compute average of non-null numbers */
function avg(nums: (number | undefined | null)[]): number | undefined {
  const valid = nums.filter((n): n is number => n != null);
  if (valid.length === 0) return undefined;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

/** Sum non-null numbers */
function sum(nums: (number | undefined | null)[]): number | undefined {
  const valid = nums.filter((n): n is number => n != null);
  if (valid.length === 0) return undefined;
  return valid.reduce((a, b) => a + b, 0);
}

/** Latest sample value for a metric on a given date */
function latestValue(
  samples: RawHealthSample[],
  metric: string,
): number | undefined {
  const matching = samples
    .filter((s) => s.metric === metric)
    .sort((a, b) => b.endDate.localeCompare(a.endDate));
  return matching[0]?.value;
}

/**
 * Build a single DailyMetrics record from raw samples for one day.
 * This is provider-agnostic — works for both HealthKit and Health Connect
 * since both are normalized to RawHealthSample/RawWorkoutSample/RawSleepSample
 * before reaching this function.
 */
export function normalizeDayFromSamples(
  userId: string,
  date: string,
  provider: typeof HealthProvider.APPLE_HEALTH | typeof HealthProvider.MANUAL,
  samples: RawHealthSample[],
  workouts: RawWorkoutSample[],
  sleepSessions: RawSleepSample[],
): DailyMetrics {
  // Heart metrics
  const restingHr = latestValue(samples, 'resting_heart_rate');
  const hrv = latestValue(samples, 'hrv');

  // Steps & calories
  const steps = sum(samples.filter((s) => s.metric === 'steps').map((s) => s.value));
  const activeCal = sum(
    samples.filter((s) => s.metric === 'active_calories').map((s) => s.value),
  );

  // Sleep: total asleep hours
  const asleepMinutes = sleepSessions
    .filter((s) => s.stage !== 'awake' && s.stage !== 'in_bed')
    .reduce((total, s) => {
      const start = new Date(s.startDate).getTime();
      const end = new Date(s.endDate).getTime();
      return total + (end - start) / 60_000;
    }, 0);
  const sleepHours = asleepMinutes > 0 ? Math.round((asleepMinutes / 60) * 100) / 100 : undefined;

  // Sleep stages
  const deepMinutes = sleepSessions
    .filter((s) => s.stage === 'deep')
    .reduce((t, s) => t + (new Date(s.endDate).getTime() - new Date(s.startDate).getTime()) / 60_000, 0);
  const remMinutes = sleepSessions
    .filter((s) => s.stage === 'rem')
    .reduce((t, s) => t + (new Date(s.endDate).getTime() - new Date(s.startDate).getTime()) / 60_000, 0);

  // Daily strain proxy — matches website: active_calories / 100, capped at 21
  const dailyStrain =
    activeCal != null ? Math.min(Math.round((activeCal / 100) * 10) / 10, 21) : undefined;

  // Normalize workouts
  const normalizedWorkouts: Workout[] = workouts.map((w) => ({
    type: w.type,
    sport_label: w.name,
    duration_min: w.duration_min,
    calories: w.calories,
    avg_hr: w.avg_hr,
    max_hr: w.max_hr,
    is_grappling: isGrapplingWorkout(w.name),
  }));

  return {
    user_id: userId,
    date,
    provider,
    recovery_score: undefined, // Apple Health / Health Connect have no native recovery score
    readiness_label: 'unknown',
    hrv_ms: hrv,
    resting_hr: restingHr,
    sleep_hours: sleepHours,
    sws_hours: deepMinutes > 0 ? Math.round((deepMinutes / 60) * 100) / 100 : undefined,
    rem_hours: remMinutes > 0 ? Math.round((remMinutes / 60) * 100) / 100 : undefined,
    daily_strain: dailyStrain,
    step_count: steps != null ? Math.round(steps) : undefined,
    active_calories: activeCal != null ? Math.round(activeCal) : undefined,
    workouts: normalizedWorkouts.length > 0 ? normalizedWorkouts : undefined,
    data_source: provider === 'apple_health' ? 'apple_health_native' : 'health_connect_native',
    imported_at: new Date().toISOString(),
    last_updated: new Date().toISOString(),
  };
}

/**
 * Normalize multiple days of raw health data into DailyMetrics[].
 * Groups all samples by date, then normalizes each day.
 */
export function normalizeHealthData(
  userId: string,
  provider: typeof HealthProvider.APPLE_HEALTH | typeof HealthProvider.MANUAL,
  samples: RawHealthSample[],
  workouts: RawWorkoutSample[],
  sleepSessions: RawSleepSample[],
): DailyMetrics[] {
  // Collect all unique dates
  const dates = new Set<string>();
  for (const s of samples) dates.add(s.startDate.slice(0, 10));
  for (const w of workouts) dates.add(w.startDate.slice(0, 10));
  for (const s of sleepSessions) dates.add(s.startDate.slice(0, 10));

  const samplesByDate = groupByDate(samples);
  const workoutsByDate = groupByDate(workouts);
  const sleepByDate = groupByDate(sleepSessions);

  const sortedDates = Array.from(dates).sort();

  return sortedDates.map((date) =>
    normalizeDayFromSamples(
      userId,
      date,
      provider,
      samplesByDate.get(date) ?? [],
      workoutsByDate.get(date) ?? [],
      sleepByDate.get(date) ?? [],
    ),
  );
}
