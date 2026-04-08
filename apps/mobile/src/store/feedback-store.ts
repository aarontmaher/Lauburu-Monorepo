/**
 * Feedback and outcome store — captures training examples daily.
 *
 * Three capture points:
 * 1. Recommendation feedback (after seeing coaching)
 * 2. Session outcome (after training)
 * 3. Next-day check-in (following morning)
 */
import { create } from 'zustand';
import type {
  RecommendationFeedback,
  RecommendationFeedbackInput,
  SessionOutcome,
  SessionOutcomeInput,
  NextDayCheckin,
  NextDayCheckinInput,
} from '@lauburu/shared';

function genId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface FeedbackState {
  recommendations: RecommendationFeedback[];
  outcomes: SessionOutcome[];
  checkins: NextDayCheckin[];

  addRecommendationFeedback: (input: RecommendationFeedbackInput) => RecommendationFeedback;
  addSessionOutcome: (input: SessionOutcomeInput) => SessionOutcome;
  addNextDayCheckin: (input: NextDayCheckinInput) => NextDayCheckin;

  /** Get feedback for a specific date */
  getFeedbackForDate: (date: string) => RecommendationFeedback | undefined;
  getOutcomeForSession: (sessionRef: string) => SessionOutcome | undefined;
  getCheckinForDate: (date: string) => NextDayCheckin | undefined;
}

export const useFeedbackStore = create<FeedbackState>((set, get) => ({
  recommendations: [],
  outcomes: [],
  checkins: [],

  addRecommendationFeedback: (input) => {
    const entry: RecommendationFeedback = {
      id: genId('rf'),
      date: input.date,
      created_at: new Date().toISOString(),
      readiness_shown: input.readiness_shown,
      recommendation_shown: input.recommendation_shown,
      followed: input.followed,
      accuracy: input.accuracy,
      usefulness: input.usefulness,
      persisted: false,
    };
    set((s) => ({
      recommendations: [
        ...s.recommendations.filter((r) => r.date !== input.date),
        entry,
      ],
    }));
    return entry;
  },

  addSessionOutcome: (input) => {
    const entry: SessionOutcome = {
      id: genId('so'),
      session_ref: input.session_ref,
      date: input.date,
      created_at: new Date().toISOString(),
      difficulty_feel: input.difficulty_feel,
      performance: input.performance,
      soreness: input.soreness,
      fatigue: input.fatigue,
      confidence: input.confidence,
      notes: input.notes ?? '',
      persisted: false,
    };
    set((s) => ({
      outcomes: [
        ...s.outcomes.filter((o) => o.session_ref !== input.session_ref),
        entry,
      ],
    }));
    return entry;
  },

  addNextDayCheckin: (input) => {
    const today = new Date().toISOString().slice(0, 10);
    const entry: NextDayCheckin = {
      id: genId('nd'),
      date: today,
      training_date: input.training_date,
      created_at: new Date().toISOString(),
      recovery_feel: input.recovery_feel,
      recommendation_accuracy: input.recommendation_accuracy,
      injury_flag: input.injury_flag,
      injury_notes: input.injury_notes ?? '',
      persisted: false,
    };
    set((s) => ({
      checkins: [
        ...s.checkins.filter((c) => c.training_date !== input.training_date),
        entry,
      ],
    }));
    return entry;
  },

  getFeedbackForDate: (date) =>
    get().recommendations.find((r) => r.date === date),
  getOutcomeForSession: (ref) =>
    get().outcomes.find((o) => o.session_ref === ref),
  getCheckinForDate: (date) =>
    get().checkins.find((c) => c.training_date === date),
}));
