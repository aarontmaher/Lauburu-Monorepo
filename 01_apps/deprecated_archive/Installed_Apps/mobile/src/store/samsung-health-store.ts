/**
 * Samsung Health direct integration store.
 *
 * Tracks the Samsung Health Data SDK connection state separately from
 * the Samsung-via-Health-Connect provenance state (which lives in
 * health-store.samsungHealthViaHc). Both paths can coexist.
 */
import { create } from 'zustand';
import {
  checkSamsungHealthDirectStatus,
  requestSamsungHealthPermissions,
  readSamsungHealthData,
  type SamsungHealthDirectState,
} from '../services/samsung-health-direct';

interface SamsungHealthStoreState {
  state: SamsungHealthDirectState;
  loading: boolean;
  syncing: boolean;
  error: string | null;
  lastReadData: Awaited<ReturnType<typeof readSamsungHealthData>> | null;

  checkStatus: () => Promise<void>;
  requestPermissions: () => Promise<boolean>;
  syncData: (startDate: string, endDate: string) => Promise<void>;
  reset: () => void;
}

const DEFAULT_STATE: SamsungHealthDirectState = {
  status: 'not_checked',
  sdkAvailable: false,
  samsungHealthAppInstalled: false,
  developerModeActive: false,
  lastSyncAt: null,
  domainsAvailable: [],
  reason: null,
};

export const useSamsungHealthStore = create<SamsungHealthStoreState>((set) => ({
  state: DEFAULT_STATE,
  loading: false,
  syncing: false,
  error: null,
  lastReadData: null,

  checkStatus: async () => {
    set({ loading: true, error: null });
    try {
      const result = await checkSamsungHealthDirectStatus();
      set({ state: result, loading: false });
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Status check failed' });
    }
  },

  requestPermissions: async () => {
    set({ loading: true, error: null });
    try {
      const granted = await requestSamsungHealthPermissions();
      // Recheck status after permission request
      const result = await checkSamsungHealthDirectStatus();
      set({ state: result, loading: false });
      return granted;
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Permission request failed' });
      return false;
    }
  },

  syncData: async (startDate, endDate) => {
    set({ syncing: true, error: null });
    try {
      const data = await readSamsungHealthData(startDate, endDate);
      const now = new Date().toISOString();
      if (data) {
        const domains: string[] = [];
        if (data.steps.length > 0) domains.push('steps');
        if (data.sleep.length > 0) domains.push('sleep');
        if (data.heartRate.length > 0) domains.push('heart_rate');
        if (data.exercises.length > 0) domains.push('workouts');
        if (data.spo2.length > 0) domains.push('spo2');
        if (data.weight.length > 0) domains.push('body_metrics');
        set((s) => ({
          syncing: false,
          lastReadData: data,
          state: {
            ...s.state,
            status: domains.length > 0 ? 'connected' : 'partial',
            lastSyncAt: now,
            domainsAvailable: domains,
          },
        }));
      } else {
        set({ syncing: false, error: 'No data returned from Samsung Health.' });
      }
    } catch (e) {
      set({ syncing: false, error: e instanceof Error ? e.message : 'Sync failed' });
    }
  },

  reset: () => set({ state: DEFAULT_STATE, loading: false, syncing: false, error: null, lastReadData: null }),
}));
