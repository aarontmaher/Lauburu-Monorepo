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
      const label = scheduleLabelFor(p.type);
      return p.time ? `${p.time} ${label}` : label;
    })
    .join(' · ');
}

function scheduleLabelFor(type: string): string {
  switch (type) {
    case 'drilling':
      return 'Drilling';
    case 'sparring':
      return 'Sparring';
    case 'positional':
      return 'Positional';
    case 'class':
      return 'Class';
    case 'open_mat':
      return 'Open mat';
    case 'conditioning':
      return 'Conditioning';
    case 'rest':
      return 'Rest';
    default:
      return type;
  }
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
}

export function buildDailyCoachingBrief(
  inputs: BuildDailyCoachingBriefInputs,
): DailyCoachingBrief {
  const { whoopDay, insights, todayPlan, recentSessions, todayIsoDate } = inputs;

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
