/**
 * HIIT workout record store — persists full HIITWorkoutRecord objects
 * with set-by-set metrics for progress tracking and Coach consumption.
 *
 * Distinct from hiit-protocols-store which stores named protocol
 * templates. This store holds the actual session data.
 *
 * Persistence: secureStorage, key `hiit_workouts_v1`.
 * Rolling window: MAX_WORKOUTS records, newest first.
 * Auto-syncs to AI backend on save (fire-and-forget).
 */
import { create } from 'zustand';
import type { HIITWorkoutRecord, HIITProgressComparison } from '@lauburu/shared';
import { compareHiitWorkouts } from '@lauburu/shared';
import { secureStorage } from './secure-storage';
import { syncHIITWorkoutToAiBackend } from '../services/ai-hiit-sync';
import { useAuthStore } from './auth-store';
import { useTrainingStore } from './training-store';

/**
 * Map a HIITWorkoutRecord to a synthetic TrainingSession so the
 * existing training-store → health-store recompute chain picks it up.
 * Without this bridge, HIIT workouts wouldn't appear in Recent Days
 * or trends and Coach wouldn't know about them until Apple Health
 * scored a matching workout (which can lag). Idempotent via the
 * preset_id field keyed to the HIIT workout id.
 */
function mirrorHiitToTrainingStore(workout: HIITWorkoutRecord): void {
  try {
    const addSession = useTrainingStore.getState().addSession;
    if (typeof addSession !== 'function') return;
    // Intensity heuristic: use workout avgHr/peakHr if available,
    // otherwise infer from duration + format. Default to 'hard' since
    // these are HIIT templates (30/15, 4x4, etc.).
    const intensity: 'light' | 'moderate' | 'hard' = workout.avgHr != null && workout.avgHr < 130 ? 'moderate' : 'hard';
    const durationMin = Math.max(1, Math.round((workout.totalDurationSeconds ?? 0) / 60));
    addSession({
      date: workout.date,
      type: 'conditioning',
      intensity,
      duration_min: durationMin,
      rounds: workout.totalSets,
      notes: `HIIT · ${workout.protocolFormat ?? 'custom'}${workout.machineType ? ` · ${workout.machineType}` : ''}`,
      tags: ['hiit', workout.protocolFormat ?? 'custom', workout.machineType ?? ''].filter(Boolean),
      preset_id: `hiit:${workout.id}`,
    });
  } catch {
    // Non-fatal — the HIIT store itself still has the workout; the
    // bridge is purely so Recent Days / Coach see it instantly.
  }
}

const STORAGE_KEY = 'hiit_workouts_v1';
// Bumped from 30 → 90 so the on-device Coach has a quarter of session
// history to reason over (trends, PR cadence, comparable workouts).
// Backend already retains the full archive via ai-hiit-sync.
const MAX_WORKOUTS = 90;

async function persistSafely(workouts: HIITWorkoutRecord[]): Promise<void> {
  try {
    if (!workouts || workouts.length === 0) {
      await secureStorage.removeItem(STORAGE_KEY);
      return;
    }
    await secureStorage.setItem(STORAGE_KEY, JSON.stringify(workouts));
  } catch {
    // Intentionally swallowed.
  }
}

interface HIITWorkoutState {
  /** All workout records, newest first. */
  workouts: HIITWorkoutRecord[];
  hydrated: boolean;

  /** Load from secureStorage. */
  hydrate: () => Promise<void>;

  /** Save a new workout record. Returns progress comparison if a previous
   *  session with the same template exists. */
  saveWorkout: (workout: HIITWorkoutRecord) => HIITProgressComparison | null;

  /** Get the most recent N workouts. */
  recent: (n?: number) => HIITWorkoutRecord[];

  /** Get workouts for a specific template (for progress tracking). */
  forTemplate: (templateId: string) => HIITWorkoutRecord[];

  /** Get the last workout for a template (for comparison). */
  lastForTemplate: (templateId: string) => HIITWorkoutRecord | null;

  /** Delete a workout by id. */
  removeWorkout: (id: string) => void;

  /** Clear all workouts. */
  clearAll: () => void;
}

export const useHIITWorkoutStore = create<HIITWorkoutState>((set, get) => ({
  workouts: [],
  hydrated: false,

  hydrate: async () => {
    try {
      const raw = await secureStorage.getItem(STORAGE_KEY);
      if (!raw) {
        set({ hydrated: true });
        return;
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        await secureStorage.removeItem(STORAGE_KEY);
        set({ hydrated: true });
        return;
      }
      const workouts = parsed
        .filter((w: any) => w && w.id && w.date)
        .slice(0, MAX_WORKOUTS) as HIITWorkoutRecord[];
      // Ensure newest-first ordering.
      workouts.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      set({ workouts, hydrated: true });
    } catch {
      set({ hydrated: true });
    }
  },

  saveWorkout: (workout) => {
    let comparison: HIITProgressComparison | null = null;
    let next: HIITWorkoutRecord[] = [];

    // Find previous session with same template for comparison.
    if (workout.templateId) {
      const prev = get().workouts.find(
        (w) => w.templateId === workout.templateId && w.id !== workout.id,
      );
      if (prev) {
        comparison = compareHiitWorkouts(workout, prev);
      }
    }

    set((state) => {
      // Dedupe by id.
      const filtered = state.workouts.filter((w) => w.id !== workout.id);
      next = [workout, ...filtered].slice(0, MAX_WORKOUTS);
      next.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
      return { workouts: next };
    });
    void persistSafely(next);
    // Mirror into training-store so Recent Days / Coach / Trends see
    // this session immediately — Apple Health workout ingest can lag
    // by minutes after the machine finishes.
    mirrorHiitToTrainingStore(workout);
    // Fire-and-forget sync to AI backend
    const uid = useAuthStore.getState().user?.id;
    if (uid) void syncHIITWorkoutToAiBackend(uid, workout).catch(() => {});
    return comparison;
  },

  recent: (n = 3) => {
    return get().workouts.slice(0, n);
  },

  forTemplate: (templateId) => {
    return get().workouts.filter((w) => w.templateId === templateId);
  },

  lastForTemplate: (templateId) => {
    return get().workouts.find((w) => w.templateId === templateId) ?? null;
  },

  removeWorkout: (id) => {
    let next: HIITWorkoutRecord[] = [];
    set((state) => {
      next = state.workouts.filter((w) => w.id !== id);
      return { workouts: next };
    });
    void persistSafely(next);
  },

  clearAll: () => {
    set({ workouts: [] });
    void persistSafely([]);
  },
}));
