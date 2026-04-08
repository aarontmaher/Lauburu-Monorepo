/**
 * Coaching preferences store — personalization seed.
 * Affects coaching output without requiring model training.
 */
import { create } from 'zustand';
import { DEFAULT_PREFERENCES } from '@lauburu/shared';
import type { CoachingPreferences } from '@lauburu/shared';

interface PreferencesState {
  preferences: CoachingPreferences;
  update: (partial: Partial<CoachingPreferences>) => void;
  reset: () => void;
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
}));
