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
import { useTierStore } from './tier-store';
import { secureStorage } from './secure-storage';

type SyncStatus = 'idle' | 'syncing' | 'synced' | 'failed';

const STORAGE_KEY = 'feedback_store_v1';

function genId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

interface PersistedFeedbackBlob {
  recommendations: RecommendationFeedback[];
  outcomes: SessionOutcome[];
  checkins: NextDayCheckin[];
  examples: TrainingExample[];
  lastSyncAt: string | null;
  lastSyncError: string | null;
}

async function persistSafely(blob: PersistedFeedbackBlob): Promise<void> {
  try {
    const isEmpty =
      blob.recommendations.length === 0 &&
      blob.outcomes.length === 0 &&
      blob.checkins.length === 0 &&
      blob.examples.length === 0 &&
      !blob.lastSyncAt &&
      !blob.lastSyncError;
    if (isEmpty) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(blob));
  } catch {
    // Silent — preserve UX even if local persistence fails.
  }
}

function buildPersistedBlob(
  state: Pick<
    FeedbackState,
    'recommendations' | 'outcomes' | 'checkins' | 'examples' | 'lastSyncAt' | 'lastSyncError'
  >,
): PersistedFeedbackBlob {
  return {
    recommendations: state.recommendations,
    outcomes: state.outcomes,
    checkins: state.checkins,
    examples: state.examples,
    lastSyncAt: state.lastSyncAt,
    lastSyncError: state.lastSyncError,
  };
}

function countPendingExamples(
  examples: TrainingExample[],
  recommendations: RecommendationFeedback[],
): number {
  return examples.filter(
    (example) =>
      !recommendations.find(
        (recommendation) =>
          recommendation.date === example.date && recommendation.persisted,
      ),
  ).length;
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
  hydrated: boolean;

  hydrate: () => Promise<void>;

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
  hydrated: false,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      if (!raw) {
        set({ hydrated: true });
        return;
      }
      const parsed = JSON.parse(raw) as Partial<PersistedFeedbackBlob>;
      const recommendations = Array.isArray(parsed.recommendations)
        ? parsed.recommendations
        : [];
      const outcomes = Array.isArray(parsed.outcomes) ? parsed.outcomes : [];
      const checkins = Array.isArray(parsed.checkins) ? parsed.checkins : [];
      const examples = Array.isArray(parsed.examples) ? parsed.examples : [];
      set({
        recommendations,
        outcomes,
        checkins,
        examples,
        lastSyncAt: parsed.lastSyncAt ?? null,
        lastSyncError: parsed.lastSyncError ?? null,
        pendingCount: countPendingExamples(examples, recommendations),
        syncStatus: 'idle',
        hydrated: true,
      });
    } catch {
      set({ hydrated: true, syncStatus: 'idle' });
    }
  },

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
    set((s) => {
      const recommendations = [
        ...s.recommendations.filter((r) => r.date !== input.date),
        entry,
      ];
      void persistSafely(buildPersistedBlob({ ...s, recommendations }));
      return { recommendations };
    });
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
    set((s) => {
      const outcomes = [
        ...s.outcomes.filter((o) => o.session_ref !== input.session_ref),
        entry,
      ];
      void persistSafely(buildPersistedBlob({ ...s, outcomes }));
      return { outcomes };
    });
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
    set((s) => {
      const checkins = [
        ...s.checkins.filter((c) => c.training_date !== input.training_date),
        entry,
      ];
      void persistSafely(buildPersistedBlob({ ...s, checkins }));
      return { checkins };
    });
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
    set((s) => {
      const examples = [
        ...s.examples.filter((e) => e.date !== date),
        example,
      ];
      const pendingCount = countPendingExamples(examples, s.recommendations);
      void persistSafely(
        buildPersistedBlob({
          ...s,
          examples,
          lastSyncError: null,
        }),
      );
      return {
        examples,
        pendingCount,
        lastSyncError: null,
      };
    });

    return example;
  },

  syncToBackend: async () => {
    // Tier gate
    if (!useTierStore.getState().can('backend_persistence')) {
      set({ syncStatus: 'failed', lastSyncError: 'Cloud sync requires Starter plan' });
      return false;
    }

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
      set((s) => {
        const recommendations = s.recommendations.map((r) => ({
          ...r,
          persisted: true,
        }));
        const outcomes = s.outcomes.map((o) => ({ ...o, persisted: true }));
        const checkins = s.checkins.map((c) => ({ ...c, persisted: true }));
        const nextState = {
          syncStatus: 'synced' as const,
          lastSyncAt: new Date().toISOString(),
          lastSyncError: null,
          pendingCount: 0,
          recommendations,
          outcomes,
          checkins,
        };
        void persistSafely(buildPersistedBlob({ ...s, ...nextState }));
        return nextState;
      });
      return true;
    } else {
      set((s) => {
        const nextState = {
          syncStatus: 'failed' as const,
          lastSyncError: result.error ?? 'Sync failed',
        };
        void persistSafely(buildPersistedBlob({ ...s, ...nextState }));
        return nextState;
      });
      return false;
    }
  },
}));
