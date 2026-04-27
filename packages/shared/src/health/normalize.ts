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

function providerDataSource(
  provider:
    | typeof HealthProvider.APPLE_HEALTH
    | typeof HealthProvider.HEALTH_CONNECT
    | typeof HealthProvider.MANUAL,
): string {
  switch (provider) {
    case HealthProvider.APPLE_HEALTH:
      return 'apple_health_native';
    case HealthProvider.HEALTH_CONNECT:
      return 'health_connect_native';
    case HealthProvider.MANUAL:
    default:
      return 'manual';
  }
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
  provider:
    | typeof HealthProvider.APPLE_HEALTH
    | typeof HealthProvider.HEALTH_CONNECT
    | typeof HealthProvider.MANUAL,
  samples: RawHealthSample[],
  workouts: RawWorkoutSample[],
  sleepSessions: RawSleepSample[],
): DailyMetrics {
  // Heart metrics
  const restingHr = latestValue(samples, 'resting_heart_rate');
  const hrv = latestValue(samples, 'hrv');

  // Steps & calories
  const steps = sum(samples.filter((s) => s.metric === 'steps').map((s) => s.value));
  // Active calories: HealthKit returns many overlapping samples for the
  // same time interval (ActivityRing minute-samples PLUS per-workout
  // totalEnergyBurned PLUS third-party apps writing their own summary
  // samples). Naive sum double- or triple-counts, producing absurd
  // daily totals (e.g. 5400+ kcal for a normal training day).
  //
  // Mitigation:
  //   1. Group samples into non-overlapping time windows; within an
  //      overlapping window, take the MAX single-source contribution
  //      rather than summing all sources.
  //   2. Cap any absurd single sample (anything > 500 kcal for a
  //      single sample is certainly a summary sample that also got
  //      duplicated elsewhere — cap it to 500 so it doesn't dominate).
  //   3. Then sum the reduced window totals.
  const activeCalSamples = samples
    .filter((s) => s.metric === 'active_calories')
    .map((s) => ({
      start: new Date(s.startDate).getTime(),
      end: new Date(s.endDate ?? s.startDate).getTime(),
      value: Math.min(s.value, 500),
      source: (s.source ?? '').trim(),
    }))
    .filter((s) => s.value > 0 && Number.isFinite(s.start) && Number.isFinite(s.end))
    .sort((a, b) => a.start - b.start);
  const windows: Array<{ start: number; end: number; bySource: Map<string, number> }> = [];
  for (const s of activeCalSamples) {
    // Merge into an existing window if the sample overlaps OR starts
    // within 60s of the last window (adjacent samples from the same
    // minute-bucket ring).
    const last = windows[windows.length - 1];
    if (last && s.start <= last.end + 60_000) {
      last.end = Math.max(last.end, s.end);
      last.bySource.set(s.source, (last.bySource.get(s.source) ?? 0) + s.value);
    } else {
      const m = new Map<string, number>();
      m.set(s.source, s.value);
      windows.push({ start: s.start, end: s.end, bySource: m });
    }
  }
  // For each window, take the MAX per-source total (the most-trusted
  // single source for that interval) instead of summing overlapping
  // sources. This correctly dedupes ring-vs-workout-vs-third-party.
  const activeCalRaw = windows.reduce((acc, w) => {
    let maxForWindow = 0;
    for (const v of w.bySource.values()) if (v > maxForWindow) maxForWindow = v;
    return acc + maxForWindow;
  }, 0);
  // Final guardrail: no single day should exceed 4000 kcal active
  // energy for a non-elite-endurance athlete. Clamp anything higher
  // to flag the data as likely duplicated upstream.
  const activeCal = activeCalRaw > 0 ? Math.min(activeCalRaw, 4000) : undefined;

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

  // Normalize workouts — pass through all available fields.
  // HealthKit/HC provide summaries only. detail is left undefined;
  // richer providers (ErgZone, Garmin) can populate it later.
  const normalizedWorkouts: Workout[] = workouts.map((w) => ({
    type: w.type,
    sport_label: w.name,
    source: w.source,
    source_id: w.source_id,
    start_time: w.startDate,
    end_time: w.endDate,
    duration_min: w.duration_min,
    calories: w.calories,
    avg_hr: w.avg_hr,
    max_hr: w.max_hr,
    steps: w.steps,
    distance_m: w.distance_m,
    is_grappling: isGrapplingWorkout(w.name),
    detail: undefined, // Not available from HealthKit/HC — future extension point
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
    data_source: providerDataSource(provider),
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
  provider:
    | typeof HealthProvider.APPLE_HEALTH
    | typeof HealthProvider.HEALTH_CONNECT
    | typeof HealthProvider.MANUAL,
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
