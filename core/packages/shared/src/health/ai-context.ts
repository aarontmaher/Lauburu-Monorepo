/**
 * AI Health Context — the single compact object that feeds any AI layer.
 *
 * Assembles normalized metrics, derived features, recent workouts, and
 * data quality into one inspectable, serializable shape.
 *
 * Design:
 * - Deterministic: same inputs → same context.
 * - Source-agnostic: works regardless of which providers fed the data.
 * - Debuggable: every field traces back to a clear source.
 * - Ready for: MCP-backed AI flows, coaching prompts, habit recommendations.
 *
 * Future enrichment insertion points:
 * - WHOOP: recovery_score and readiness populate directly from DailyMetrics
 * - ErgZone: workout_detail in recent_workouts carries interval data
 * - Cronometer: nutrition_today / nutrition_7d_avg can be added below
 * - Subjective: mood/energy/RPE when manual entry is wired
 */
import type { DailyMetrics, DerivedFeatures, Workout } from '../types/health';
import type { HealthFlag } from './derive-features';

/**
 * Compact AI health context — everything an AI model or rules engine needs
 * to generate training guidance in a single object.
 */
export interface AIHealthContext {
  /** When this context was computed */
  computed_at: string;

  /** Data coverage */
  data_quality: {
    days_available: number;
    has_today: boolean;
    providers: string[];
    missing: DerivedFeatures['missing'];
  };

  /** Today's snapshot */
  today: {
    date: string;
    recovery_score: number | null;
    readiness: string;
    hrv_ms: number | null;
    resting_hr: number | null;
    sleep_hours: number | null;
    sleep_deep_hours: number | null;
    sleep_rem_hours: number | null;
    daily_strain: number | null;
    step_count: number | null;
    active_calories: number | null;
    workout_count: number;
    grappling_today: boolean;
  } | null;

  /** Personal baselines (full history) */
  baselines: {
    recovery_mean: number | null;
    hrv_mean: number | null;
    strain_mean: number | null;
    sleep_mean: number | null;
    resting_hr_mean: number | null;
  };

  /** Recent 7-day summary */
  recent_7d: {
    recovery_mean: number | null;
    strain_mean: number | null;
    sleep_mean: number | null;
    workout_count: number;
    grappling_count: number;
    rest_days: number;
  };

  /** Trend directions */
  trends: {
    recovery: DerivedFeatures['recovery_trend'];
    strain: DerivedFeatures['strain_trend'];
    hrv: 'improving' | 'declining' | 'stable';
    resting_hr: 'improving' | 'declining' | 'stable';
  };

  /** Recent workouts (last 7 days, most recent first) */
  recent_workouts: Array<{
    date: string;
    type: string;
    name: string;
    duration_min: number;
    calories?: number;
    avg_hr?: number;
    max_hr?: number;
    is_grappling: boolean;
    source?: string;
    has_detail: boolean;
  }>;

  /** Pre-computed flags from rules engine */
  flags: HealthFlag[];
}

/**
 * Build the AI health context from normalized data and derived features.
 */
export function buildAIHealthContext(
  days: DailyMetrics[],
  features: DerivedFeatures,
  flags: HealthFlag[],
): AIHealthContext {
  const sorted = [...days].sort((a, b) => a.date.localeCompare(b.date));
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayData = sorted.find((d) => d.date === todayStr) ?? null;
  const last7 = sorted.slice(-7);

  // Collect recent workouts
  const recentWorkouts: AIHealthContext['recent_workouts'] = [];
  for (const day of last7.slice().reverse()) {
    for (const w of day.workouts ?? []) {
      recentWorkouts.push({
        date: day.date,
        type: w.type,
        name: w.sport_label ?? w.type,
        duration_min: w.duration_min,
        calories: w.calories,
        avg_hr: w.avg_hr,
        max_hr: w.max_hr,
        is_grappling: w.is_grappling,
        source: w.source,
        has_detail: w.detail != null,
      });
    }
  }

  // Count rest days (no workouts) in last 7
  const restDays = last7.filter(
    (d) => !d.workouts?.length && !d.grappling_session,
  ).length;

  // Resting HR baseline + trend
  const restingHrValues = sorted
    .map((d) => d.resting_hr)
    .filter((n): n is number => n != null);
  const restingHrMean =
    restingHrValues.length > 0
      ? Math.round(
          (restingHrValues.reduce((a, b) => a + b, 0) /
            restingHrValues.length) *
            10,
        ) / 10
      : null;

  // RHR trend: lower is better, so invert for trend naming
  const rhrTrend = computeSimpleTrend(
    sorted.map((d) => (d.resting_hr != null ? -d.resting_hr : undefined)),
  );

  // HRV trend
  const hrvTrend = computeSimpleTrend(sorted.map((d) => d.hrv_ms));

  return {
    computed_at: new Date().toISOString(),

    data_quality: {
      days_available: sorted.length,
      has_today: todayData != null,
      providers: features.provenance,
      missing: features.missing,
    },

    today: todayData
      ? {
          date: todayData.date,
          recovery_score: todayData.recovery_score ?? null,
          readiness: todayData.readiness_label ?? 'unknown',
          hrv_ms: todayData.hrv_ms ?? null,
          resting_hr: todayData.resting_hr ?? null,
          sleep_hours: todayData.sleep_hours ?? null,
          sleep_deep_hours: todayData.sws_hours ?? null,
          sleep_rem_hours: todayData.rem_hours ?? null,
          daily_strain: todayData.daily_strain ?? null,
          step_count: todayData.step_count ?? null,
          active_calories: todayData.active_calories ?? null,
          workout_count: todayData.workouts?.length ?? 0,
          grappling_today:
            (todayData.workouts?.some((w) => w.is_grappling) ?? false) ||
            todayData.grappling_session != null,
        }
      : null,

    baselines: {
      recovery_mean: features.baseline_recovery_mean,
      hrv_mean: features.baseline_hrv_mean,
      strain_mean: features.baseline_strain_mean,
      sleep_mean: features.baseline_sleep_mean,
      resting_hr_mean: restingHrMean,
    },

    recent_7d: {
      recovery_mean: features.last_7d_recovery_mean,
      strain_mean: features.last_7d_strain_mean,
      sleep_mean: mean7d(last7.map((d) => d.sleep_hours)),
      workout_count: last7.reduce(
        (n, d) => n + (d.workouts?.length ?? 0),
        0,
      ),
      grappling_count: last7.reduce(
        (n, d) =>
          n +
          (d.workouts?.filter((w) => w.is_grappling).length ?? 0) +
          (d.grappling_session ? 1 : 0),
        0,
      ),
      rest_days: restDays,
    },

    trends: {
      recovery: features.recovery_trend,
      strain: features.strain_trend,
      hrv: hrvTrend,
      resting_hr: rhrTrend,
    },

    recent_workouts: recentWorkouts,
    flags,
  };
}

// --- Helpers ---

function computeSimpleTrend(
  values: (number | undefined)[],
): 'improving' | 'declining' | 'stable' {
  const valid = values.filter((n): n is number => n != null);
  if (valid.length < 4) return 'stable';
  const mid = Math.floor(valid.length / 2);
  const first = valid.slice(0, mid);
  const second = valid.slice(mid);
  const avgFirst = first.reduce((a, b) => a + b, 0) / first.length;
  const avgSecond = second.reduce((a, b) => a + b, 0) / second.length;
  const pct = ((avgSecond - avgFirst) / (avgFirst || 1)) * 100;
  if (pct > 3) return 'improving';
  if (pct < -3) return 'declining';
  return 'stable';
}

function mean7d(values: (number | undefined)[]): number | null {
  const valid = values.filter((n): n is number => n != null);
  return valid.length > 0
    ? Math.round((valid.reduce((a, b) => a + b, 0) / valid.length) * 100) / 100
    : null;
}
