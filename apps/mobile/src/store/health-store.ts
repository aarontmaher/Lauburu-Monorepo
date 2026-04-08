/**
 * Health data store — manages permissions, sync, backend persistence,
 * and derived features. Connects native health services through the
 * shared normalization and feature derivation layers.
 */
import { Platform } from 'react-native';
import { create } from 'zustand';
import {
  HealthProvider,
  normalizeHealthData,
  deriveFeatures,
  computeFlags,
  toBackendPayload,
  importHealthData,
  buildAIHealthContext,
  generateInsights,
  exportAIPayload,
  generateCoaching,
  mergeTrainingSessions,
} from '@lauburu/shared';
import type {
  DailyMetrics,
  DerivedFeatures,
  HealthPermissions,
  AIHealthContext,
  TrainingInsight,
  AIPayload,
  CoachingResponse,
} from '@lauburu/shared';
import type { HealthFlag } from '@lauburu/shared';
import { getHealthService } from '../services/health';
import { useAuthStore } from './auth-store';
import { useTrainingStore } from './training-store';

interface HealthState {
  /** Current permission state */
  permissions: HealthPermissions | null;

  /** Whether a sync is in progress */
  syncing: boolean;

  /** Whether a backend persist is in progress */
  persisting: boolean;

  /** Last successful native sync timestamp */
  lastSyncAt: string | null;

  /** Last successful backend persist timestamp */
  lastPersistedAt: string | null;

  /** Backend persist result summary */
  lastPersistResult: { recordCount: number; dateRange: string } | null;

  /** Normalized daily metrics from native health source */
  days: DailyMetrics[];

  /** Today's metrics (convenience accessor) */
  today: DailyMetrics | null;

  /** AI-ready derived features computed from days[] */
  features: DerivedFeatures | null;

  /** Notable flags / conditions for UI display */
  flags: HealthFlag[];

  /** Compact AI health context (for future MCP/AI consumption) */
  aiContext: AIHealthContext | null;

  /** Rules-based training insights */
  insights: TrainingInsight | null;

  /** Exportable AI payload for MCP/coaching consumption */
  aiPayload: AIPayload | null;

  /** Structured coaching response */
  coaching: CoachingResponse | null;

  /** Error from last operation */
  error: string | null;

  /** Check permissions without requesting */
  checkPermissions: () => Promise<void>;

  /** Request health permissions from user */
  requestPermissions: () => Promise<boolean>;

  /** Sync health data for the last N days from native source */
  syncData: (userId: string, daysBack?: number) => Promise<void>;

  /** Persist current days[] to Supabase backend */
  persistToBackend: () => Promise<boolean>;
}

const todayStr = () => new Date().toISOString().slice(0, 10);

export const useHealthStore = create<HealthState>((set, get) => ({
  permissions: null,
  syncing: false,
  persisting: false,
  lastSyncAt: null,
  lastPersistedAt: null,
  lastPersistResult: null,
  days: [],
  today: null,
  features: null,
  flags: [],
  aiContext: null,
  insights: null,
  aiPayload: null,
  coaching: null,
  error: null,

  checkPermissions: async () => {
    try {
      const service = getHealthService();
      const perms = await service.checkPermissions();
      set({ permissions: perms, error: null });
    } catch (e: any) {
      set({ error: e?.message ?? 'Permission check failed' });
    }
  },

  requestPermissions: async () => {
    try {
      const service = getHealthService();
      const perms = await service.requestPermissions();
      set({ permissions: perms, error: null });
      const anyAuthorized = Object.values(perms.permissions).some(
        (s) => s === 'authorized',
      );
      return anyAuthorized;
    } catch (e: any) {
      set({ error: e?.message ?? 'Permission request failed' });
      return false;
    }
  },

  syncData: async (userId, daysBack = 7) => {
    const { permissions } = get();
    if (!permissions?.available) {
      set({ error: 'Health data not available on this device' });
      return;
    }

    set({ syncing: true, error: null });

    try {
      const service = getHealthService();
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - daysBack);
      const range = { start, end };

      // Fetch all metric types in parallel
      const [restingHr, hrv, steps, activeCal, workouts, sleep] =
        await Promise.all([
          service.fetchSamples('resting_heart_rate', range),
          service.fetchSamples('hrv', range),
          service.fetchSamples('steps', range),
          service.fetchSamples('active_calories', range),
          service.fetchWorkouts(range),
          service.fetchSleep(range),
        ]);

      const allSamples = [...restingHr, ...hrv, ...steps, ...activeCal];

      const provider =
        Platform.OS === 'ios'
          ? HealthProvider.APPLE_HEALTH
          : HealthProvider.MANUAL;

      // Normalize through shared layer
      const nativeDays = normalizeHealthData(
        userId,
        provider,
        allSamples,
        workouts,
        sleep,
      );

      // Merge manual training sessions
      const trainingSessions = useTrainingStore.getState().sessions;
      const days = mergeTrainingSessions(nativeDays, trainingSessions);

      const today = days.find((d) => d.date === todayStr()) ?? null;

      // Derive AI-ready features (includes manual grappling context)
      const features = deriveFeatures(days);
      const flags = computeFlags(features, today);

      // Build AI context + generate insights
      const aiContext = buildAIHealthContext(days, features, flags);
      const insights = generateInsights(aiContext);

      const now = new Date().toISOString();
      const { lastPersistedAt } = get();

      // Build exportable AI payload + coaching
      const aiPayload = exportAIPayload(
        days, features, flags, insights, aiContext, now, lastPersistedAt,
      );
      const coaching = generateCoaching(aiPayload);

      set({
        days,
        today,
        features,
        flags,
        aiContext,
        insights,
        aiPayload,
        coaching,
        syncing: false,
        lastSyncAt: now,
        error: null,
      });
    } catch (e: any) {
      set({
        syncing: false,
        error: e?.message ?? 'Health sync failed',
      });
    }
  },

  persistToBackend: async () => {
    const { days } = get();
    if (days.length === 0) {
      set({ error: 'No health data to persist' });
      return false;
    }

    const getToken = useAuthStore.getState().getAccessToken;
    const token = await getToken();
    if (!token) {
      set({ error: 'Sign in to save health data to your account' });
      return false;
    }

    set({ persisting: true, error: null });

    try {
      const provider =
        Platform.OS === 'ios' ? 'apple_health' : 'health_connect';

      const payload = toBackendPayload(days);

      const result = await importHealthData(
        getToken,
        provider,
        'native_sync',
        payload,
      );

      if (result?.ok) {
        const dateRange = result.date_range
          ? `${result.date_range.start} → ${result.date_range.end}`
          : '';
        set({
          persisting: false,
          lastPersistedAt: new Date().toISOString(),
          lastPersistResult: {
            recordCount: result.record_count,
            dateRange,
          },
          error: null,
        });
        return true;
      } else {
        set({
          persisting: false,
          error: 'Backend import failed',
        });
        return false;
      }
    } catch (e: any) {
      set({
        persisting: false,
        error: e?.message ?? 'Backend persist failed',
      });
      return false;
    }
  },
}));
