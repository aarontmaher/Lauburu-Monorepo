/**
 * Coaching preferences + weekly schedule store.
 */
import { create } from 'zustand';
import { DEFAULT_PREFERENCES } from '@lauburu/shared';
import type { CoachingPreferences, DayOfWeek, PlannedSession, ScheduleSessionType } from '@lauburu/shared';
import { readStoredJson, writeStoredJson } from './secure-storage';

const STORAGE_KEY = 'coaching_preferences_v1';

function genId(): string {
  return `ps-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

async function persistSafely(preferences: CoachingPreferences): Promise<void> {
  await writeStoredJson(STORAGE_KEY, preferences);
}

function sanitizePreferences(
  value: unknown,
): CoachingPreferences | null {
  if (!value || typeof value !== 'object') return null;
  const parsed = value as Partial<CoachingPreferences>;
  const schedule =
    parsed.schedule && typeof parsed.schedule === 'object'
      ? { ...DEFAULT_PREFERENCES.schedule, ...parsed.schedule }
      : DEFAULT_PREFERENCES.schedule;

  return {
    ...DEFAULT_PREFERENCES,
    ...parsed,
    schedule,
  };
}

interface PreferencesState {
  preferences: CoachingPreferences;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  update: (partial: Partial<Omit<CoachingPreferences, 'schedule'>>) => void;
  reset: () => void;

  // Schedule operations
  addSession: (day: DayOfWeek, type: ScheduleSessionType, time?: string) => void;
  removeSession: (day: DayOfWeek, sessionId: string) => void;
  toggleSession: (day: DayOfWeek, sessionId: string) => void;
  updateSession: (day: DayOfWeek, sessionId: string, updates: Partial<PlannedSession>) => void;
}

export const usePreferencesStore = create<PreferencesState>((set) => ({
  preferences: { ...DEFAULT_PREFERENCES },
  hydrated: false,

  hydrate: async () => {
    const parsed = await readStoredJson<unknown>(STORAGE_KEY);
    const next = sanitizePreferences(parsed);
    set({
      preferences: next ?? { ...DEFAULT_PREFERENCES },
      hydrated: true,
    });
  },

  update: (partial) => {
    set((s) => {
      const preferences = { ...s.preferences, ...partial };
      void persistSafely(preferences);
      return { preferences };
    });
  },

  reset: () => {
    const preferences = { ...DEFAULT_PREFERENCES };
    set({ preferences });
    void persistSafely(preferences);
  },

  addSession: (day, type, time) => {
    set((s) => {
      const preferences = {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: [
            ...s.preferences.schedule[day],
            { id: genId(), type, time: time ?? '', enabled: true },
          ],
        },
      };
      void persistSafely(preferences);
      return { preferences };
    });
  },

  removeSession: (day, sessionId) => {
    set((s) => {
      const preferences = {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: s.preferences.schedule[day].filter((ss) => ss.id !== sessionId),
        },
      };
      void persistSafely(preferences);
      return { preferences };
    });
  },

  toggleSession: (day, sessionId) => {
    set((s) => {
      const preferences = {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: s.preferences.schedule[day].map((ss) =>
            ss.id === sessionId ? { ...ss, enabled: !ss.enabled } : ss,
          ),
        },
      };
      void persistSafely(preferences);
      return { preferences };
    });
  },

  updateSession: (day, sessionId, updates) => {
    set((s) => {
      const preferences = {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: s.preferences.schedule[day].map((ss) =>
            ss.id === sessionId ? { ...ss, ...updates } : ss,
          ),
        },
      };
      void persistSafely(preferences);
      return { preferences };
    });
  },
}));
