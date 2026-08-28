import type { TimerConfig } from '../store/timer-store';

export type TimerPlanPhase = 'work' | 'rest' | 'running';

export interface TimerPlanStep {
  phase: TimerPlanPhase;
  round: number;
  duration_s: number;
  starts_at_s: number;
  ends_at_s: number;
}

export interface TimerPlanSummary {
  mode: TimerConfig['mode'];
  total_duration_s: number;
  total_rounds: number;
  steps: TimerPlanStep[];
}

function positiveInt(value: number | undefined, fallback: number): number {
  if (Number.isFinite(value) && value != null && value > 0) {
    return Math.floor(value);
  }
  return fallback;
}

/**
 * Build the deterministic phase plan for the live timer.
 *
 * Pure helper used by tests and coaching surfaces so interval duration,
 * round count, and rest omission stay consistent with timer-store.tick().
 */
export function buildTimerPlan(config: TimerConfig): TimerPlanSummary {
  if (config.mode === 'stopwatch') {
    return { mode: 'stopwatch', total_duration_s: 0, total_rounds: 0, steps: [] };
  }

  if (config.mode === 'duration') {
    const total = positiveInt(config.total_s, 0);
    return {
      mode: 'duration',
      total_duration_s: total,
      total_rounds: total > 0 ? 1 : 0,
      steps: total > 0
        ? [{ phase: 'running', round: 1, duration_s: total, starts_at_s: 0, ends_at_s: total }]
        : [],
    };
  }

  const rounds = positiveInt(config.rounds, 1);
  const work = positiveInt(config.work_s, 30);
  const rest = positiveInt(config.rest_s, 0);
  const steps: TimerPlanStep[] = [];
  let cursor = 0;

  for (let round = 1; round <= rounds; round += 1) {
    steps.push({
      phase: 'work',
      round,
      duration_s: work,
      starts_at_s: cursor,
      ends_at_s: cursor + work,
    });
    cursor += work;

    if (rest > 0 && round < rounds) {
      steps.push({
        phase: 'rest',
        round,
        duration_s: rest,
        starts_at_s: cursor,
        ends_at_s: cursor + rest,
      });
      cursor += rest;
    }
  }

  return {
    mode: 'interval',
    total_duration_s: cursor,
    total_rounds: rounds,
    steps,
  };
}
