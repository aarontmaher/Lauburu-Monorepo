/**
 * Assemble complete training examples from a day's data.
 *
 * A training example is a single row suitable for future model training:
 * health inputs + context + recommendation + behavior + outcomes.
 *
 * Design: deterministic, source-agnostic, null-safe.
 * Missing data produces null fields, not errors.
 */
import type { DailyMetrics } from '../types/health';
import type { TrainingSession } from '../types/training';
import type {
  TrainingExample,
  RecommendationFeedback,
  SessionOutcome,
  NextDayCheckin,
} from '../types/feedback';
import type { AIPayload } from './ai-payload';
import type { CoachingResponse } from './coaching';

export function assembleTrainingExample(
  date: string,
  dayMetrics: DailyMetrics | null,
  session: TrainingSession | null,
  payload: AIPayload | null,
  coaching: CoachingResponse | null,
  feedback: RecommendationFeedback | null,
  outcome: SessionOutcome | null,
  nextDay: NextDayCheckin | null,
): TrainingExample {
  return {
    version: 1,
    date,
    generated_at: new Date().toISOString(),

    health_inputs: {
      recovery_score: dayMetrics?.recovery_score ?? null,
      hrv_ms: dayMetrics?.hrv_ms ?? null,
      resting_hr: dayMetrics?.resting_hr ?? null,
      sleep_hours: dayMetrics?.sleep_hours ?? null,
      daily_strain: dayMetrics?.daily_strain ?? null,
      step_count: dayMetrics?.step_count ?? null,
      providers: payload?.coverage.providers ?? [],
    },

    training_context: {
      workouts_7d: payload?.training_context.workouts_7d ?? 0,
      grappling_sessions_7d: payload?.training_context.grappling_sessions_7d ?? 0,
      rest_days_7d: payload?.training_context.rest_days_7d ?? 0,
      consecutive_training_days: payload?.training_context.consecutive_training_days ?? 0,
      hard_sessions_7d: payload?.training_context.hard_sessions_7d ?? 0,
      avg_rpe_7d: payload?.training_context.avg_rpe_7d ?? null,
    },

    recommendation: {
      readiness: coaching?.readiness.level ?? 'unknown',
      action: coaching?.today_recommendation.action ?? 'unknown',
      summary: coaching?.today_recommendation.summary ?? '',
    },

    behavior: {
      followed_recommendation: feedback?.followed ?? null,
      session_type: session?.type ?? null,
      session_intensity: session?.intensity ?? null,
      session_duration_min: session?.duration_min ?? null,
      session_rpe: session?.rpe ?? null,
    },

    same_day_outcome: outcome
      ? {
          difficulty_feel: outcome.difficulty_feel,
          performance: outcome.performance,
          soreness: outcome.soreness,
          fatigue: outcome.fatigue,
          confidence: outcome.confidence,
        }
      : null,

    next_day_outcome: nextDay
      ? {
          recovery_feel: nextDay.recovery_feel,
          recommendation_was: nextDay.recommendation_accuracy,
          injury_flag: nextDay.injury_flag,
        }
      : null,

    feedback: feedback
      ? {
          accuracy: feedback.accuracy,
          usefulness: feedback.usefulness,
        }
      : null,
  };
}
