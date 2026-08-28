/**
 * Suggested metrics — blind-spot-driven list of optional things the
 * athlete could start tracking, gated on whether tracking them would
 * materially improve Coach analysis for *this* user's current data.
 *
 * Rules:
 *   - Never auto-enable. Every suggestion is optional.
 *   - Only surface when the value is clear (missing piece blocks a
 *     class of analysis the user already engages with).
 *   - Low-noise: cap at 3 at a time, ranked by value.
 *   - Include: what to track, why, what it unlocks, effort.
 */

export type SuggestionEffort = 'trivial' | 'light' | 'moderate';

export interface MetricSuggestion {
  id: string;
  title: string;
  why: string;
  unlocks: string;
  effort: SuggestionEffort;
  route?: string; // expo-router path if there's a direct action
}

export interface SuggestedMetricsInputs {
  // Integrations.
  appleHealthConnected: boolean;
  whoopConnected: boolean;
  whoopCsvImported: boolean;

  // Nutrition.
  hasNutritionToday: boolean;
  waterLoggedToday: boolean;
  caloriesLoggedToday: boolean;
  proteinLoggedToday: boolean;

  // Training / sessions.
  sessionsLast7d: number;
  sessionsLast7dWithRpe: number;
  grapplingSessionsLast7d: number;
  grapplingSessionsWithRoundMarkers: number;

  // Body.
  hasWeightLogged: boolean;
}

export function computeSuggestedMetrics(
  inputs: SuggestedMetricsInputs,
): MetricSuggestion[] {
  const out: Array<MetricSuggestion & { rank: number }> = [];

  if (!inputs.appleHealthConnected && !inputs.whoopConnected) {
    out.push({
      id: 'connect_health_source',
      title: 'Connect a health source',
      why: 'Without sleep and HRV, Coach can only guess at recovery.',
      unlocks: 'Recovery-aware training, readiness, sleep trends',
      effort: 'trivial',
      route: '/(tabs)/health',
      rank: 100,
    });
  }

  if (
    inputs.sessionsLast7d >= 2 &&
    inputs.sessionsLast7dWithRpe === 0
  ) {
    out.push({
      id: 'session_rpe',
      title: 'Log RPE on sessions',
      why: 'You\u2019ve trained recently but none of the sessions have RPE. A 1\u201310 rating takes 5 seconds.',
      unlocks: 'Fatigue-aware week planning, honest load comparisons',
      effort: 'trivial',
      rank: 80,
    });
  }

  if (
    inputs.grapplingSessionsLast7d >= 1 &&
    inputs.grapplingSessionsWithRoundMarkers === 0
  ) {
    out.push({
      id: 'grappling_round_markers',
      title: 'Mark rounds during rolling',
      why: 'Round markers let Coach see intensity distribution across a session, not just the average.',
      unlocks: 'Per-round HR recovery, zone time, true hard-round count',
      effort: 'light',
      rank: 70,
    });
  }

  if (inputs.caloriesLoggedToday && !inputs.waterLoggedToday) {
    out.push({
      id: 'hydration',
      title: 'Log water today',
      why: 'You logged calories but not hydration. Under-fueling conclusions depend on both.',
      unlocks: 'Hydration-aware fueling guidance, heat-session flags',
      effort: 'trivial',
      rank: 60,
    });
  }

  if (inputs.caloriesLoggedToday && !inputs.proteinLoggedToday) {
    out.push({
      id: 'protein',
      title: 'Log protein',
      why: 'Calories without protein blocks the most useful nutrition questions.',
      unlocks: 'Protein-per-kg guidance, recovery-aware fueling',
      effort: 'trivial',
      rank: 55,
    });
  }

  if (
    inputs.whoopConnected &&
    !inputs.whoopCsvImported &&
    inputs.sessionsLast7d >= 3
  ) {
    out.push({
      id: 'whoop_csv',
      title: 'Upload a WHOOP export',
      why: 'Direct API gives live cycles. A WHOOP CSV export adds deeper history and richer fields for longer-range analysis.',
      unlocks: 'Multi-month recovery baselines, strain-vs-outcome trends',
      effort: 'light',
      route: '/(tabs)/health',
      rank: 40,
    });
  }

  if (!inputs.hasWeightLogged) {
    out.push({
      id: 'body_weight',
      title: 'Log body weight weekly',
      why: 'Weight is the anchor for protein-per-kg and strength progress.',
      unlocks: 'Protein-per-kg targets, strength-per-kg comparisons',
      effort: 'trivial',
      rank: 30,
    });
  }

  out.sort((a, b) => b.rank - a.rank);
  return out.slice(0, 3).map(({ rank: _rank, ...s }) => s);
}
