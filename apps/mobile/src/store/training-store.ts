/**
 * Training session store — manages manually logged grappling sessions.
 * Sessions are stored locally and trigger health pipeline recomputation.
 */
import { create } from 'zustand';
import type { TrainingSession, TrainingSessionInput } from '@lauburu/shared';

interface TrainingState {
  sessions: TrainingSession[];

  addSession: (input: TrainingSessionInput) => TrainingSession;
  editSession: (id: string, input: Partial<TrainingSessionInput>) => void;
  removeSession: (id: string) => void;
  getSessionsForRange: (startDate: string, endDate: string) => TrainingSession[];
}

function generateId(): string {
  return `ts-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useTrainingStore = create<TrainingState>((set, get) => ({
  sessions: [],

  addSession: (input) => {
    const session: TrainingSession = {
      id: generateId(),
      created_at: new Date().toISOString(),
      date: input.date,
      type: input.type,
      intensity: input.intensity,
      duration_min: input.duration_min,
      rounds: input.rounds,
      rpe: input.rpe,
      tags: input.tags ?? [],
      notes: input.notes ?? '',
      conditioning: input.conditioning,
      persisted: false,
    };
    set((state) => ({ sessions: [...state.sessions, session] }));
    return session;
  },

  editSession: (id, input) => {
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === id
          ? {
              ...s,
              ...input,
              tags: input.tags ?? s.tags,
              notes: input.notes ?? s.notes,
            }
          : s,
      ),
    }));
  },

  removeSession: (id) => {
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
    }));
  },

  getSessionsForRange: (startDate, endDate) => {
    return get().sessions.filter(
      (s) => s.date >= startDate && s.date <= endDate,
    );
  },
}));
