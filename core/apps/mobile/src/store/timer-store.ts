/**
 * Live session timer store.
 *
 * Modes:
 * - interval: work/rest cycles (HIIT, intervals, sprint intervals, circuit)
 * - duration: simple countdown (steady state, zone 2, tempo)
 * - stopwatch: count up (weight training, other)
 */
import { create } from 'zustand';
import type { ConditioningSubtype, Modality } from '@lauburu/shared';

export type TimerMode = 'interval' | 'duration' | 'stopwatch';
export type TimerPhase = 'idle' | 'work' | 'rest' | 'running' | 'paused' | 'complete';

export interface TimerConfig {
  mode: TimerMode;
  subtype: ConditioningSubtype;
  modality?: Modality;
  work_s?: number;
  rest_s?: number;
  rounds?: number;
  total_s?: number;
  /**
   * Optional user-provided protocol label, carried through the timer
   * flow so the completion path can auto-update the matching saved
   * HIIT protocol with this session's metrics. Undefined when the
   * user launched the timer without naming the protocol.
   */
  label?: string;
}

interface TimerState {
  config: TimerConfig | null;
  phase: TimerPhase;
  /** Phase before pause (for correct resume) */
  pausedFrom: TimerPhase;
  remaining_s: number;
  currentRound: number;
  elapsed_s: number;

  setup: (config: TimerConfig) => void;
  start: () => void;
  pause: () => void;
  skip: () => void;
  tick: () => void;
  reset: () => void;
}

export const useTimerStore = create<TimerState>((set, get) => ({
  config: null,
  phase: 'idle',
  pausedFrom: 'idle',
  remaining_s: 0,
  currentRound: 0,
  elapsed_s: 0,

  setup: (config) => {
    let remaining = 0;
    if (config.mode === 'interval' && config.work_s) {
      remaining = config.work_s;
    } else if (config.mode === 'duration' && config.total_s) {
      remaining = config.total_s;
    }
    set({
      config,
      phase: 'idle',
      pausedFrom: 'idle',
      remaining_s: remaining,
      currentRound: config.mode === 'interval' ? 1 : 0,
      elapsed_s: 0,
    });
  },

  start: () => {
    const { config, phase, pausedFrom } = get();
    if (!config) return;

    if (phase === 'idle') {
      const initial: TimerPhase =
        config.mode === 'interval' ? 'work' : 'running';
      set({ phase: initial, pausedFrom: 'idle' });
    } else if (phase === 'paused') {
      // Resume to the phase we were in before pause
      set({ phase: pausedFrom });
    }
  },

  pause: () => {
    const { phase } = get();
    if (phase === 'work' || phase === 'rest' || phase === 'running') {
      set({ phase: 'paused', pausedFrom: phase });
    }
  },

  skip: () => {
    const { config, phase, currentRound } = get();
    if (!config || phase === 'idle' || phase === 'complete') return;

    // Resolve actual phase (might be paused)
    const activePhase = phase === 'paused' ? get().pausedFrom : phase;

    if (config.mode === 'interval') {
      const maxRounds = config.rounds ?? 1;
      if (activePhase === 'work') {
        if (config.rest_s && config.rest_s > 0) {
          set({ phase: 'rest', remaining_s: config.rest_s, pausedFrom: 'rest' });
        } else if (currentRound >= maxRounds) {
          set({ phase: 'complete', remaining_s: 0 });
        } else {
          set({ phase: 'work', remaining_s: config.work_s ?? 30, currentRound: currentRound + 1 });
        }
      } else if (activePhase === 'rest') {
        if (currentRound >= maxRounds) {
          set({ phase: 'complete', remaining_s: 0 });
        } else {
          set({ phase: 'work', remaining_s: config.work_s ?? 30, currentRound: currentRound + 1 });
        }
      }
    } else {
      set({ phase: 'complete', remaining_s: 0 });
    }
  },

  tick: () => {
    const { config, phase, remaining_s, currentRound } = get();
    if (!config || phase === 'idle' || phase === 'paused' || phase === 'complete') return;

    const newElapsed = get().elapsed_s + 1;

    if (config.mode === 'stopwatch') {
      set({ elapsed_s: newElapsed });
      return;
    }

    const newRemaining = remaining_s - 1;

    if (newRemaining > 0) {
      set({ remaining_s: newRemaining, elapsed_s: newElapsed });
      return;
    }

    // Hit zero — transition
    if (config.mode === 'duration') {
      set({ phase: 'complete', remaining_s: 0, elapsed_s: newElapsed });
      return;
    }

    // Interval transitions
    const maxRounds = config.rounds ?? 1;
    if (phase === 'work') {
      if (config.rest_s && config.rest_s > 0) {
        set({ phase: 'rest', remaining_s: config.rest_s, elapsed_s: newElapsed });
      } else if (currentRound >= maxRounds) {
        set({ phase: 'complete', remaining_s: 0, elapsed_s: newElapsed });
      } else {
        set({ phase: 'work', remaining_s: config.work_s ?? 30, currentRound: currentRound + 1, elapsed_s: newElapsed });
      }
    } else if (phase === 'rest') {
      if (currentRound >= maxRounds) {
        set({ phase: 'complete', remaining_s: 0, elapsed_s: newElapsed });
      } else {
        set({ phase: 'work', remaining_s: config.work_s ?? 30, currentRound: currentRound + 1, elapsed_s: newElapsed });
      }
    }
  },

  reset: () => {
    set({
      config: null,
      phase: 'idle',
      pausedFrom: 'idle',
      remaining_s: 0,
      currentRound: 0,
      elapsed_s: 0,
    });
  },
}));
