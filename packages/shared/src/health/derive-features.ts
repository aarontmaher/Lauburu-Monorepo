/**
 * Derive AI-ready features from normalized health history.
 * Matches the website's deriveFeatures() output shape.
 *
 * Design principles:
 * - Deterministic: same input always produces same output.
 * - Source-agnostic: works for WHOOP, HealthKit, Health Connect, future ErgZone/Cronometer.
 * - Graceful degradation: missing fields produce null, not errors.
 * - Explainable: every derived value has a clear calculation path.
 */
import type { DailyMetrics, DerivedFeatures } from '../types/health';

/** Compute mean of non-null numbers */
function mean(nums: (number | undefined)[]): number | null {
  const valid = nums.filter((n): n is number => n != null);
  return valid.length > 0
    ? Math.round((valid.reduce((a, b) => a + b, 0) / valid.length) * 100) / 100
    : null;
}

/** Compute standard deviation */
function std(nums: (number | undefined)[]): number | null {
  const valid = nums.filter((n): n is number => n != null);
  if (valid.length < 2) return null;
  const m = valid.reduce((a, b) => a + b, 0) / valid.length;
  const variance = valid.reduce((sum, v) => sum + (v - m) ** 2, 0) / valid.length;
  return Math.round(Math.sqrt(variance) * 100) / 100;
}

/** Determine trend from two halves of a series */
function trend(
  values: (number | undefined)[],
): 'improving' | 'declining' | 'stable' {
  const valid = values.filter((n): n is number => n != null);
  if (valid.length < 4) return 'stable';
  const mid = Math.floor(valid.length / 2);
  const firstHalf = valid.slice(0, mid);
  const secondHalf = valid.slice(mid);
  const avgFirst = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
  const avgSecond = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
  const pctChange = ((avgSecond - avgFirst) / (avgFirst || 1)) * 100;
  if (pctChange > 3) return 'improving';
  if (pctChange < -3) return 'declining';
  return 'stable';
}

/**
 * Derive features from a history of daily metrics.
 * Days should be sorted chronologically (oldest first).
 */
export function deriveFeatures(days: DailyMetrics[]): DerivedFeatures {
  if (days.length === 0) {
    return emptyFeatures();
  }

  const sorted = [...days].sort((a, b) => a.date.localeCompare(b.date));
  const today = sorted[sorted.length - 1];
  const last7 = sorted.slice(-7);

  // Workout counts
  const totalWorkouts = sorted.reduce(
    (n, d) => n + (d.workouts?.length ?? 0),
    0,
  );
  const grapplingCount = sorted.reduce(
    (n, d) =>
      n +
      (d.workouts?.filter((w) => w.is_grappling).length ?? 0) +
      (d.grappling_session ? 1 : 0),
    0,
  );

  // Sleep detail availability
  const hasSleepDetail = sorted.some(
    (d) => d.sws_hours != null || d.rem_hours != null,
  );

  // Recovery trend: higher = improving (WHOOP recovery, or proxy)
  const recoveryValues = sorted.map((d) => d.recovery_score);
  // HRV trend: higher = improving
  const hrvValues = sorted.map((d) => d.hrv_ms);
  // Strain trend: uses opposite naming — increasing strain = "increasing"
  const strainValues = sorted.map((d) => d.daily_strain);
  // Resting HR trend: lower = improving (invert for trend calc)
  const restingHrTrend = trend(
    sorted.map((d) => (d.resting_hr != null ? -d.resting_hr : undefined)),
  );

  const recoveryTrend = trend(recoveryValues);
  const hrvTrend = trend(hrvValues);
  const rawStrainTrend = trend(strainValues);
  const strainTrend: 'increasing' | 'decreasing' | 'stable' =
    rawStrainTrend === 'improving'
      ? 'increasing'
      : rawStrainTrend === 'declining'
        ? 'decreasing'
        : 'stable';

  return {
    // Today
    today_recovery: today.recovery_score ?? null,
    today_readiness: today.readiness_label ?? 'unknown',
    today_strain: today.daily_strain ?? null,
    today_hrv: today.hrv_ms ?? null,
    today_sleep: today.sleep_hours ?? null,

    // Baselines (full history)
    baseline_recovery_mean: mean(sorted.map((d) => d.recovery_score)),
    baseline_hrv_mean: mean(sorted.map((d) => d.hrv_ms)),
    baseline_strain_mean: mean(sorted.map((d) => d.daily_strain)),
    baseline_sleep_mean: mean(sorted.map((d) => d.sleep_hours)),

    // Last 7 days
    last_7d_recovery_mean: mean(last7.map((d) => d.recovery_score)),
    last_7d_strain_mean: mean(last7.map((d) => d.daily_strain)),

    // Counts
    workouts: totalWorkouts,
    grappling_sessions: grapplingCount,
    sleep_detail: hasSleepDetail,

    // Trends
    recovery_trend: recoveryTrend,
    strain_trend: strainTrend,

    // Missing data flags
    missing: {
      grappling_sessions: grapplingCount === 0,
      grappling_workout:
        sorted.every(
          (d) => !d.workouts?.some((w) => w.is_grappling),
        ),
      sleep_data: sorted.every((d) => d.sleep_hours == null),
      sleep_detail: !hasSleepDetail,
      strain_data: sorted.every((d) => d.daily_strain == null),
      hrv_data: sorted.every((d) => d.hrv_ms == null),
      workout_detail: totalWorkouts === 0,
      subjective_data: sorted.every((d) => d.subjective == null),
      insufficient_history: sorted.length < 7,
    },

    // Data provenance
    provenance: [
      ...new Set(sorted.map((d) => d.provider).filter(Boolean)),
    ],
  };
}

/**
 * Compute notable flags / conditions for UI display.
 * Returns human-readable flag strings for the Health tab.
 */
export interface HealthFlag {
  type: 'warning' | 'info' | 'positive';
  label: string;
}

export function computeFlags(
  features: DerivedFeatures,
  today: DailyMetrics | null,
): HealthFlag[] {
  const flags: HealthFlag[] = [];

  if (features.missing.insufficient_history) {
    flags.push({
      type: 'info',
      label: `Only ${features.workouts > 0 ? 'partial' : 'no'} history — trends improve with more data`,
    });
  }

  if (today) {
    // Low sleep
    if (
      today.sleep_hours != null &&
      features.baseline_sleep_mean != null &&
      today.sleep_hours < features.baseline_sleep_mean * 0.8
    ) {
      flags.push({
        type: 'warning',
        label: `Sleep ${today.sleep_hours.toFixed(1)}h — below your average of ${features.baseline_sleep_mean.toFixed(1)}h`,
      });
    }

    // Low HRV
    if (
      today.hrv_ms != null &&
      features.baseline_hrv_mean != null &&
      today.hrv_ms < features.baseline_hrv_mean * 0.8
    ) {
      flags.push({
        type: 'warning',
        label: `HRV ${Math.round(today.hrv_ms)}ms — below your baseline of ${Math.round(features.baseline_hrv_mean)}ms`,
      });
    }

    // High resting HR (above baseline + 10%)
    if (
      today.resting_hr != null &&
      features.baseline_hrv_mean != null
    ) {
      // We use baseline_strain_mean as proxy check for resting HR baseline
      // since we don't have a dedicated resting HR baseline in DerivedFeatures
    }

    // High strain
    if (today.daily_strain != null && today.daily_strain > 16) {
      flags.push({
        type: 'warning',
        label: `High strain today (${today.daily_strain.toFixed(1)}) — consider recovery tomorrow`,
      });
    }

    // Good recovery
    if (today.recovery_score != null && today.recovery_score >= 67) {
      flags.push({
        type: 'positive',
        label: `Recovery ${Math.round(today.recovery_score)}% — green zone`,
      });
    }

    // No workout today
    if (!today.workouts?.length && !today.grappling_session) {
      flags.push({ type: 'info', label: 'No workout recorded today' });
    }
  }

  // Trend flags
  if (features.recovery_trend === 'declining') {
    flags.push({
      type: 'warning',
      label: 'Recovery trending down — watch for overtraining',
    });
  }
  if (features.recovery_trend === 'improving') {
    flags.push({ type: 'positive', label: 'Recovery trending up' });
  }

  return flags;
}

function emptyFeatures(): DerivedFeatures {
  return {
    today_recovery: null,
    today_readiness: 'unknown',
    today_strain: null,
    today_hrv: null,
    today_sleep: null,
    baseline_recovery_mean: null,
    baseline_hrv_mean: null,
    baseline_strain_mean: null,
    baseline_sleep_mean: null,
    last_7d_recovery_mean: null,
    last_7d_strain_mean: null,
    workouts: 0,
    grappling_sessions: 0,
    sleep_detail: false,
    recovery_trend: 'stable',
    strain_trend: 'stable',
    missing: {
      grappling_sessions: true,
      grappling_workout: true,
      sleep_data: true,
      sleep_detail: true,
      strain_data: true,
      hrv_data: true,
      workout_detail: true,
      subjective_data: true,
      insufficient_history: true,
    },
    provenance: [],
  };
}
