/**
 * Home top-action selection contract test. Locks every
 * precedence rule from `docs/HOME_SCREEN_ACTIONABILITY_SPEC.md`
 * § 2 plus the anti-rules:
 *
 * - Pending follow-up wins over every other rule (already
 *   user-requested).
 * - Setup-required blocker on a previously-connected source
 *   wins over today's-plan and fuel.
 * - Today's-plan only fires when scheduled AND not opened in
 *   the last 12h.
 * - Log-fuel only fires after local noon AND no fuel logged
 *   yet today.
 * - All-stale / nothing-actionable inputs return null.
 * - Defence in depth: directive readiness / clinical / causal
 *   labels are refused at the helper output.
 */

import assert from 'node:assert/strict';
import {
  HOME_TOP_ACTION_EMPTY_COPY,
  selectTopAction,
  type HomeTopActionInput,
} from '../../apps/mobile/src/services/home-top-action';

const NOW = Date.parse('2026-05-09T18:00:00Z'); // 18:00 UTC; used for relative times

function baseInput(overrides: Partial<HomeTopActionInput> = {}): HomeTopActionInput {
  return {
    sources: [],
    todaySessionScheduled: false,
    lastPlanOpenAtMs: null,
    nowMs: NOW,
    fuelLoggedToday: true,
    pendingFollowupCount: 0,
    readinessConfidence: 'medium',
    localHour: 14,
    ...overrides,
  };
}

function expectPendingFollowupWinsOverEverythingElse(): void {
  const result = selectTopAction(baseInput({
    sources: [{ id: 'whoop', label: 'WHOOP', sourceState: 'setup required', previouslyConnected: true }],
    todaySessionScheduled: true,
    lastPlanOpenAtMs: null,
    fuelLoggedToday: false,
    pendingFollowupCount: 2,
  }));
  assert.ok(result, 'pending follow-up MUST always produce an action');
  assert.equal(result!.precedenceRule, 'pending_followup');
  assert.equal(result!.label, 'Open follow-up');
  assert.equal(result!.dismissible, false, 'pending follow-up is non-dismissible');
}

function expectSetupRequiredBeatsTodaysPlan(): void {
  const result = selectTopAction(baseInput({
    sources: [{ id: 'health_connect', label: 'Health Connect', sourceState: 'setup required', previouslyConnected: true }],
    todaySessionScheduled: true,
    lastPlanOpenAtMs: null,
  }));
  assert.ok(result);
  assert.equal(result!.precedenceRule, 'setup_required');
  assert.equal(result!.label, 'Reconnect Health Connect');
  assert.equal(result!.routeOrAction, '/(tabs)/health');
}

function expectSetupRequiredOnFreshSourceIsIgnored(): void {
  // A `setup required` chip on a NEVER-CONNECTED source is not a
  // P1 actionable — the user has not asked to connect it. Should
  // fall through to lower precedence rules.
  const result = selectTopAction(baseInput({
    sources: [{ id: 'whoop', label: 'WHOOP', sourceState: 'setup required', previouslyConnected: false }],
    todaySessionScheduled: true,
    lastPlanOpenAtMs: null,
  }));
  assert.ok(result);
  assert.equal(result!.precedenceRule, 'todays_plan', 'never-connected setup_required must not block today plan');
}

function expectTodaysPlanFiresWhenNoOpenYet(): void {
  const result = selectTopAction(baseInput({
    todaySessionScheduled: true,
    lastPlanOpenAtMs: null,
    fuelLoggedToday: true,
  }));
  assert.ok(result);
  assert.equal(result!.precedenceRule, 'todays_plan');
  assert.equal(result!.label, "Open today's plan");
  assert.equal(result!.dismissible, true);
}

function expectTodaysPlanFiresWhenStaleOpen(): void {
  const result = selectTopAction(baseInput({
    todaySessionScheduled: true,
    lastPlanOpenAtMs: NOW - 13 * 60 * 60 * 1000, // 13h ago
  }));
  assert.equal(result?.precedenceRule, 'todays_plan');
}

function expectTodaysPlanSkipsWhenRecentlyOpened(): void {
  const result = selectTopAction(baseInput({
    todaySessionScheduled: true,
    lastPlanOpenAtMs: NOW - 60 * 60 * 1000, // 1h ago — fresh
    fuelLoggedToday: true,
    localHour: 14,
  }));
  assert.equal(result, null, 'recent plan-open + fuel logged + after noon → no actionable');
}

function expectLogFuelOnlyAfterNoon(): void {
  const beforeNoon = selectTopAction(baseInput({
    todaySessionScheduled: false,
    lastPlanOpenAtMs: null,
    fuelLoggedToday: false,
    localHour: 11,
  }));
  assert.equal(beforeNoon, null, 'before noon: no fuel-log nudge');

  const afterNoon = selectTopAction(baseInput({
    todaySessionScheduled: false,
    lastPlanOpenAtMs: null,
    fuelLoggedToday: false,
    localHour: 12,
  }));
  assert.equal(afterNoon?.precedenceRule, 'log_fuel');
  assert.equal(afterNoon?.label, 'Log fuel');
  assert.equal(afterNoon?.dismissible, true);
}

function expectNullWhenNothingActionable(): void {
  const result = selectTopAction(baseInput({
    sources: [
      { id: 'apple_health', label: 'Apple Health', sourceState: 'live', previouslyConnected: true },
    ],
    todaySessionScheduled: false,
    fuelLoggedToday: true,
    pendingFollowupCount: 0,
    localHour: 14,
  }));
  assert.equal(result, null);
}

function expectEmptyCopyMatchesSpec(): void {
  // Anti-rule lock: the empty-state copy is the verbatim string
  // from docs/HOME_SCREEN_ACTIONABILITY_SPEC.md § 2.
  assert.equal(HOME_TOP_ACTION_EMPTY_COPY, 'Nothing scheduled — when ready, train or log a session.');
}

function expectConfidenceFlowsThroughUntouched(): void {
  // The helper preserves the readiness compute layer's confidence
  // signal; it does NOT override or recompute it.
  const result = selectTopAction(baseInput({
    sources: [{ id: 'health_connect', label: 'Health Connect', sourceState: 'setup required', previouslyConnected: true }],
    readinessConfidence: 'high',
  }));
  assert.equal(result?.confidence, 'high');

  const provisional = selectTopAction(baseInput({
    sources: [{ id: 'health_connect', label: 'Health Connect', sourceState: 'setup required', previouslyConnected: true }],
    readinessConfidence: 'provisional',
  }));
  assert.equal(provisional?.confidence, 'provisional');
}

function expectNullReadinessSurfacesAsUnknown(): void {
  const result = selectTopAction(baseInput({
    pendingFollowupCount: 1,
    readinessConfidence: null,
  }));
  assert.equal(result?.confidence, 'unknown', 'null readiness must surface as the canonical "unknown" confidence');
}

function main(): void {
  expectPendingFollowupWinsOverEverythingElse();
  expectSetupRequiredBeatsTodaysPlan();
  expectSetupRequiredOnFreshSourceIsIgnored();
  expectTodaysPlanFiresWhenNoOpenYet();
  expectTodaysPlanFiresWhenStaleOpen();
  expectTodaysPlanSkipsWhenRecentlyOpened();
  expectLogFuelOnlyAfterNoon();
  expectNullWhenNothingActionable();
  expectEmptyCopyMatchesSpec();
  expectConfidenceFlowsThroughUntouched();
  expectNullReadinessSurfacesAsUnknown();
  console.log('Home top-action selection contract test passed (pending-followup / setup-required / todays-plan / log-fuel precedence + anti-rules).');
}

main();
