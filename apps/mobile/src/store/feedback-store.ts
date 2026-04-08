/**
 * Feedback and outcome store — captures training examples daily
 * and syncs them to the backend.
 */
import { create } from 'zustand';
import {
  assembleTrainingExample,
  persistTrainingExamples,
} from '@lauburu/shared';
import type {
  RecommendationFeedback,
  RecommendationFeedbackInput,
  SessionOutcome,
  SessionOutcomeInput,
  NextDayCheckin,
  NextDayCheckinInput,
  TrainingExample,
} from '@lauburu/shared';
import { useAuthStore } from './auth-store';
import { useHealthStore } from './health-store';
import { useTrainingStore } from './training-store';
import { useConsentStore } from './consent-store';

type SyncStatus = 'idle' | 'syncing' | 'synced' | 'failed';

function genId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface FeedbackState {
  recommendations: RecommendationFeedback[];
  outcomes: SessionOutcome[];
  checkins: NextDayCheckin[];

  /** Assembled training examples ready for sync */
  examples: TrainingExample[];

  /** Sync state */
  syncStatus: SyncStatus;
  lastSyncAt: string | null;
  lastSyncError: string | null;
  pendingCount: number;

  addRecommendationFeedback: (input: RecommendationFeedbackInput) => RecommendationFeedback;
  addSessionOutcome: (input: SessionOutcomeInput) => SessionOutcome;
  addNextDayCheckin: (input: NextDayCheckinInput) => NextDayCheckin;

  getFeedbackForDate: (date: string) => RecommendationFeedback | undefined;
  getOutcomeForSession: (sessionRef: string) => SessionOutcome | undefined;
  getCheckinForDate: (date: string) => NextDayCheckin | undefined;

  /** Assemble a training example for a date and add to queue */
  assembleForDate: (date: string) => TrainingExample | null;

  /** Sync pending examples to backend */
  syncToBackend: () => Promise<boolean>;
}

export const useFeedbackStore = create<FeedbackState>((set, get) => ({
  recommendations: [],
  outcomes: [],
  checkins: [],
  examples: [],
  syncStatus: 'idle',
  lastSyncAt: null,
  lastSyncError: null,
  pendingCount: 0,

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
    // Auto-assemble after adding feedback
    setTimeout(() => get().assembleForDate(input.date), 0);
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
    setTimeout(() => get().assembleForDate(input.date), 0);
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
    setTimeout(() => get().assembleForDate(input.training_date), 0);
    return entry;
  },

  getFeedbackForDate: (date) =>
    get().recommendations.find((r) => r.date === date),
  getOutcomeForSession: (ref) =>
    get().outcomes.find((o) => o.session_ref === ref),
  getCheckinForDate: (date) =>
    get().checkins.find((c) => c.training_date === date),

  assembleForDate: (date) => {
    const { recommendations, outcomes, checkins, examples } = get();
    const healthStore = useHealthStore.getState();
    const trainingStore = useTrainingStore.getState();

    const dayMetrics = healthStore.days.find((d) => d.date === date) ?? null;
    const session = trainingStore.sessions.find((s) => s.date === date) ?? null;
    const feedback = recommendations.find((r) => r.date === date) ?? null;
    const outcome = session
      ? outcomes.find((o) => o.session_ref === session.id) ?? null
      : null;
    const nextDay = checkins.find((c) => c.training_date === date) ?? null;

    // Build eligibility from current consent
    const userId = useAuthStore.getState().user?.id ?? null;
    const eligibility = useConsentStore.getState().getEligibility(userId);

    const example = assembleTrainingExample(
      date,
      dayMetrics,
      session,
      healthStore.aiPayload,
      healthStore.coaching,
      feedback,
      outcome,
      nextDay,
      eligibility,
    );

    // Replace existing example for this date
    set((s) => ({
      examples: [
        ...s.examples.filter((e) => e.date !== date),
        example,
      ],
      pendingCount: s.examples.filter((e) => e.date !== date).length + 1 -
        s.examples.filter((e) => e.date !== date).filter(() => false).length,
    }));

    // Recount pending
    const updated = get().examples;
    set({ pendingCount: updated.filter((e) => !get().recommendations.find((r) => r.date === e.date && r.persisted)).length });

    return example;
  },

  syncToBackend: async () => {
    const { examples } = get();
    if (examples.length === 0) return true;

    const auth = useAuthStore.getState();
    const token = await auth.getAccessToken();
    const userId = auth.user?.id;

    if (!token || !userId) {
      set({ syncStatus: 'failed', lastSyncError: 'Not signed in' });
      return false;
    }

    set({ syncStatus: 'syncing', lastSyncError: null });

    const result = await persistTrainingExamples(userId, token, examples);

    if (result.ok) {
      // Mark all feedback as persisted
      set((s) => ({
        syncStatus: 'synced',
        lastSyncAt: new Date().toISOString(),
        lastSyncError: null,
        pendingCount: 0,
        recommendations: s.recommendations.map((r) => ({ ...r, persisted: true })),
        outcomes: s.outcomes.map((o) => ({ ...o, persisted: true })),
        checkins: s.checkins.map((c) => ({ ...c, persisted: true })),
      }));
      return true;
    } else {
      set({
        syncStatus: 'failed',
        lastSyncError: result.error ?? 'Sync failed',
      });
      return false;
    }
  },
}));
