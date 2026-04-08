/**
 * Health data store — manages permissions, sync, and normalized daily metrics.
 * Connects native health services to the shared normalization layer.
 */
import { Platform } from 'react-native';
import { create } from 'zustand';
import { HealthProvider, normalizeHealthData } from '@lauburu/shared';
import type {
  DailyMetrics,
  HealthPermissions,
  HealthMetricType,
} from '@lauburu/shared';
import { getHealthService } from '../services/health';

interface HealthState {
  /** Current permission state */
  permissions: HealthPermissions | null;

  /** Whether a sync is in progress */
  syncing: boolean;

  /** Last successful sync timestamp */
  lastSyncAt: string | null;

  /** Normalized daily metrics from native health source */
  days: DailyMetrics[];

  /** Today's metrics (convenience accessor) */
  today: DailyMetrics | null;

  /** Error from last operation */
  error: string | null;

  /** Check permissions without requesting */
  checkPermissions: () => Promise<void>;

  /** Request health permissions from user */
  requestPermissions: () => Promise<boolean>;

  /** Sync health data for the last N days */
  syncData: (userId: string, daysBack?: number) => Promise<void>;
}

const todayStr = () => new Date().toISOString().slice(0, 10);

export const useHealthStore = create<HealthState>((set, get) => ({
  permissions: null,
  syncing: false,
  lastSyncAt: null,
  days: [],
  today: null,
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

      // Check if at least one metric was authorized
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
      const [
        restingHr,
        hrv,
        steps,
        activeCal,
        workouts,
        sleep,
      ] = await Promise.all([
        service.fetchSamples('resting_heart_rate', range),
        service.fetchSamples('hrv', range),
        service.fetchSamples('steps', range),
        service.fetchSamples('active_calories', range),
        service.fetchWorkouts(range),
        service.fetchSleep(range),
      ]);

      // Combine all samples
      const allSamples = [...restingHr, ...hrv, ...steps, ...activeCal];

      // Determine provider based on platform
      const provider =
        Platform.OS === 'ios'
          ? HealthProvider.APPLE_HEALTH
          : HealthProvider.MANUAL; // HC normalizes as manual for now

      // Normalize through shared layer
      const days = normalizeHealthData(
        userId,
        provider,
        allSamples,
        workouts,
        sleep,
      );

      const today = days.find((d) => d.date === todayStr()) ?? null;

      set({
        days,
        today,
        syncing: false,
        lastSyncAt: new Date().toISOString(),
        error: null,
      });
    } catch (e: any) {
      set({
        syncing: false,
        error: e?.message ?? 'Health sync failed',
      });
    }
  },
}));
