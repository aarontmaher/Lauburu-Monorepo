/**
 * Coaching response layer — deterministic training guidance.
 *
 * Produces structured coaching output from the AI payload.
 * This is the client-side coaching engine. A future MCP-backed
 * server can produce richer output from the same AI payload.
 *
 * Architecture:
 * ─────────────
 * LOCAL (this file):
 *   AIPayload → generateCoaching() → CoachingResponse
 *   - Deterministic, explainable, works offline
 *   - No model calls, no network required
 *   - Always available as the baseline
 *
 * FUTURE SERVER-SIDE (MCP endpoint):
 *   POST /api/coaching
 *   Body: AIPayload
 *   Response: CoachingResponse (same shape, richer content)
 *   - Model-generated text alongside structured data
 *   - Personalized based on training history
 *   - Cross-referenced with shared memory (facts, insights, rules)
 *
 * The app should:
 *   1. Always show local coaching (instant, offline)
 *   2. Optionally fetch server coaching when available
 *   3. Merge or replace — server coaching takes priority if present
 *
 * MCP endpoint spec (for future implementation):
 * ──────────────────────────────────────────────
 *   Route: @mcp.custom_route("/api/coaching", methods=["POST", "OPTIONS"])
 *   Auth: JWT from Authorization header
 *   Body: AIPayload (version: 1)
 *   Response: {
 *     ok: true,
 *     coaching: CoachingResponse,
 *     model: "local" | "gpt-4o" | "claude-sonnet" | etc,
 *     generated_at: ISO8601
 *   }
 *   Fallback: if model unavailable, return local coaching
 */
import type { AIPayload } from './ai-payload';
import type { CoachingPreferences } from '../types/preferences';
import { DEFAULT_PREFERENCES, getTargetSessionsPerWeek, getTodayPlan, SCHEDULE_SESSION_LABELS } from '../types/preferences';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const readinessLabels: Record<string, string> = {
  green: 'Good to push',
  yellow: 'Moderate effort',
  red: 'Recovery day',
  grey: 'Insufficient data',
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CoachingResponse {
  /** When this coaching was generated */
  generated_at: string;

  /** Source of this coaching */
  source: 'local' | 'server';

  /** Which preferences shaped this output (for explainability) */
  preference_effects?: string[];

  /** Overall readiness (mirrors insights but with coaching framing) */
  readiness: {
    level: 'green' | 'yellow' | 'red' | 'grey';
    headline: string;
  };

  /** Primary training recommendation for today */
  today_recommendation: {
    action: 'push' | 'moderate' | 'light' | 'rest' | 'unknown';
    summary: string;
    detail: string;
  };

  /** Recovery guidance */
  recovery: {
    status: 'recovered' | 'recovering' | 'fatigued' | 'unknown';
    summary: string;
    actions: string[];
  };

  /** Sleep assessment */
  sleep: {
    status: 'good' | 'adequate' | 'poor' | 'unknown';
    summary: string;
  };

  /** Training load assessment */
  training_load: {
    status: 'balanced' | 'high' | 'low' | 'overreaching' | 'unknown';
    summary: string;
  };

  /** Grappling-specific guidance */
  grappling: {
    summary: string;
    suggestion: string;
  };

  /** Top caution notes (things to watch) */
  cautions: string[];

  /** Data quality / confidence note */
  confidence: {
    level: 'high' | 'moderate' | 'low';
    note: string;
  };
}

// ---------------------------------------------------------------------------
// Engine
// ---------------------------------------------------------------------------

/**
 * Generate coaching from AI payload + user preferences.
 * Deterministic, explainable, offline-capable.
 */
export function generateCoaching(
  payload: AIPayload,
  prefs: CoachingPreferences = DEFAULT_PREFERENCES,
): CoachingResponse {
  const { readiness, coverage } = payload;

  if (!coverage.has_today || coverage.days_available < 2) {
    return insufficientDataCoaching(payload);
  }

  // Apply preference adjustments to readiness level
  const adjustedLevel = adjustReadiness(readiness.level, payload, prefs);
  const prefEffects = collectPreferenceEffects(readiness.level, adjustedLevel, prefs);

  const adjustedPayload = {
    ...payload,
    readiness: { ...payload.readiness, level: adjustedLevel },
  };

  return {
    generated_at: new Date().toISOString(),
    source: 'local',
    preference_effects: prefEffects.length > 0 ? prefEffects : undefined,

    readiness: {
      level: adjustedLevel,
      headline: readinessLabels[adjustedLevel],
    },

    today_recommendation: buildTodayRec(adjustedPayload, prefs),
    recovery: buildRecovery(adjustedPayload, prefs),
    sleep: buildSleep(adjustedPayload),
    training_load: buildTrainingLoad(adjustedPayload, prefs),
    grappling: buildGrappling(adjustedPayload, prefs),
    cautions: payload.concerns,
    confidence: buildConfidence(adjustedPayload),
  };
}

/**
 * Adjust readiness level based on preferences.
 */
function adjustReadiness(
  base: string,
  payload: AIPayload,
  prefs: CoachingPreferences,
): CoachingResponse['readiness']['level'] {
  let level = base as 'green' | 'yellow' | 'red' | 'grey';

  // Conservative recovery: shift yellow → red, green stays green
  if (prefs.recovery_conservatism === 'conservative' && level === 'yellow') {
    level = 'red';
  }
  // Aggressive recovery: shift yellow → green
  if (prefs.recovery_conservatism === 'aggressive' && level === 'yellow') {
    level = 'green';
  }

  // Train-through bias: shift red → yellow (never skip entirely)
  if (prefs.hard_day_bias === 'train_through' && level === 'red') {
    level = 'yellow';
  }
  // Err-on-rest bias: shift yellow → red
  if (prefs.hard_day_bias === 'err_on_rest' && level === 'yellow') {
    level = 'red';
  }

  // Comp prep: allow higher load (don't downgrade green for high frequency)
  if (prefs.comp_prep && level === 'yellow') {
    const tc = payload.training_context;
    // In comp prep, only go red if genuinely fatigued, not just high volume
    if (tc.rest_days_7d >= 1 && tc.hard_sessions_7d <= 4) {
      level = 'green';
    }
  }

  return level;
}

/**
 * Explain which preferences affected the output.
 */
function collectPreferenceEffects(
  originalLevel: string,
  adjustedLevel: string,
  prefs: CoachingPreferences,
): string[] {
  const effects: string[] = [];

  if (originalLevel !== adjustedLevel) {
    effects.push(
      `Readiness shifted ${originalLevel} → ${adjustedLevel}`,
    );
  }

  if (prefs.recovery_conservatism !== 'moderate') {
    effects.push(
      prefs.recovery_conservatism === 'conservative'
        ? 'Conservative recovery mode — erring on rest'
        : 'Aggressive recovery mode — pushing through',
    );
  }

  if (prefs.comp_prep) {
    effects.push('Competition prep mode — higher load tolerance');
  }

  if (prefs.hard_day_bias !== 'balanced') {
    effects.push(
      prefs.hard_day_bias === 'train_through'
        ? 'Train-through bias active'
        : 'Rest-first bias active',
    );
  }

  if (prefs.goal === 'competition') {
    effects.push('Goal: competition — prioritizing performance');
  } else if (prefs.goal === 'skill_development') {
    effects.push('Goal: skill development — technique focus');
  }

  return effects;
}

// ---------------------------------------------------------------------------
// Builders
// ---------------------------------------------------------------------------

function buildTodayRec(
  p: AIPayload,
  prefs: CoachingPreferences,
): CoachingResponse['today_recommendation'] {
  const { readiness, training_context: tc } = p;
  const action = mapLevel(readiness.level);
  const todayPlan = getTodayPlan(prefs.schedule);
  const isPlannedDay = todayPlan.length > 0;
  const plannedTypes = todayPlan.map((s) => s.type);

  let detail: string;
  const goalCtx = prefs.goal === 'competition'
    ? 'competition-style '
    : prefs.goal === 'skill_development'
      ? 'technique-focused '
      : '';

  switch (action) {
    case 'push':
      detail = tc.grappling_sessions_7d > 0
        ? `Your body is recovered. Good day for ${goalCtx}hard sparring or high-intensity drilling. You've had ${tc.rest_days_7d} rest day${tc.rest_days_7d !== 1 ? 's' : ''} this week.`
        : `Recovery signals are strong. Good day to push intensity${prefs.goal === 'skill_development' ? ' — consider focused technique work at higher pace' : ''}.`;
      break;
    case 'moderate':
      if (prefs.goal === 'skill_development') {
        detail = 'Good day for drilling and positional work. Save hard sparring for when recovery is stronger.';
      } else if (prefs.comp_prep) {
        detail = 'Comp prep mode: keep a technical session today. Save intensity for a better recovery day.';
      } else {
        detail = tc.consecutive_training_days >= 3
          ? `${tc.consecutive_training_days} consecutive training days. Focus on technique and positional rounds.`
          : 'Some signals are suboptimal. Keep intensity moderate — technique work or focused positional rounds.';
      }
      break;
    case 'light':
      detail = prefs.hard_day_bias === 'train_through'
        ? 'Recovery indicators are low, but train-through mode is on. Keep it very light — flow rolling or mobility only.'
        : 'Recovery indicators suggest taking it easy. Light flow rolling, stretching, mobility, or video study.';
      break;
    case 'rest':
      detail = prefs.hard_day_bias === 'train_through'
        ? 'Even in train-through mode, today warrants rest. Your body needs recovery to perform.'
        : tc.rest_days_7d === 0
          ? 'No rest days this week. A full rest day will improve your next training session.'
          : 'Multiple recovery indicators are low. Rest today to avoid accumulated fatigue.';
      break;
    default:
      detail = 'Connect a health source and sync to get personalized training guidance.';
  }

  // Add schedule context
  if (isPlannedDay && action !== 'unknown') {
    const typeStr = plannedTypes.length === 1
      ? SCHEDULE_SESSION_LABELS[plannedTypes[0]] ?? plannedTypes[0]
      : `${plannedTypes.length} sessions`;
    const timeStr = todayPlan[0]?.time ? ` at ${todayPlan[0].time}` : '';
    detail += ` Planned: ${typeStr}${timeStr}.`;
  } else if (!isPlannedDay && action === 'push') {
    detail += ' No session planned today — rest day on your schedule.';
  }

  return {
    action,
    summary: readinessLabels[readiness.level as keyof typeof readinessLabels] ?? readiness.label,
    detail,
  };
}

function buildRecovery(
  p: AIPayload,
  prefs: CoachingPreferences,
): CoachingResponse['recovery'] {
  const { readiness, trends, baselines, metrics } = p;

  const hrvMetric = metrics.find((m) => m.label === 'HRV');
  const rhrMetric = metrics.find((m) => m.label === 'Resting HR');

  let status: CoachingResponse['recovery']['status'] = 'unknown';
  const actions: string[] = [];

  if (readiness.level === 'green') {
    status = 'recovered';
  } else if (readiness.level === 'yellow') {
    status = 'recovering';
    actions.push('Prioritize sleep tonight');
    if (trends.hrv === 'declining') actions.push('Monitor HRV over the next 2-3 days');
    if (prefs.recovery_conservatism === 'conservative') {
      actions.push('Consider lighter intensity tomorrow');
    }
  } else if (readiness.level === 'red') {
    status = 'fatigued';
    actions.push('Aim for 8+ hours of sleep');
    if (prefs.hard_day_bias !== 'train_through') {
      actions.push('Reduce training intensity for 1-2 days');
    }
    actions.push('Consider active recovery (walking, stretching)');
  }

  const parts: string[] = [];
  if (hrvMetric) parts.push(`HRV ${hrvMetric.value}`);
  if (rhrMetric) parts.push(`Resting HR ${rhrMetric.value}`);
  if (trends.recovery !== 'stable') parts.push(`Recovery ${trends.recovery}`);

  const summary = parts.length > 0
    ? `${status === 'recovered' ? 'Well recovered' : status === 'recovering' ? 'Still recovering' : 'Showing fatigue'}. ${parts.join(', ')}.`
    : `Recovery status: ${status}.`;

  return { status, summary, actions };
}

function buildSleep(p: AIPayload): CoachingResponse['sleep'] {
  const sleepMetric = p.metrics.find((m) => m.label === 'Sleep');
  if (!sleepMetric || !p.coverage.has_sleep) {
    return { status: 'unknown', summary: 'No sleep data available.' };
  }

  const hours = parseFloat(sleepMetric.value);
  let status: CoachingResponse['sleep']['status'];
  let summary: string;

  if (hours >= 7) {
    status = 'good';
    summary = `${sleepMetric.value} of sleep — well above the 7h threshold.`;
  } else if (hours >= 6) {
    status = 'adequate';
    summary = `${sleepMetric.value} of sleep — adequate but not optimal. Aim for 7+h.`;
  } else {
    status = 'poor';
    summary = `Only ${sleepMetric.value} of sleep. This will impact recovery and performance.`;
  }

  if (p.baselines.sleep_mean) {
    const diff = hours - p.baselines.sleep_mean;
    if (Math.abs(diff) > 0.5) {
      summary += ` (${diff > 0 ? '+' : ''}${diff.toFixed(1)}h vs your ${p.baselines.sleep_mean.toFixed(1)}h average)`;
    }
  }

  return { status, summary };
}

function buildTrainingLoad(
  p: AIPayload,
  prefs: CoachingPreferences,
): CoachingResponse['training_load'] {
  const tc = p.training_context;

  if (tc.workouts_7d === 0) {
    return { status: 'low', summary: 'No workouts recorded this week.' };
  }

  let status: CoachingResponse['training_load']['status'];
  const parts: string[] = [];

  parts.push(`${tc.workouts_7d} workout${tc.workouts_7d !== 1 ? 's' : ''} this week`);
  if (tc.grappling_sessions_7d > 0) {
    parts.push(`${tc.grappling_sessions_7d} grappling`);
  }
  parts.push(`${tc.rest_days_7d} rest day${tc.rest_days_7d !== 1 ? 's' : ''}`);

  // Thresholds adjust for comp prep and target sessions
  const highThreshold = prefs.comp_prep ? 7 : 6;
  const consecutiveThreshold = prefs.comp_prep ? 5 : 4;

  if (tc.rest_days_7d === 0 && tc.workouts_7d >= highThreshold) {
    status = 'overreaching';
  } else if (tc.workouts_7d >= highThreshold || tc.consecutive_training_days >= consecutiveThreshold) {
    status = 'high';
  } else if (tc.workouts_7d >= Math.max(2, getTargetSessionsPerWeek(prefs) - 1) && tc.rest_days_7d >= 1) {
    status = 'balanced';
  } else if (tc.workouts_7d < Math.max(1, getTargetSessionsPerWeek(prefs) - 2)) {
    status = 'low';
  } else {
    status = 'balanced';
  }

  // Add target context
  if (tc.workouts_7d < getTargetSessionsPerWeek(prefs)) {
    parts.push(`target: ${getTargetSessionsPerWeek(prefs)}/week`);
  }

  return { status, summary: parts.join(', ') + '.' };
}

function buildGrappling(
  p: AIPayload,
  prefs: CoachingPreferences,
): CoachingResponse['grappling'] {
  const tc = p.training_context;

  if (tc.grappling_sessions_7d === 0) {
    return {
      summary: 'No grappling sessions this week.',
      suggestion: p.readiness.level === 'green'
        ? 'Good day to get on the mats.'
        : p.readiness.level === 'red'
          ? 'Focus on recovery before your next session.'
          : 'Consider a light technique-focused session.',
    };
  }

  // Build rich summary using session-specific detail
  const parts: string[] = [];
  parts.push(`${tc.grappling_sessions_7d} session${tc.grappling_sessions_7d !== 1 ? 's' : ''} this week`);
  if (tc.hard_sessions_7d > 0) parts.push(`${tc.hard_sessions_7d} hard`);
  if (tc.sparring_sessions_7d > 0) parts.push(`${tc.sparring_sessions_7d} sparring/comp`);
  if (tc.avg_rpe_7d != null) parts.push(`avg RPE ${tc.avg_rpe_7d}`);
  const summary = parts.join(' · ') + '.';

  let suggestion: string;

  // High hard/sparring load with poor recovery
  if (tc.hard_sessions_7d >= 3 && p.readiness.level !== 'green') {
    suggestion = 'Multiple hard sessions this week with suboptimal recovery. Switch to drilling or light positional rounds today.';
  }
  // High sparring accumulation
  else if (tc.sparring_sessions_7d >= 3) {
    suggestion = p.readiness.level === 'green'
      ? 'Heavy sparring week but recovery is good. One more hard session is fine, then plan a lighter day.'
      : 'Sparring load is high. Prioritize technique and flow today.';
  }
  // High RPE trend
  else if (tc.avg_rpe_7d != null && tc.avg_rpe_7d >= 8) {
    suggestion = 'Average RPE is high this week. Consider a technique-focused session to give your body a break.';
  }
  // Green + moderate load — can push
  else if (p.readiness.level === 'green' && tc.grappling_sessions_7d < 4) {
    suggestion = prefs.goal === 'skill_development'
      ? 'Body is ready. Good day for focused technique drilling or hard positional rounds.'
      : prefs.comp_prep
        ? 'Body is ready. Good day for competition-style sparring — match intensity and timing.'
        : 'Body is ready for hard rolling. Good day for competition-style sparring or intensive drilling.';
  }
  // High frequency but green
  else if (tc.grappling_sessions_7d >= 4 && p.readiness.level === 'green') {
    suggestion = 'High frequency but recovery is strong. You can push today — just plan a rest day soon.';
  }
  // Yellow — moderate approach
  else if (p.readiness.level === 'yellow') {
    suggestion = 'Keep it technical today — positional rounds and drilling over hard sparring.';
  }
  // Red — recovery
  else if (p.readiness.level === 'red') {
    suggestion = 'Recovery signals are low. If you must train, keep it light — flow rolling or video study.';
  }
  // Default moderate
  else {
    suggestion = 'Moderate approach today. Mix technique work with light positional sparring.';
  }

  return { summary, suggestion };
}

function buildConfidence(p: AIPayload): CoachingResponse['confidence'] {
  const { coverage, sync } = p;

  let level: 'high' | 'moderate' | 'low';
  const parts: string[] = [];

  if (coverage.days_available >= 14 && coverage.has_sleep && coverage.has_hrv) {
    level = 'high';
    parts.push(`${coverage.days_available} days of data`);
  } else if (coverage.days_available >= 7) {
    level = 'moderate';
    parts.push(`${coverage.days_available} days — accuracy improves with 14+`);
  } else {
    level = 'low';
    parts.push(`Only ${coverage.days_available} day${coverage.days_available !== 1 ? 's' : ''} — need more data`);
  }

  if (!coverage.has_hrv) parts.push('No HRV data');
  if (!coverage.has_sleep) parts.push('No sleep data');
  if (!coverage.has_recovery) parts.push('No recovery score');

  if (sync.data_age_hours != null && sync.data_age_hours > 12) {
    parts.push(`Data is ${Math.round(sync.data_age_hours)}h old — sync for fresh insights`);
  }

  parts.push(`Sources: ${coverage.providers.join(', ') || 'none'}`);

  return { level, note: parts.join('. ') + '.' };
}

function insufficientDataCoaching(p: AIPayload): CoachingResponse {
  return {
    generated_at: new Date().toISOString(),
    source: 'local',
    readiness: { level: 'grey', headline: 'Insufficient data' },
    today_recommendation: {
      action: 'unknown',
      summary: 'Not enough data for a personalized recommendation.',
      detail: 'Connect a health source on the Health tab and sync at least 2 days of data to get training guidance.',
    },
    recovery: { status: 'unknown', summary: 'No recovery data.', actions: ['Sync health data'] },
    sleep: { status: 'unknown', summary: 'No sleep data.' },
    training_load: { status: 'unknown', summary: 'No workout data.' },
    grappling: { summary: 'No grappling data.', suggestion: 'Sync health data to get grappling-specific guidance.' },
    cautions: [],
    confidence: {
      level: 'low',
      note: `${p.coverage.days_available} day${p.coverage.days_available !== 1 ? 's' : ''} of data. Need at least 2 for guidance, 14+ for strong personalization.`,
    },
  };
}

function mapLevel(level: string): CoachingResponse['today_recommendation']['action'] {
  switch (level) {
    case 'green': return 'push';
    case 'yellow': return 'moderate';
    case 'red': return 'light';
    default: return 'unknown';
  }
}
