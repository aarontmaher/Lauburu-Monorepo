/**
 * HIIT last-session home note — pure helper that picks the single
 * most useful compact signal to surface on Home's Today-Coach card
 * as "From your last HIIT: ...". Fully retrospective (session-based,
 * no store coupling), so it's safe to compute on every Home render
 * and never races with the ephemeral save/timer banners in Train.
 *
 * Signal priority (first match wins — only one line ever shown):
 *   1. PR beat — the latest HIIT session set a new personal best on
 *      a PR-eligible field (distance_m, avg_power_w, calories,
 *      kilojoules) against the max of all older same-label HIIT
 *      sessions. Returns "🏆 New best distance" style.
 *   2. vs-last delta — the latest HIIT session has comparable
 *      machine metrics against the next-older same-label HIIT
 *      session. Returns "+400m vs last" / "-15W vs last" / "matched
 *      last" via buildProgressionDelta.
 *   3. Interpretive coaching note — buildIntervalCoachingNote
 *      (WHOOP / suggested-intensity / HR zone / work-rest-ratio).
 *      Only applies WHOOP + suggested-intensity ctx when the latest
 *      HIIT session is TODAY — historical context mismatch is worse
 *      than no context.
 *   4. Nothing meaningful → return null (Home hides the line).
 *
 * Freshness gate: older than `maxAgeDays` (default 3) returns null.
 * A 5-day-old HIIT result is no longer a continuity cue — it's
 * history, and surfacing it as "your last HIIT" implies recency.
 */
import {
  buildIntervalCoachingNote,
  type IntervalCoachingContext,
} from '@lauburu/shared';
import type {
  TrainingSession,
  SessionIntensity,
  ConditioningSubtype,
  MachineMetrics,
} from '@lauburu/shared';
import {
  buildProgressionDelta,
  type SavedHIITProtocolMetrics,
} from '../store/hiit-protocols-store';

/** Subtypes that count as HIIT/interval work. Kept in sync with the
 * same set used in session-summary.ts and the TimerScreen modality
 * checks — a single source of truth here would require a shared
 * helper, left as a future cleanup. */
const HIIT_SUBTYPES: ConditioningSubtype[] = [
  'hiit',
  'intervals',
  'sprint_intervals',
  'circuit',
];

/** Human-readable labels for PR-eligible fields, matching the PR
 * labels used inside hiit-protocols-store.ts. Kept local to avoid
 * a cross-file coupling that would drag the store into this pure
 * helper. If a third UI needs the same labels, lift them to shared. */
const PR_FIELD_LABELS: Record<
  'distance_m' | 'avg_power_w' | 'calories' | 'kilojoules',
  string
> = {
  distance_m: 'distance',
  avg_power_w: 'avg power',
  calories: 'calories',
  kilojoules: 'kJ',
};

/** Priority-ordered PR-eligible field list. Used for both max
 * computation and tie-break when a session beats multiple fields
 * at once — only the highest-priority improvement is announced so
 * the line stays compact. */
const PR_FIELD_ORDER: Array<'distance_m' | 'avg_power_w' | 'calories' | 'kilojoules'> = [
  'distance_m',
  'avg_power_w',
  'calories',
  'kilojoules',
];

function isHIIT(s: TrainingSession): boolean {
  if (s.type !== 'conditioning') return false;
  const cd = s.conditioning;
  if (!cd || !cd.interval) return false;
  return HIIT_SUBTYPES.includes(cd.subtype);
}

/** UTC-safe full-day difference between two YYYY-MM-DD date strings. */
function daysBetween(earlier: string, later: string): number {
  const a = new Date(earlier + 'T00:00:00Z').getTime();
  const b = new Date(later + 'T00:00:00Z').getTime();
  return Math.floor((b - a) / (24 * 60 * 60 * 1000));
}

/** Normalize a protocol label for case-insensitive matching.
 *  Mirrors the store's internal normalizeLabel helper. */
function normalizeLabel(label: string | undefined): string {
  return (label ?? '').trim().toLowerCase();
}

export interface BuildLastHIITHomeNoteInputs {
  sessions: TrainingSession[];
  /** Today in YYYY-MM-DD (caller's local date). */
  todayIsoDate: string;
  /** WHOOP recovery score for today, 0-100. Only applied if the
   *  latest HIIT session happened today. */
  whoopRecovery?: number;
  /** Suggested intensity for today from the coaching layer. Only
   *  applied if the latest HIIT session happened today. */
  suggestedIntensity?: SessionIntensity;
  /** Freshness gate in whole days — older sessions return null.
   *  Defaults to 3. */
  maxAgeDays?: number;
}

/**
 * Return the compact note (without any "Last HIIT:" prefix — the UI
 * renders its own label) or null when no meaningful signal exists.
 * Pure function, no side effects.
 */
export function buildLastHIITHomeNote(
  inputs: BuildLastHIITHomeNoteInputs,
): string | null {
  const {
    sessions,
    todayIsoDate,
    whoopRecovery,
    suggestedIntensity,
    maxAgeDays = 3,
  } = inputs;

  // Sort HIIT sessions newest-first. created_at is the tiebreaker
  // for same-day entries so the most-recently-logged wins.
  const hiit = sessions
    .filter(isHIIT)
    .sort((a, b) =>
      (b.date + '|' + b.created_at).localeCompare(a.date + '|' + a.created_at),
    );
  if (hiit.length === 0) return null;

  const latest = hiit[0];

  // Freshness gate — stale sessions don't get to hijack the Home card.
  const ageDays = daysBetween(latest.date, todayIsoDate);
  if (ageDays < 0 || ageDays > maxAgeDays) return null;

  const latestLabelNorm = normalizeLabel(latest.conditioning?.interval?.label);
  const latestMM = latest.conditioning?.machine_metrics;

  // Same-label older sessions. Used for both PR scan and vs-last
  // delta computation. Skipped when the latest session has no label
  // (nothing to compare against meaningfully).
  const sameLabelPrior =
    latestLabelNorm.length > 0
      ? hiit.slice(1).filter(
          (s) =>
            normalizeLabel(s.conditioning?.interval?.label) === latestLabelNorm,
        )
      : [];

  // -- Priority 1: retrospective PR detection ----------------------------
  if (latestMM && sameLabelPrior.length > 0) {
    // Compute max of each PR-eligible field across all older matching
    // sessions. Sessions without a value on a field are skipped for
    // that field only.
    const priorFieldMax: Partial<Record<keyof MachineMetrics, number>> = {};
    for (const s of sameLabelPrior) {
      const mm = s.conditioning?.machine_metrics;
      if (!mm) continue;
      for (const f of PR_FIELD_ORDER) {
        const v = mm[f];
        if (v != null && Number.isFinite(v)) {
          const currentMax = priorFieldMax[f];
          if (currentMax == null || v > currentMax) {
            priorFieldMax[f] = v;
          }
        }
      }
    }
    // Walk the priority order and announce the first beat.
    for (const f of PR_FIELD_ORDER) {
      const cur = latestMM[f];
      const best = priorFieldMax[f];
      if (cur != null && best != null && cur > best) {
        return `🏆 New best ${PR_FIELD_LABELS[f]}`;
      }
    }
  }

  // -- Priority 2: vs-last delta -----------------------------------------
  // Compare against the single next-older same-label session's metrics.
  // buildProgressionDelta handles field-priority selection internally.
  if (latestMM && sameLabelPrior.length > 0) {
    const prior = sameLabelPrior[0];
    const priorMM = prior.conditioning?.machine_metrics;
    if (priorMM) {
      const priorSnap: SavedHIITProtocolMetrics = {
        distance_m: priorMM.distance_m,
        calories: priorMM.calories,
        kilojoules: priorMM.kilojoules,
        avg_power_w: priorMM.avg_power_w,
        avg_hr_bpm: priorMM.avg_hr_bpm,
        duration_min: prior.duration_min,
        captured_at: prior.date,
      };
      const delta = buildProgressionDelta(
        {
          metrics: latestMM,
          duration_min: latest.duration_min,
        },
        priorSnap,
      );
      if (delta) return delta;
    }
  }

  // -- Priority 3: interpretive coaching note ----------------------------
  // Only pass WHOOP / suggested-intensity ctx if the latest session is
  // TODAY — applying today's recovery to a two-day-old session is
  // worse than no context.
  const latestIsToday = latest.date === todayIsoDate;
  const ctx: IntervalCoachingContext | undefined = latestIsToday
    ? {
        whoopRecovery,
        suggestedIntensity,
      }
    : undefined;
  const note = buildIntervalCoachingNote(latest, ctx);
  if (note) return note;

  return null;
}
