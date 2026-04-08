/**
 * Feedback and outcome types for the data-capture/training-example pipeline.
 *
 * Three capture points per training day:
 * 1. Recommendation feedback — after seeing coaching output
 * 2. Session outcome — after training
 * 3. Next-day check-in — the following morning
 *
 * These combine with health inputs + training context + coaching output
 * to form complete training examples for future model personalization.
 */

// ---------------------------------------------------------------------------
// 1. Recommendation feedback
// ---------------------------------------------------------------------------

export interface RecommendationFeedback {
  id: string;
  date: string; // YYYY-MM-DD
  created_at: string;

  /** What readiness level was shown */
  readiness_shown: 'green' | 'yellow' | 'red' | 'grey';
  /** What action was recommended */
  recommendation_shown: 'push' | 'moderate' | 'light' | 'rest' | 'unknown';

  /** Did you follow the recommendation? */
  followed: 'yes' | 'partly' | 'no';
  /** How accurate was it? 1-5 */
  accuracy: number;
  /** How useful was it? 1-5 */
  usefulness: number;

  persisted: boolean;
}

export interface RecommendationFeedbackInput {
  date: string;
  readiness_shown: RecommendationFeedback['readiness_shown'];
  recommendation_shown: RecommendationFeedback['recommendation_shown'];
  followed: RecommendationFeedback['followed'];
  accuracy: number;
  usefulness: number;
}

// ---------------------------------------------------------------------------
// 2. Session outcome
// ---------------------------------------------------------------------------

export interface SessionOutcome {
  id: string;
  /** Links to TrainingSession.id or a health-derived workout date */
  session_ref: string;
  date: string;
  created_at: string;

  /** How the session felt */
  difficulty_feel: 'too_hard' | 'right' | 'too_easy';
  /** Performance quality 1-5 */
  performance: number;
  /** Soreness level 1-5 */
  soreness: number;
  /** Fatigue level 1-5 */
  fatigue: number;
  /** Confidence / how good you felt 1-5 */
  confidence: number;
  /** Optional notes */
  notes: string;

  persisted: boolean;
}

export interface SessionOutcomeInput {
  session_ref: string;
  date: string;
  difficulty_feel: SessionOutcome['difficulty_feel'];
  performance: number;
  soreness: number;
  fatigue: number;
  confidence: number;
  notes?: string;
}

// ---------------------------------------------------------------------------
// 3. Next-day check-in
// ---------------------------------------------------------------------------

export interface NextDayCheckin {
  id: string;
  /** The date being reported ON (today), covering yesterday's training */
  date: string;
  /** The training date being evaluated */
  training_date: string;
  created_at: string;

  /** Recovery vs expectation */
  recovery_feel: 'better' | 'same' | 'worse';
  /** Was the recommendation right? */
  recommendation_accuracy: 'right' | 'wrong' | 'mixed';
  /** Any injury or warning */
  injury_flag: boolean;
  injury_notes: string;

  persisted: boolean;
}

export interface NextDayCheckinInput {
  training_date: string;
  recovery_feel: NextDayCheckin['recovery_feel'];
  recommendation_accuracy: NextDayCheckin['recommendation_accuracy'];
  injury_flag: boolean;
  injury_notes?: string;
}

// ---------------------------------------------------------------------------
// 4. Training example — complete data point for future model training
// ---------------------------------------------------------------------------

/**
 * A complete training example combining all signals for one training day.
 * This is the canonical shape for future model training / personalization.
 *
 * Produced by assembleTrainingExample() from the day's health data,
 * coaching output, behavior, and outcomes.
 */
export interface TrainingExample {
  /** Schema version for forward compatibility */
  version: 1;

  /** The training date */
  date: string;
  generated_at: string;

  /** Health inputs (snapshot of what was available) */
  health_inputs: {
    recovery_score: number | null;
    hrv_ms: number | null;
    resting_hr: number | null;
    sleep_hours: number | null;
    daily_strain: number | null;
    step_count: number | null;
    providers: string[];
  };

  /** Training context at time of recommendation */
  training_context: {
    workouts_7d: number;
    grappling_sessions_7d: number;
    rest_days_7d: number;
    consecutive_training_days: number;
    hard_sessions_7d: number;
    avg_rpe_7d: number | null;
  };

  /** What the system recommended */
  recommendation: {
    readiness: string;
    action: string;
    summary: string;
  };

  /** What the user actually did */
  behavior: {
    followed_recommendation: 'yes' | 'partly' | 'no' | null;
    session_type: string | null;
    session_intensity: string | null;
    session_duration_min: number | null;
    session_rpe: number | null;
  };

  /** Same-day outcome */
  same_day_outcome: {
    difficulty_feel: string | null;
    performance: number | null;
    soreness: number | null;
    fatigue: number | null;
    confidence: number | null;
  } | null;

  /** Next-day outcome */
  next_day_outcome: {
    recovery_feel: string | null;
    recommendation_was: string | null;
    injury_flag: boolean;
  } | null;

  /** Recommendation feedback ratings */
  feedback: {
    accuracy: number | null;
    usefulness: number | null;
  } | null;
}
