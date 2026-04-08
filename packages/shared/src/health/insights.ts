/**
 * Rules-based health insights engine.
 *
 * Produces actionable, explainable training guidance from the AI context.
 * Every insight has a clear reason chain — no black-box output.
 *
 * This is the local/deterministic layer. A future MCP-backed AI can
 * consume the same AIHealthContext to produce richer, personalized output.
 *
 * Readiness levels match the website's WHOOP-style model:
 *   green  = good to push hard
 *   yellow = moderate effort, technique-focused
 *   red    = active recovery or rest
 *   grey   = insufficient data to assess
 */
import type { AIHealthContext } from './ai-context';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ReadinessLevel = 'green' | 'yellow' | 'red' | 'grey';

export interface TrainingInsight {
  /** Overall readiness assessment */
  readiness: ReadinessLevel;
  readiness_label: string;

  /** Recommended training approach */
  recommendation: {
    level: 'push' | 'moderate' | 'light' | 'rest' | 'unknown';
    summary: string;
    /** Specific reasons driving the recommendation */
    reasons: string[];
  };

  /** Key metrics summary for display */
  key_metrics: Array<{
    label: string;
    value: string;
    status: 'good' | 'caution' | 'warning' | 'neutral';
  }>;

  /** Positive signals */
  positives: string[];

  /** Concerns / things to watch */
  concerns: string[];

  /** Data coverage note */
  data_note: string;
}

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------

/**
 * Generate training insights from the AI health context.
 * Deterministic: same context → same insights.
 */
export function generateInsights(ctx: AIHealthContext): TrainingInsight {
  // Insufficient data path
  if (!ctx.today || ctx.data_quality.days_available < 2) {
    return insufficientData(ctx);
  }

  const t = ctx.today;
  const b = ctx.baselines;
  const reasons: string[] = [];
  const positives: string[] = [];
  const concerns: string[] = [];
  let readinessScore = 50; // neutral start, adjust up/down

  // --- Recovery score (if available from WHOOP/Polar) ---
  if (t.recovery_score != null) {
    if (t.recovery_score >= 67) {
      readinessScore += 20;
      positives.push(`Recovery ${Math.round(t.recovery_score)}% (green)`);
    } else if (t.recovery_score >= 34) {
      positives.push(`Recovery ${Math.round(t.recovery_score)}% (yellow)`);
    } else {
      readinessScore -= 25;
      concerns.push(`Recovery ${Math.round(t.recovery_score)}% (red)`);
      reasons.push('Low recovery score');
    }
  }

  // --- Sleep ---
  if (t.sleep_hours != null) {
    if (t.sleep_hours >= 7) {
      readinessScore += 10;
      positives.push(`${t.sleep_hours.toFixed(1)}h sleep`);
    } else if (t.sleep_hours >= 6) {
      // Adequate but not ideal
    } else {
      readinessScore -= 15;
      concerns.push(`Only ${t.sleep_hours.toFixed(1)}h sleep`);
      reasons.push('Low sleep');
    }

    // Compare to personal baseline
    if (b.sleep_mean != null && t.sleep_hours < b.sleep_mean * 0.8) {
      readinessScore -= 10;
      reasons.push(`Sleep ${Math.round((1 - t.sleep_hours / b.sleep_mean) * 100)}% below your average`);
    }
  }

  // --- HRV ---
  if (t.hrv_ms != null && b.hrv_mean != null) {
    const ratio = t.hrv_ms / b.hrv_mean;
    if (ratio >= 1.1) {
      readinessScore += 10;
      positives.push(`HRV ${Math.round(t.hrv_ms)}ms (above baseline)`);
    } else if (ratio < 0.8) {
      readinessScore -= 15;
      concerns.push(`HRV ${Math.round(t.hrv_ms)}ms (${Math.round((1 - ratio) * 100)}% below baseline)`);
      reasons.push('Suppressed HRV');
    }
  }

  // --- Resting HR ---
  if (t.resting_hr != null && b.resting_hr_mean != null) {
    const diff = t.resting_hr - b.resting_hr_mean;
    if (diff > 5) {
      readinessScore -= 10;
      concerns.push(`Resting HR ${Math.round(t.resting_hr)}bpm (+${Math.round(diff)} above baseline)`);
      reasons.push('Elevated resting heart rate');
    } else if (diff < -3) {
      readinessScore += 5;
      positives.push(`Resting HR ${Math.round(t.resting_hr)}bpm (below baseline)`);
    }
  }

  // --- Strain / training load ---
  if (t.daily_strain != null) {
    if (t.daily_strain > 16) {
      readinessScore -= 10;
      concerns.push(`High strain today (${t.daily_strain.toFixed(1)})`);
      reasons.push('Already accumulated high strain');
    }
  }

  // --- Recent training load ---
  if (ctx.recent_7d.rest_days === 0 && ctx.recent_7d.workout_count >= 7) {
    readinessScore -= 15;
    concerns.push('No rest days in the last 7 days');
    reasons.push('Zero rest days this week');
  } else if (ctx.recent_7d.rest_days >= 2) {
    readinessScore += 5;
    positives.push(`${ctx.recent_7d.rest_days} rest days this week`);
  }

  // --- Trends ---
  if (ctx.trends.recovery === 'declining') {
    readinessScore -= 10;
    concerns.push('Recovery trending down');
    reasons.push('Declining recovery trend');
  }
  if (ctx.trends.recovery === 'improving') {
    readinessScore += 5;
    positives.push('Recovery trending up');
  }
  if (ctx.trends.hrv === 'declining') {
    readinessScore -= 5;
    concerns.push('HRV trending down');
  }
  if (ctx.trends.resting_hr === 'declining') {
    // declining resting HR = improving (we inverted in ai-context)
    readinessScore += 3;
    positives.push('Resting HR trending down (good)');
  }

  // --- Consecutive training days ---
  let consecutiveTraining = 0;
  const recentSorted = [...(ctx.recent_workouts || [])];
  // Count consecutive days with workouts from most recent
  const daySet = new Set(recentSorted.map((w) => w.date));
  const sortedDates = Array.from(daySet).sort().reverse();
  const todayDate = ctx.today?.date;
  if (todayDate && sortedDates[0] === todayDate) {
    for (let i = 0; i < sortedDates.length; i++) {
      const expected = new Date(todayDate);
      expected.setDate(expected.getDate() - i);
      if (sortedDates[i] === expected.toISOString().slice(0, 10)) {
        consecutiveTraining++;
      } else break;
    }
  }
  if (consecutiveTraining >= 4) {
    readinessScore -= 10;
    concerns.push(`${consecutiveTraining} consecutive training days`);
    reasons.push('Extended consecutive training without rest');
  } else if (consecutiveTraining === 3) {
    readinessScore -= 5;
    concerns.push('3 consecutive training days — consider rest tomorrow');
  }

  // --- Sleep quality (deep + REM if available) ---
  if (t.sleep_deep_hours != null && t.sleep_rem_hours != null && t.sleep_hours != null && t.sleep_hours > 0) {
    const qualityRatio = (t.sleep_deep_hours + t.sleep_rem_hours) / t.sleep_hours;
    if (qualityRatio >= 0.4) {
      readinessScore += 5;
      positives.push(`Good sleep quality (${Math.round(qualityRatio * 100)}% deep+REM)`);
    } else if (qualityRatio < 0.25) {
      readinessScore -= 5;
      concerns.push(`Low sleep quality (${Math.round(qualityRatio * 100)}% deep+REM)`);
      reasons.push('Poor sleep quality — low deep and REM sleep');
    }
  }

  // --- Weekly training consistency ---
  if (ctx.data_quality.days_available >= 7) {
    const wk = ctx.recent_7d;
    if (wk.workout_count >= 3 && wk.workout_count <= 5 && wk.rest_days >= 2) {
      positives.push(`Good training consistency (${wk.workout_count} sessions, ${wk.rest_days} rest days)`);
    } else if (wk.workout_count <= 1 && !ctx.data_quality.missing.workout_detail) {
      concerns.push('Low training frequency this week');
    }
  }

  // --- Weekly grappling load ---
  if (ctx.recent_7d.grappling_count >= 4) {
    concerns.push(`${ctx.recent_7d.grappling_count} grappling sessions this week — watch for accumulated fatigue`);
    readinessScore -= 5;
  }

  // --- Clamp and classify ---
  readinessScore = Math.max(0, Math.min(100, readinessScore));

  const readiness: ReadinessLevel =
    readinessScore >= 65 ? 'green' : readinessScore >= 40 ? 'yellow' : 'red';

  const recommendation = buildRecommendation(readiness, reasons, t.grappling_today);

  // --- Key metrics for display ---
  const keyMetrics = buildKeyMetrics(t, b);

  // --- Data coverage note ---
  const dataParts: string[] = [];
  dataParts.push(`${ctx.data_quality.days_available} days of data`);
  dataParts.push(`Sources: ${ctx.data_quality.providers.join(', ') || 'none'}`);
  if (ctx.data_quality.missing.insufficient_history) {
    dataParts.push('More history will improve accuracy');
  }

  return {
    readiness,
    readiness_label: readinessLabels[readiness],
    recommendation,
    key_metrics: keyMetrics,
    positives,
    concerns,
    data_note: dataParts.join(' · '),
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const readinessLabels: Record<ReadinessLevel, string> = {
  green: 'Good to push',
  yellow: 'Moderate effort',
  red: 'Recovery day',
  grey: 'Insufficient data',
};

function buildRecommendation(
  readiness: ReadinessLevel,
  reasons: string[],
  grapplingToday: boolean,
): TrainingInsight['recommendation'] {
  switch (readiness) {
    case 'green':
      return {
        level: 'push',
        summary: grapplingToday
          ? 'Great day for hard sparring or competition prep.'
          : 'Body is recovered — good day to train hard.',
        reasons: reasons.length > 0 ? reasons : ['All signals look good'],
      };
    case 'yellow':
      return {
        level: 'moderate',
        summary: grapplingToday
          ? 'Technique-focused rolling — avoid all-out intensity.'
          : 'Moderate training. Focus on skill work over conditioning.',
        reasons,
      };
    case 'red':
      return {
        level: reasons.includes('Zero rest days this week') ? 'rest' : 'light',
        summary:
          reasons.includes('Zero rest days this week')
            ? 'Consider a rest day. Your body needs recovery.'
            : 'Light movement only — stretching, mobility, flow rolling.',
        reasons,
      };
    default:
      return {
        level: 'unknown',
        summary: 'Not enough data to make a recommendation.',
        reasons: ['Connect a health source and sync data'],
      };
  }
}

function buildKeyMetrics(
  t: NonNullable<AIHealthContext['today']>,
  b: AIHealthContext['baselines'],
): TrainingInsight['key_metrics'] {
  const metrics: TrainingInsight['key_metrics'] = [];

  if (t.recovery_score != null) {
    metrics.push({
      label: 'Recovery',
      value: `${Math.round(t.recovery_score)}%`,
      status: t.recovery_score >= 67 ? 'good' : t.recovery_score >= 34 ? 'caution' : 'warning',
    });
  }

  if (t.sleep_hours != null) {
    metrics.push({
      label: 'Sleep',
      value: `${t.sleep_hours.toFixed(1)}h`,
      status: t.sleep_hours >= 7 ? 'good' : t.sleep_hours >= 6 ? 'caution' : 'warning',
    });
  }

  if (t.hrv_ms != null) {
    const status: 'good' | 'caution' | 'warning' | 'neutral' =
      b.hrv_mean != null
        ? t.hrv_ms >= b.hrv_mean * 0.9
          ? 'good'
          : t.hrv_ms >= b.hrv_mean * 0.8
            ? 'caution'
            : 'warning'
        : 'neutral';
    metrics.push({
      label: 'HRV',
      value: `${Math.round(t.hrv_ms)}ms`,
      status,
    });
  }

  if (t.resting_hr != null) {
    const status: 'good' | 'caution' | 'warning' | 'neutral' =
      b.resting_hr_mean != null
        ? t.resting_hr <= b.resting_hr_mean + 3
          ? 'good'
          : t.resting_hr <= b.resting_hr_mean + 5
            ? 'caution'
            : 'warning'
        : 'neutral';
    metrics.push({
      label: 'Resting HR',
      value: `${Math.round(t.resting_hr)}bpm`,
      status,
    });
  }

  if (t.daily_strain != null) {
    metrics.push({
      label: 'Strain',
      value: t.daily_strain.toFixed(1),
      status: t.daily_strain <= 12 ? 'good' : t.daily_strain <= 16 ? 'caution' : 'warning',
    });
  }

  return metrics;
}

function insufficientData(ctx: AIHealthContext): TrainingInsight {
  return {
    readiness: 'grey',
    readiness_label: 'Insufficient data',
    recommendation: {
      level: 'unknown',
      summary: 'Connect a health source and sync to get training guidance.',
      reasons: ['Not enough data to assess readiness'],
    },
    key_metrics: [],
    positives: [],
    concerns: [],
    data_note: ctx.today
      ? `${ctx.data_quality.days_available} day(s) — need at least 2 for insights`
      : 'No health data synced yet',
  };
}
