/**
 * Live session timer store.
 *
 * Modes:
 * - interval: work/rest cycles (HIIT, intervals, sprint intervals, circuit)
 * - duration: simple countdown (steady state, zone 2, tempo)
 * - stopwatch: count up (weight training, other)
 *
 * Future: bike-connected mode adds live metrics alongside the timer.
 */
import { create } from 'zustand';
import type { IntervalDetail, Modality, ConditioningSubtype } from '@lauburu/shared';

export type TimerMode = 'interval' | 'duration' | 'stopwatch';
export type TimerPhase = 'idle' | 'work' | 'rest' | 'running' | 'paused' | 'complete';

export interface TimerConfig {
  mode: TimerMode;
  subtype: ConditioningSubtype;
  modality?: Modality;
  /** Interval mode */
  work_s?: number;
  rest_s?: number;
  rounds?: number;
  /** Duration mode */
  total_s?: number;
}

interface TimerState {
  config: TimerConfig | null;
  phase: TimerPhase;
  /** Seconds remaining in current interval/phase */
  remaining_s: number;
  /** Current round (1-indexed) */
  currentRound: number;
  /** Total elapsed seconds */
  elapsed_s: number;
  /** Timestamp when timer was last started/resumed */
  startedAt: number | null;

  /** Configure and prepare timer */
  setup: (config: TimerConfig) => void;
  /** Start or resume */
  start: () => void;
  /** Pause */
  pause: () => void;
  /** Skip to next interval/round */
  skip: () => void;
  /** Tick — called every second by the UI interval */
  tick: () => void;
  /** Reset to idle */
  reset: () => void;
}

export const useTimerStore = create<TimerState>((set, get) => ({
  config: null,
  phase: 'idle',
  remaining_s: 0,
  currentRound: 0,
  elapsed_s: 0,
  startedAt: null,

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
      remaining_s: remaining,
      currentRound: config.mode === 'interval' ? 1 : 0,
      elapsed_s: 0,
      startedAt: null,
    });
  },

  start: () => {
    const { config, phase } = get();
    if (!config) return;

    if (phase === 'idle') {
      // First start
      const initialPhase: TimerPhase =
        config.mode === 'interval' ? 'work' :
        config.mode === 'duration' ? 'running' : 'running';
      set({ phase: initialPhase, startedAt: Date.now() });
    } else if (phase === 'paused') {
      set({ phase: get().remaining_s > 0 ? (config.mode === 'interval' ? 'work' : 'running') : 'complete', startedAt: Date.now() });
    }
  },

  pause: () => {
    set({ phase: 'paused', startedAt: null });
  },

  skip: () => {
    const { config, phase, currentRound } = get();
    if (!config || phase === 'idle' || phase === 'complete') return;

    if (config.mode === 'interval') {
      const maxRounds = config.rounds ?? 1;
      if (phase === 'work') {
        // Skip to rest
        if (config.rest_s && config.rest_s > 0) {
          set({ phase: 'rest', remaining_s: config.rest_s });
        } else {
          // No rest — next round or complete
          if (currentRound >= maxRounds) {
            set({ phase: 'complete', remaining_s: 0 });
          } else {
            set({
              phase: 'work',
              remaining_s: config.work_s ?? 30,
              currentRound: currentRound + 1,
            });
          }
        }
      } else if (phase === 'rest') {
        // Skip to next round
        if (currentRound >= maxRounds) {
          set({ phase: 'complete', remaining_s: 0 });
        } else {
          set({
            phase: 'work',
            remaining_s: config.work_s ?? 30,
            currentRound: currentRound + 1,
          });
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

    // Countdown modes
    const newRemaining = remaining_s - 1;

    if (newRemaining > 0) {
      set({ remaining_s: newRemaining, elapsed_s: newElapsed });
      return;
    }

    // Timer hit zero
    if (config.mode === 'duration') {
      set({ phase: 'complete', remaining_s: 0, elapsed_s: newElapsed });
      return;
    }

    // Interval mode — transition
    const maxRounds = config.rounds ?? 1;
    if (phase === 'work') {
      if (config.rest_s && config.rest_s > 0) {
        set({ phase: 'rest', remaining_s: config.rest_s, elapsed_s: newElapsed });
      } else if (currentRound >= maxRounds) {
        set({ phase: 'complete', remaining_s: 0, elapsed_s: newElapsed });
      } else {
        set({
          phase: 'work',
          remaining_s: config.work_s ?? 30,
          currentRound: currentRound + 1,
          elapsed_s: newElapsed,
        });
      }
    } else if (phase === 'rest') {
      if (currentRound >= maxRounds) {
        set({ phase: 'complete', remaining_s: 0, elapsed_s: newElapsed });
      } else {
        set({
          phase: 'work',
          remaining_s: config.work_s ?? 30,
          currentRound: currentRound + 1,
          elapsed_s: newElapsed,
        });
      }
    }
  },

  reset: () => {
    set({
      config: null,
      phase: 'idle',
      remaining_s: 0,
      currentRound: 0,
      elapsed_s: 0,
      startedAt: null,
    });
  },
}));
