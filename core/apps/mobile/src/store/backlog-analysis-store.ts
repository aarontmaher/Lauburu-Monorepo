/**
 * Backlog-analysis store — tracks the first-run "should we analyse
 * your history?" permission flow per-user.
 *
 * States:
 *   - not_started: user has not opened the card yet (or record missing)
 *   - permission_requested: user has seen the card but not answered
 *   - running: backend is analysing the window
 *   - partial / complete / failed: end states
 *   - skipped: user tapped "Not now"
 *
 * The backend is authoritative — this store mirrors it. We never
 * fabricate or persist a "complete" state without a backend
 * confirmation. Local state is wiped on sign-out by clear-user-data.
 */
import { create } from 'zustand';
import {
  buildBacklogClientConfig,
  getBacklogStatus,
  startBacklog,
  skipBacklog,
  type BacklogStatusResponse,
} from '../services/backlog-analysis-client';
import { useAuthStore } from './auth-store';

type BacklogStatusValue = BacklogStatusResponse['status']['status'];

interface BacklogAnalysisState {
  status: BacklogStatusValue;
  record: BacklogStatusResponse['status'] | null;
  summary: BacklogStatusResponse['summary'] | null;
  trends: BacklogStatusResponse['trends'];
  loading: boolean;
  starting: boolean;
  error: string | null;
  lastFetchedAt: string | null;

  refresh: () => Promise<void>;
  start: (opts?: { windowDays?: number }) => Promise<void>;
  skip: () => Promise<void>;
  reset: () => void;
}

const initial: Pick<
  BacklogAnalysisState,
  'status' | 'record' | 'summary' | 'trends' | 'loading' | 'starting' | 'error' | 'lastFetchedAt'
> = {
  status: 'not_started',
  record: null,
  summary: null,
  trends: [],
  loading: false,
  starting: false,
  error: null,
  lastFetchedAt: null,
};

export const useBacklogAnalysisStore = create<BacklogAnalysisState>((set) => ({
  ...initial,

  refresh: async () => {
    const user = useAuthStore.getState().user;
    const session = useAuthStore.getState().session;
    const cfg = buildBacklogClientConfig(user?.id, session?.access_token ?? null);
    if (!cfg) {
      set({ ...initial, error: 'Sign in to see backlog analysis status.' });
      return;
    }
    set({ loading: true, error: null });
    const res = await getBacklogStatus(cfg);
    if (!res.ok) {
      set({
        loading: false,
        error: res.error,
        // 401/403: keep previous state (might be sign-out in flight)
      });
      return;
    }
    const { status: record, summary, trends } = res.data;
    set({
      loading: false,
      status: record.status,
      record,
      summary,
      trends: trends ?? [],
      lastFetchedAt: new Date().toISOString(),
      error: null,
    });
  },

  start: async (opts) => {
    const user = useAuthStore.getState().user;
    const session = useAuthStore.getState().session;
    const cfg = buildBacklogClientConfig(user?.id, session?.access_token ?? null);
    if (!cfg) {
      set({ error: 'Sign in before running backlog analysis.' });
      return;
    }
    set({ starting: true, error: null, status: 'running' });
    const res = await startBacklog(cfg, {
      windowDays: opts?.windowDays ?? 30,
      ...(opts as any)?.historyScope ? { historyScope: (opts as any).historyScope } : {},
    });
    if (!res.ok) {
      set({ starting: false, error: res.error, status: 'failed' });
      return;
    }
    set({
      starting: false,
      status: res.data.status.status,
      record: res.data.status,
      summary: res.data.summary,
      trends: res.data.trendCandidates ?? [],
      lastFetchedAt: new Date().toISOString(),
      error: null,
    });
  },

  skip: async () => {
    const user = useAuthStore.getState().user;
    const session = useAuthStore.getState().session;
    const cfg = buildBacklogClientConfig(user?.id, session?.access_token ?? null);
    if (!cfg) {
      // Client-only skip if not signed in; remote sync happens on next refresh.
      set({ status: 'skipped' });
      return;
    }
    set({ status: 'skipped', error: null });
    const res = await skipBacklog(cfg);
    if (res.ok) {
      set({ record: res.data.status });
    }
    // If remote skip fails, keep local state so the prompt doesn't re-appear.
  },

  reset: () => set({ ...initial }),
}));
