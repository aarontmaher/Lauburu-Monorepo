/**
 * Coaching preferences + weekly schedule store.
 */
import { create } from 'zustand';
import { DEFAULT_PREFERENCES } from '@lauburu/shared';
import type { CoachingPreferences, DayOfWeek, PlannedSession, ScheduleSessionType } from '@lauburu/shared';

function genId(): string {
  return `ps-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

interface PreferencesState {
  preferences: CoachingPreferences;
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

  update: (partial) => {
    set((s) => ({
      preferences: { ...s.preferences, ...partial },
    }));
  },

  reset: () => {
    set({ preferences: { ...DEFAULT_PREFERENCES } });
  },

  addSession: (day, type, time) => {
    set((s) => ({
      preferences: {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: [
            ...s.preferences.schedule[day],
            { id: genId(), type, time: time ?? '', enabled: true },
          ],
        },
      },
    }));
  },

  removeSession: (day, sessionId) => {
    set((s) => ({
      preferences: {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: s.preferences.schedule[day].filter((ss) => ss.id !== sessionId),
        },
      },
    }));
  },

  toggleSession: (day, sessionId) => {
    set((s) => ({
      preferences: {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: s.preferences.schedule[day].map((ss) =>
            ss.id === sessionId ? { ...ss, enabled: !ss.enabled } : ss,
          ),
        },
      },
    }));
  },

  updateSession: (day, sessionId, updates) => {
    set((s) => ({
      preferences: {
        ...s.preferences,
        schedule: {
          ...s.preferences.schedule,
          [day]: s.preferences.schedule[day].map((ss) =>
            ss.id === sessionId ? { ...ss, ...updates } : ss,
          ),
        },
      },
    }));
  },
}));
