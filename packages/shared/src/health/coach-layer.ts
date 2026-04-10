/**
 * Daily coaching brief — a compact, read-only synthesis of:
 *   - today's WHOOP day (primary readiness source when present)
 *   - today's plan from the user's weekly schedule
 *   - recent training sessions (for load context)
 *   - the existing insights engine output (fallback readiness source)
 *
 * This module is deliberately light. It does NOT replace the full
 * `generateCoaching()` pipeline in coaching.ts (which runs on Apple Health
 * derived features) — it sits alongside it as a small, composable "what
 * should I do right now" layer that can honor WHOOP even when HealthKit
 * is empty.
 *
 * Pure function. No I/O, no mutation, no store imports. Accepts any
 * structurally-compatible WHOOP snapshot so the mobile whoop-store's
 * WhoopDay type satisfies it without conversion.
 */
import type { TrainingSession, SessionIntensity } from '../types/training';
import type { PlannedSession } from '../types/preferences';
import {
  SCHEDULE_SESSION_LABELS,
  GRAPPLING_SCHEDULE_SUBTYPE_LABELS,
} from '../types/preferences';
import type { NutritionRecord, NutritionTargets } from '../types/nutrition';
import type { ReadinessLevel, TrainingInsight } from './insights';

/**
 * Minimal WHOOP snapshot shape — the mobile store's WhoopDay matches
 * this structurally without any cast or conversion.
 */
export interface WhoopSnapshot {
  date: string;
  recovery_score: number | null;
  hrv_ms: number | null;
  resting_hr: number | null;
  sleep_hours: number | null;
  daily_strain: number | null;
  /** Number of workouts the backend has for today so far. */
  workout_count: number;
  /** Upstream freshness timestamp. Null if unknown. */
  source_updated_at: string | null;
}

/**
 * Polar snapshot — first-slice scaffolding for a future Polar integration.
 *
 * Status as of 2026-04-10: NO live ingestion path. Polar data today flows
 * through Apple HealthKit / Health Connect when the user has the Polar app
 * set to write there, which means it arrives as generic HealthKit metrics
 * with no Polar-specific richness. This type reserves the shape that a
 * future direct Polar path (Polar AccessLink API, Polar Flow web sync, or
 * a Polar sensor BLE path) will target.
 *
 * Structurally mirrors WhoopSnapshot so downstream consumers can choose
 * "whoopDay ?? polarDay" as a readiness source fallback without knowing
 * which vendor provided the numbers.
 */
export interface PolarSnapshot {
  date: string;
  /** Polar's "Recovery Pro" score 0-100 when available. */
  recovery_score: number | null;
  /** Orthostatic HRV (ms) or overnight RMSSD. */
  hrv_ms: number | null;
  /** Overnight resting heart rate (bpm). */
  resting_hr: number | null;
  /** Total sleep in hours (Polar Sleep Plus Stages). */
  sleep_hours: number | null;
  /** Polar Nightly Recharge status ("very good" → 5, "very poor" → 1). */
  nightly_recharge?: number | null;
  /** Count of workouts Polar has uploaded for today. */
  workout_count: number;
  /** Last upstream update timestamp. */
  source_updated_at: string | null;
}

/** Where the readiness assessment ultimately came from. */
export type PrimaryReadinessSource = 'whoop' | 'insights' | 'none';

/** High-level training modes the brief can recommend. */
export type CoachedMode = 'grappling' | 'hiit' | 'zone2' | 'weights' | 'rest';

/**
 * Coaching-level interpretation of today's accumulated load.
 *
 * Explicitly NOT a "strain / 21" progress bar — raw WHOOP strain is a
 * scale metric, not a personal target. We interpret it against the
 * user's current readiness to describe whether there's room for more.
 *
 * 'low'        — very little load accumulated so far
 * 'building'   — a normal amount, room for more
 * 'at_target'  — an appropriate amount for today's readiness
 * 'over'       — already past what today's readiness supports
 * 'unknown'    — no strain signal yet
 */
export type LoadBand = 'low' | 'building' | 'at_target' | 'over' | 'unknown';

export interface DailyCoachingBrief {
  /** One-line headline for the card header (e.g. "67% recovered — push hard today"). */
  headline: string;

  /** Overall readiness assessment. */
  readiness: ReadinessLevel;

  /** Where the readiness value came from. */
  primary_source: PrimaryReadinessSource;

  /** Recommended intensity for any session logged today. */
  suggested_intensity: SessionIntensity;

  /**
   * Suggested training modes in order of preference.
   * An empty array means "rest" — no training recommended.
   */
  suggested_modes: CoachedMode[];

  /**
   * Short rendered summary of today's plan from the weekly schedule.
   * Null if there is no plan for today (rest day).
   */
  plan_hint: string | null;

  /**
   * Number of enabled planned sessions for today. Useful for the UI
   * to decide whether to show a plan block at all.
   */
  planned_count: number;

  /**
   * Up to 3 plain-English reasons explaining the recommendation.
   * Never longer — keeps the card readable.
   */
  reasons: string[];

  /** True if WHOOP has today's recovery but zero workouts logged so far. */
  whoop_workouts_missing_today: boolean;

  /**
   * Coaching interpretation of today's accumulated load. Derived from
   * WHOOP day strain + current readiness — NOT a raw `/21` progress bar.
   * UI should render this as words ("building", "at target", "over") so
   * the user thinks about load as personal, not as a WHOOP scale target.
   */
  load_band: LoadBand;
  /** One-line load interpretation for the card ("Room for more today"). */
  load_line: string;
}

// ---------------------------------------------------------------------------
// Readiness derivation
// ---------------------------------------------------------------------------

function whoopScoreToReadiness(score: number | null): ReadinessLevel {
  if (score == null) return 'grey';
  if (score >= 67) return 'green';
  if (score >= 34) return 'yellow';
  return 'red';
}

function readinessToIntensity(r: ReadinessLevel): SessionIntensity {
  if (r === 'green') return 'hard';
  if (r === 'yellow') return 'moderate';
  // red + grey default conservative
  return 'light';
}

function readinessToModes(r: ReadinessLevel): CoachedMode[] {
  if (r === 'green') return ['grappling', 'hiit', 'weights', 'zone2'];
  if (r === 'yellow') return ['grappling', 'zone2', 'weights'];
  if (r === 'red') return ['zone2', 'rest'];
  // grey — cautious default
  return ['grappling', 'zone2'];
}

// ---------------------------------------------------------------------------
// Load awareness — look at the last 3 days for hard sessions
// ---------------------------------------------------------------------------

function countHardSessionsInLastDays(
  sessions: TrainingSession[],
  todayIsoDate: string,
  daysBack: number,
): number {
  const today = new Date(todayIsoDate + 'T00:00:00');
  const floor = new Date(today);
  floor.setDate(floor.getDate() - daysBack);
  const floorIso = floor.toISOString().slice(0, 10);
  return sessions.filter(
    (s) => s.date >= floorIso && s.date <= todayIsoDate && s.intensity === 'hard',
  ).length;
}

// ---------------------------------------------------------------------------
// Nutrition reason — concise, time-aware, target-gated
// ---------------------------------------------------------------------------

/**
 * Build at most one concise nutrition-aware reason for the brief.
 *
 * Rules fire top-down; the first match wins. All rules require the
 * corresponding target to be set — we never fake precision by guessing
 * a target. The "time of day" rules are deliberately conservative
 * (late afternoon onwards) so the brief doesn't nag at 9am when a
 * light breakfast is fine.
 *
 * Rule priority (high → low):
 *   1. under-fuelling at high load (strong signal, most actionable)
 *   2. multi-day trend: calories chronically low
 *   3. multi-day trend: protein chronically behind
 *   4. calories very low for the time of day (fuel before training)
 *   5. protein behind target (simple macro shortfall)
 *   6. nothing logged yet after mid-afternoon (log-gap nag)
 */
function buildNutritionReason(inputs: {
  nutritionToday: NutritionRecord | null | undefined;
  nutritionTargets: NutritionTargets | null | undefined;
  nutritionHistory: NutritionRecord[] | null | undefined;
  readiness: ReadinessLevel;
  recentHard: number;
  currentHour: number;
}): string | null {
  const {
    nutritionToday,
    nutritionTargets,
    nutritionHistory,
    readiness,
    recentHard,
    currentHour,
  } = inputs;
  const cals = nutritionToday?.calories_kcal ?? null;
  const protein = nutritionToday?.protein_g ?? null;
  const calTarget = nutritionTargets?.calories_kcal ?? null;
  const proteinTarget = nutritionTargets?.protein_g ?? null;

  const calsPct = cals != null && calTarget ? cals / calTarget : null;
  const proteinPct =
    protein != null && proteinTarget ? protein / proteinTarget : null;

  // Rule 1 — under-fuelling + high training load. Only fires when we have
  // real numbers AND the user's readiness is already yellow/red OR there
  // have been multiple hard sessions recently. Highest-priority signal.
  if (
    calsPct != null &&
    calsPct < 0.5 &&
    (recentHard >= 2 || readiness === 'yellow' || readiness === 'red') &&
    currentHour >= 14
  ) {
    return 'Training load rising but intake is still low';
  }

  // Multi-day trend rules — only fire when we have at least 3 history
  // entries AND a target for the field being judged. Trend rules are
  // ranked above single-day rules (except rule 1) because a pattern
  // is more actionable than a one-off miss. Each rule requires the
  // most-recent N history days all fail the threshold.
  const hasTrend =
    !!nutritionHistory &&
    nutritionHistory.length >= 3 &&
    nutritionTargets != null;

  if (hasTrend) {
    // Rule 2 — calories chronically low. Last 3 history days all under
    // 70% of target (conservative threshold for a trend call) AND
    // calories target exists.
    if (calTarget != null) {
      const recent3 = nutritionHistory!.slice(0, 3);
      const allLow = recent3.every((d) => {
        if (d.calories_kcal == null) return false;
        return d.calories_kcal / calTarget < 0.7;
      });
      if (allLow) {
        return 'Calories behind target for 3 days running — consider a bigger day';
      }
    }

    // Rule 3 — protein chronically behind. Last 3 history days all under
    // 80% of target.
    if (proteinTarget != null) {
      const recent3 = nutritionHistory!.slice(0, 3);
      const allLow = recent3.every((d) => {
        if (d.protein_g == null) return false;
        return d.protein_g / proteinTarget < 0.8;
      });
      if (allLow) {
        return 'Protein behind target for 3 days running — add a protein-dense meal';
      }
    }
  }

  // Rule 4 — calories very low for the time of day. Fires after 14:00
  // local when calories are below 40% of target. Simple fuel nudge.
  if (calsPct != null && calsPct < 0.4 && currentHour >= 14) {
    return 'Fuel is still low for today — eat before training';
  }

  // Rule 5 — protein behind target. Fires any time of day once we're
  // past 10am if protein is under 80%.
  if (proteinPct != null && proteinPct < 0.8 && currentHour >= 10) {
    return 'Protein is behind target — add another meal or shake';
  }

  // Rule 6 — nothing logged yet after mid-afternoon. Only when the user
  // has targets set (opted into this level of coaching) but hasn't
  // entered anything for today.
  const hasAnyTarget =
    nutritionTargets != null &&
    (nutritionTargets.calories_kcal != null ||
      nutritionTargets.protein_g != null);
  const nothingLoggedToday =
    nutritionToday == null ||
    (nutritionToday.calories_kcal == null &&
      nutritionToday.protein_g == null &&
      nutritionToday.carbs_g == null &&
      nutritionToday.fat_g == null);
  if (hasAnyTarget && nothingLoggedToday && currentHour >= 15) {
    return 'No fuel logged yet today — quick entry on the Health tab';
  }

  // Nothing worth saying yet.
  return null;
}

// ---------------------------------------------------------------------------
// Load interpretation — strain against readiness, not against /21
// ---------------------------------------------------------------------------

/**
 * Interpret today's accumulated load relative to readiness.
 *
 * Thresholds are intentionally rough — the point is to turn a scale
 * number into a coaching word ("building" vs "over"), not to claim
 * sub-decimal precision. Recovery determines the "target" band:
 *   green  → target ~14, over ~18
 *   yellow → target ~10, over ~14
 *   red    → target ~6,  over ~10
 * These are heuristics, not measurements.
 */
function interpretLoad(
  strain: number | null,
  readiness: ReadinessLevel,
): { band: LoadBand; line: string } {
  if (strain == null) {
    return { band: 'unknown', line: 'No load signal yet today' };
  }

  const targetHigh =
    readiness === 'green' ? 14 : readiness === 'yellow' ? 10 : 6;
  const overHigh =
    readiness === 'green' ? 18 : readiness === 'yellow' ? 14 : 10;

  if (strain < targetHigh * 0.5) {
    return {
      band: 'low',
      line:
        readiness === 'red'
          ? 'Plenty of room — keep it light'
          : 'Load is low so far — room for a real session',
    };
  }
  if (strain < targetHigh) {
    return {
      band: 'building',
      line:
        readiness === 'green'
          ? 'Load is building — you can still push'
          : 'Load is building — stay on target',
    };
  }
  if (strain < overHigh) {
    return {
      band: 'at_target',
      line:
        readiness === 'green'
          ? 'Near target for a hard day — last push is fine'
          : 'Already at a sensible load for today',
    };
  }
  return {
    band: 'over',
    line:
      readiness === 'red'
        ? 'Already well over what recovery supports — back off'
        : 'Past target for today — prioritise recovery',
  };
}

// ---------------------------------------------------------------------------
// Plan hint rendering
// ---------------------------------------------------------------------------

function renderPlanHint(planned: PlannedSession[]): string | null {
  const enabled = planned.filter((p) => p.enabled);
  if (enabled.length === 0) return null;
  // Sort by time if present, untimed last
  const sorted = [...enabled].sort((a, b) => {
    const at = a.time || '99:99';
    const bt = b.time || '99:99';
    return at.localeCompare(bt);
  });
  return sorted
    .map((p) => {
      const label = renderPlannedLabel(p);
      return p.time ? `${p.time} ${label}` : label;
    })
    .join(' · ');
}

/**
 * Render a planned session as a single readable label. For grappling with
 * a subtype, show the subtype name only (e.g. "Jiu Jitsu") since grappling
 * is implied by context. For everything else, show the top-level label.
 */
function renderPlannedLabel(p: PlannedSession): string {
  if (p.type === 'grappling' && p.grappling_subtype) {
    return GRAPPLING_SCHEDULE_SUBTYPE_LABELS[p.grappling_subtype];
  }
  return SCHEDULE_SESSION_LABELS[p.type] ?? p.type;
}

// ---------------------------------------------------------------------------
// Headline
// ---------------------------------------------------------------------------

function buildHeadline(opts: {
  readiness: ReadinessLevel;
  whoopScore: number | null;
  source: PrimaryReadinessSource;
  intensity: SessionIntensity;
}): string {
  const { readiness, whoopScore, source, intensity } = opts;
  if (source === 'whoop' && whoopScore != null) {
    const verb =
      intensity === 'hard'
        ? 'push hard'
        : intensity === 'moderate'
          ? 'train moderate'
          : 'train light';
    return `${whoopScore}% recovered — ${verb} today`;
  }
  if (source === 'insights') {
    if (readiness === 'green') return 'Good to push today';
    if (readiness === 'yellow') return 'Moderate day — focus on technique';
    if (readiness === 'red') return 'Recovery priority today';
    return 'Not enough data yet';
  }
  return 'Log a session or connect a source for guidance';
}

// ---------------------------------------------------------------------------
// Main entry — build the daily coaching brief
// ---------------------------------------------------------------------------

export interface BuildDailyCoachingBriefInputs {
  whoopDay: WhoopSnapshot | null;
  insights: TrainingInsight | null;
  todayPlan: PlannedSession[];
  recentSessions: TrainingSession[];
  todayIsoDate: string;
  /** Today's nutrition record (manual/Cronometer/AI). Optional. */
  nutritionToday?: NutritionRecord | null;
  /** Daily calorie/macro targets. Optional — reasons are only added when both
   *  a record and targets exist for a given field. */
  nutritionTargets?: NutritionTargets | null;
  /**
   * Rolling window of past nutrition records (newest first), NOT including
   * today. Enables multi-day trend reasons like "protein behind target for
   * 3 days running". Optional — reasons only fire when both targets and
   * at least one history entry exist.
   */
  nutritionHistory?: NutritionRecord[] | null;
  /** Hour of day in the user's local timezone (0-23). Defaults to the
   *  machine clock. Passed explicitly so tests can simulate specific times. */
  currentHour?: number;
}

export function buildDailyCoachingBrief(
  inputs: BuildDailyCoachingBriefInputs,
): DailyCoachingBrief {
  const {
    whoopDay,
    insights,
    todayPlan,
    recentSessions,
    todayIsoDate,
    nutritionToday,
    nutritionTargets,
    nutritionHistory,
    currentHour: currentHourOverride,
  } = inputs;
  const currentHour =
    currentHourOverride != null ? currentHourOverride : new Date().getHours();

  // 1. Determine readiness source, preferring WHOOP when present.
  let readiness: ReadinessLevel;
  let primary_source: PrimaryReadinessSource;
  if (whoopDay && whoopDay.recovery_score != null) {
    readiness = whoopScoreToReadiness(whoopDay.recovery_score);
    primary_source = 'whoop';
  } else if (insights && insights.readiness !== 'grey') {
    readiness = insights.readiness;
    primary_source = 'insights';
  } else {
    readiness = 'grey';
    primary_source = 'none';
  }

  // 2. Base intensity + modes from readiness
  let suggested_intensity = readinessToIntensity(readiness);
  let suggested_modes = readinessToModes(readiness);

  // 3. Load-aware adjustment — 2+ hard sessions in last 3 days dials it back
  const recentHard = countHardSessionsInLastDays(recentSessions, todayIsoDate, 3);
  const loadOverride = recentHard >= 2 && suggested_intensity === 'hard';
  if (loadOverride) {
    suggested_intensity = 'moderate';
    // Move grappling out of the front slot, prefer zone2 first
    suggested_modes = ['zone2', 'grappling', 'weights'];
  }

  // 4. Reasons — keep to max 3, most relevant first
  const reasons: string[] = [];
  if (primary_source === 'whoop' && whoopDay && whoopDay.recovery_score != null) {
    reasons.push(`WHOOP recovery ${whoopDay.recovery_score}%`);
  } else if (primary_source === 'insights' && insights) {
    const topReason = insights.recommendation.reasons[0];
    if (topReason) reasons.push(topReason);
  }
  if (loadOverride) {
    reasons.push(`${recentHard} hard sessions in the last 3 days`);
  }
  if (
    primary_source === 'whoop' &&
    whoopDay &&
    whoopDay.sleep_hours != null &&
    whoopDay.sleep_hours < 6
  ) {
    reasons.push(`Only ${whoopDay.sleep_hours.toFixed(1)}h sleep last night`);
  }

  // Nutrition-aware reasons — only fire when we have BOTH today's record
  // and a target for the field being judged. Never fakes precision, never
  // turns Home into a nutrition dashboard; max one nutrition reason per
  // brief so it doesn't crowd out readiness and load.
  const nutritionReason = buildNutritionReason({
    nutritionToday,
    nutritionTargets,
    nutritionHistory,
    readiness,
    recentHard,
    currentHour,
  });
  if (nutritionReason) {
    reasons.push(nutritionReason);
  }

  // Cap at 3
  const cappedReasons = reasons.slice(0, 3);

  // 5. Plan hint + planned count
  const plan_hint = renderPlanHint(todayPlan);
  const planned_count = todayPlan.filter((p) => p.enabled).length;

  // 6. Headline
  const headline = buildHeadline({
    readiness,
    whoopScore: whoopDay?.recovery_score ?? null,
    source: primary_source,
    intensity: suggested_intensity,
  });

  // 7. WHOOP missing-workout flag — only if today's day row has zero workouts
  const whoop_workouts_missing_today =
    !!whoopDay && whoopDay.date === todayIsoDate && whoopDay.workout_count === 0;

  // 8. Load interpretation — turns raw WHOOP strain into a coaching word
  //    relative to today's readiness. Never exposes "/21".
  const { band: load_band, line: load_line } = interpretLoad(
    whoopDay?.daily_strain ?? null,
    readiness,
  );

  // 9. If load is already over target and we were going to push, dial down
  //    and fold that into the reasons list (capped at 3 total).
  let finalIntensity = suggested_intensity;
  let finalModes = suggested_modes;
  const finalReasons = [...cappedReasons];
  if (load_band === 'over' && finalIntensity === 'hard') {
    finalIntensity = 'moderate';
    finalModes = ['zone2', 'grappling', 'weights'];
    if (finalReasons.length < 3) {
      finalReasons.push('Load is already past today\'s target');
    }
  }

  return {
    headline,
    readiness,
    primary_source,
    suggested_intensity: finalIntensity,
    suggested_modes: finalModes,
    plan_hint,
    planned_count,
    reasons: finalReasons,
    whoop_workouts_missing_today,
    load_band,
    load_line,
  };
}

// ---------------------------------------------------------------------------
// Smaller helper — just the Train-screen intensity suggestion
// ---------------------------------------------------------------------------

/**
 * Small helper for the Train screen's AI coach suggestion bubbles.
 * Returns only an intensity recommendation plus a short explanation.
 * Cheaper than rebuilding the full brief for each SelectorRow mount.
 */
export function suggestTrainIntensity(inputs: {
  whoopDay: WhoopSnapshot | null;
  insights: TrainingInsight | null;
  recentSessions: TrainingSession[];
  todayIsoDate: string;
}): { intensity: SessionIntensity; reason: string } {
  const brief = buildDailyCoachingBrief({
    whoopDay: inputs.whoopDay,
    insights: inputs.insights,
    todayPlan: [],
    recentSessions: inputs.recentSessions,
    todayIsoDate: inputs.todayIsoDate,
  });
  const reason =
    brief.reasons[0] ??
    (brief.primary_source === 'none'
      ? 'No readiness signal yet'
      : 'Based on today\'s readiness');
  return { intensity: brief.suggested_intensity, reason };
}

// ---------------------------------------------------------------------------
// HIIT protocol suggestion — recovery-aware work/rest/rounds recipe
// ---------------------------------------------------------------------------

export interface HIITProtocolSuggestion {
  work_s: number;
  rest_s: number;
  rounds: number;
  /** Short explanation for the UI bubble ("Green recovery — push harder"). */
  reason: string;
  /** Human label for the protocol ("30/30 × 12"). */
  label: string;
}

/**
 * Suggest a HIIT work/rest/rounds recipe tailored to today's recovery.
 *
 * Rules are deliberately simple and explainable:
 *   green  → 30 / 30 × 12  (longer session, balanced rest, push available)
 *   yellow → 30 / 45 × 10  (standard interval, longer rest, moderate load)
 *   red    → 20 / 60 × 6   (short work, long rest, fewer rounds — maintain)
 *   grey   → 30 / 30 × 10  (default, no readiness signal)
 *
 * These are starting points, not mandates. The UI renders this as a
 * tappable "Suggested: 30/30 × 12" bubble that seeds the inputs on tap.
 */
export function suggestHIITProtocol(inputs: {
  whoopDay: WhoopSnapshot | null;
  insights: TrainingInsight | null;
  recentSessions: TrainingSession[];
  todayIsoDate: string;
}): HIITProtocolSuggestion {
  const brief = buildDailyCoachingBrief({
    whoopDay: inputs.whoopDay,
    insights: inputs.insights,
    todayPlan: [],
    recentSessions: inputs.recentSessions,
    todayIsoDate: inputs.todayIsoDate,
  });

  let work_s: number;
  let rest_s: number;
  let rounds: number;
  let reason: string;

  switch (brief.readiness) {
    case 'green':
      work_s = 30;
      rest_s = 30;
      rounds = 12;
      reason =
        brief.primary_source === 'whoop' &&
        inputs.whoopDay?.recovery_score != null
          ? `Recovery ${inputs.whoopDay.recovery_score}% — push harder`
          : 'Green recovery — push harder';
      break;
    case 'yellow':
      work_s = 30;
      rest_s = 45;
      rounds = 10;
      reason = 'Moderate recovery — balanced intervals';
      break;
    case 'red':
      work_s = 20;
      rest_s = 60;
      rounds = 6;
      reason = 'Low recovery — short work, long rest';
      break;
    default:
      work_s = 30;
      rest_s = 30;
      rounds = 10;
      reason = 'Default protocol — no readiness signal yet';
  }

  // Load-band override: if the day is already over target, back off hard.
  if (brief.load_band === 'over') {
    work_s = 20;
    rest_s = 60;
    rounds = Math.min(rounds, 6);
    reason = 'Load already over target — dial it back';
  }

  return {
    work_s,
    rest_s,
    rounds,
    reason,
    label: `${work_s}/${rest_s} × ${rounds}`,
  };
}
