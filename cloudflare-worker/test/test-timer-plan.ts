/**
 * Timer plan contract test.
 *
 * Locks a pure representation of the live timer's phases so App
 * Functionality work can safely reuse it for Coach context and audit
 * evidence without changing timer-store runtime behaviour.
 */

import assert from 'node:assert/strict';
import { buildTimerPlan } from '../../apps/mobile/src/services/timer-plan';

function expectIntervalWithRestBetweenRoundsOnly(): void {
  const plan = buildTimerPlan({
    mode: 'interval',
    subtype: 'hiit',
    work_s: 30,
    rest_s: 15,
    rounds: 3,
  });

  assert.equal(plan.mode, 'interval');
  assert.equal(plan.total_rounds, 3);
  assert.equal(plan.total_duration_s, 120);
  assert.deepEqual(
    plan.steps.map((s) => `${s.phase}:${s.round}:${s.starts_at_s}-${s.ends_at_s}`),
    [
      'work:1:0-30',
      'rest:1:30-45',
      'work:2:45-75',
      'rest:2:75-90',
      'work:3:90-120',
    ],
    'interval plans must not append rest after the final work round',
  );
}

function expectZeroRestOmitsRestSteps(): void {
  const plan = buildTimerPlan({
    mode: 'interval',
    subtype: 'sprint_intervals',
    work_s: 20,
    rest_s: 0,
    rounds: 4,
  });

  assert.equal(plan.total_duration_s, 80);
  assert.equal(plan.steps.length, 4);
  assert.ok(plan.steps.every((s) => s.phase === 'work'));
}

function expectDefaultsMatchTimerStore(): void {
  const plan = buildTimerPlan({
    mode: 'interval',
    subtype: 'circuit',
  });

  assert.equal(plan.total_rounds, 1);
  assert.equal(plan.total_duration_s, 30);
  assert.deepEqual(plan.steps, [
    { phase: 'work', round: 1, duration_s: 30, starts_at_s: 0, ends_at_s: 30 },
  ]);
}

function expectDurationAndStopwatchModes(): void {
  const duration = buildTimerPlan({
    mode: 'duration',
    subtype: 'zone2',
    total_s: 1800,
  });
  assert.equal(duration.total_duration_s, 1800);
  assert.equal(duration.total_rounds, 1);
  assert.deepEqual(duration.steps, [
    { phase: 'running', round: 1, duration_s: 1800, starts_at_s: 0, ends_at_s: 1800 },
  ]);

  const stopwatch = buildTimerPlan({
    mode: 'stopwatch',
    subtype: 'weight_training',
  });
  assert.equal(stopwatch.total_duration_s, 0);
  assert.equal(stopwatch.total_rounds, 0);
  assert.deepEqual(stopwatch.steps, []);
}

function main(): void {
  expectIntervalWithRestBetweenRoundsOnly();
  expectZeroRestOmitsRestSteps();
  expectDefaultsMatchTimerStore();
  expectDurationAndStopwatchModes();
  console.log('Timer plan contract test passed (interval/rest/defaults/duration/stopwatch).');
}

main();
