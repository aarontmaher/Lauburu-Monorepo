/**
 * Normalized session summary — a coach-ready shape layer over TrainingSession.
 *
 * Goal: make it easy for the coaching engine (and later AI/personalization)
 * to reason about "what kind of session was this" without re-walking every
 * segment. Pure derivation — does not mutate the input.
 */
import type {
  TrainingSession,
  SessionSegment,
  SegmentType,
  SessionIntensity,
  LiftingFocus,
  Modality,
} from '../types/training';
import { SEGMENT_TYPE_LABELS, MODALITY_LABELS } from '../types/training';

export type SessionKind =
  | 'grappling'
  | 'wrestling'
  | 'hiit'
  | 'zone2'
  | 'weights'
  | 'recovery'
  | 'other';

export type SessionShape =
  | 'technique_heavy'
  | 'wrestling_heavy'
  | 'live_round_heavy'
  | 'mixed_grappling'
  | 'interval'
  | 'aerobic'
  | 'strength'
  | 'functional'
  | 'rehab'
  | 'recovery'
  | 'other';

export interface SessionSummary {
  kind: SessionKind;
  shape: SessionShape;
  total_duration_min: number;
  dominant_segment?: SegmentType;
  dominant_segment_share?: number; // 0..1
  sparring_minutes?: number;
  intensity: SessionIntensity;
  headline: string;
  /**
   * For HIIT / interval sessions, a compact post-session takeaway combining
   * protocol, modality, and any captured machine metrics. Null for sessions
   * without interval detail or machine data.
   */
  interval_takeaway?: string;
}

/**
 * Grappling segment buckets used for shape classification.
 */
const TECHNIQUE_SEGMENTS: SegmentType[] = ['technique', 'drilling'];
const LIVE_SEGMENTS: SegmentType[] = ['live_rounds', 'comp_prep', 'open_mat'];
const WRESTLE_SEGMENTS: SegmentType[] = ['wrestling', 'takedowns'];

function sumDurations(segments: SessionSegment[]): number {
  return segments.reduce((acc, s) => acc + (s.duration_min || 0), 0);
}

function bucketMinutes(
  segments: SessionSegment[],
  types: SegmentType[],
): number {
  return segments
    .filter((s) => types.includes(s.type))
    .reduce((acc, s) => acc + (s.duration_min || 0), 0);
}

function dominantSegment(
  segments: SessionSegment[],
): { type: SegmentType; share: number } | undefined {
  if (segments.length === 0) return undefined;
  const total = sumDurations(segments) || 1;
  const byType = new Map<SegmentType, number>();
  for (const s of segments) {
    byType.set(s.type, (byType.get(s.type) ?? 0) + (s.duration_min || 0));
  }
  let bestType: SegmentType = segments[0].type;
  let bestMin = 0;
  for (const [t, m] of byType.entries()) {
    if (m > bestMin) {
      bestType = t;
      bestMin = m;
    }
  }
  return { type: bestType, share: bestMin / total };
}

function classifyGrapplingShape(segments: SessionSegment[]): SessionShape {
  if (segments.length === 0) return 'mixed_grappling';
  const total = sumDurations(segments) || 1;
  const tech = bucketMinutes(segments, TECHNIQUE_SEGMENTS) / total;
  const live = bucketMinutes(segments, LIVE_SEGMENTS) / total;
  const wrestle = bucketMinutes(segments, WRESTLE_SEGMENTS) / total;

  // Highest-share bucket wins if >= 0.5, otherwise "mixed"
  const buckets = [
    { shape: 'technique_heavy' as SessionShape, share: tech },
    { shape: 'live_round_heavy' as SessionShape, share: live },
    { shape: 'wrestling_heavy' as SessionShape, share: wrestle },
  ];
  buckets.sort((a, b) => b.share - a.share);
  if (buckets[0].share >= 0.5) return buckets[0].shape;
  return 'mixed_grappling';
}

function liftingShape(focus: LiftingFocus | undefined): SessionShape {
  if (focus === 'functional_muscle') return 'functional';
  if (focus === 'rehab') return 'rehab';
  return 'strength';
}

function buildHeadline(opts: {
  kind: SessionKind;
  shape: SessionShape;
  minutes: number;
  modality?: Modality;
  dominantLabel?: string;
}): string {
  const { kind, shape, minutes, modality, dominantLabel } = opts;
  const mins = `${Math.max(0, Math.round(minutes))}min`;

  switch (kind) {
    case 'grappling': {
      switch (shape) {
        case 'technique_heavy':
          return `Technique-heavy grappling · ${mins}`;
        case 'wrestling_heavy':
          return `Wrestling-heavy grappling · ${mins}`;
        case 'live_round_heavy':
          return `Live-round heavy grappling · ${mins}`;
        default:
          return `Mixed grappling · ${mins}${dominantLabel ? ` · ${dominantLabel} dominant` : ''}`;
      }
    }
    case 'wrestling':
      return `Wrestling session · ${mins}`;
    case 'hiit':
      return `HIIT interval · ${mins}${modality ? ` · ${MODALITY_LABELS[modality]}` : ''}`;
    case 'zone2':
      return `Zone 2 aerobic · ${mins}${modality ? ` · ${MODALITY_LABELS[modality]}` : ''}`;
    case 'weights':
      return `${shape === 'functional' ? 'Functional muscle' : shape === 'rehab' ? 'Rehab' : 'Strength'} lifting · ${mins}`;
    case 'recovery':
      return `Recovery · ${mins}`;
    default:
      return `Session · ${mins}`;
  }
}

/**
 * Derive a normalized summary from a TrainingSession.
 * Pure function — no mutation, no side effects.
 */
export function summarizeSession(s: TrainingSession): SessionSummary {
  const segments = s.segments ?? [];
  const segTotal = sumDurations(segments);
  const totalMin = segTotal > 0 ? segTotal : s.duration_min;

  // Grappling branch (has segments or non-conditioning type)
  if (s.type !== 'conditioning' && s.type !== 'other') {
    const dom = dominantSegment(segments);
    const shape =
      s.type === 'wrestling'
        ? 'wrestling_heavy'
        : classifyGrapplingShape(segments);
    const sparring = bucketMinutes(segments, [
      'live_rounds',
      'comp_prep',
      'wrestling',
    ]);
    return {
      kind: s.type === 'wrestling' ? 'wrestling' : 'grappling',
      shape,
      total_duration_min: totalMin,
      dominant_segment: dom?.type,
      dominant_segment_share: dom?.share,
      sparring_minutes: sparring > 0 ? sparring : undefined,
      intensity: s.intensity,
      headline: buildHeadline({
        kind: s.type === 'wrestling' ? 'wrestling' : 'grappling',
        shape,
        minutes: totalMin,
        dominantLabel: dom ? SEGMENT_TYPE_LABELS[dom.type] : undefined,
      }),
    };
  }

  // Conditioning branch
  if (s.type === 'conditioning' && s.conditioning) {
    const cd = s.conditioning;
    const modality = cd.modality;

    if (cd.subtype === 'weight_training') {
      const shape = liftingShape(cd.weight_training?.focus);
      return {
        kind: 'weights',
        shape,
        total_duration_min: totalMin,
        intensity: s.intensity,
        headline: buildHeadline({ kind: 'weights', shape, minutes: totalMin }),
      };
    }

    const isHIIT = ['hiit', 'intervals', 'sprint_intervals', 'circuit'].includes(
      cd.subtype,
    );
    if (isHIIT) {
      // Recompute duration from interval if present (more accurate than top-level)
      const iv = cd.interval;
      const intervalMin = iv
        ? Math.round(((iv.work_duration_s + iv.rest_duration_s) * iv.rounds) / 60)
        : totalMin;
      // Build the post-session interval takeaway from protocol + machine
      // metrics, only if there's at least one piece of real detail.
      const takeawayParts: string[] = [];
      if (iv) {
        takeawayParts.push(
          `${iv.work_duration_s}s/${iv.rest_duration_s}s × ${iv.rounds}`,
        );
      }
      const mm = cd.machine_metrics;
      if (mm) {
        if (mm.distance_m != null) takeawayParts.push(`${mm.distance_m}m`);
        if (mm.calories != null) takeawayParts.push(`${mm.calories}kcal`);
        if (mm.avg_power_w != null) takeawayParts.push(`${mm.avg_power_w}W avg`);
        if (mm.max_hr_bpm != null) takeawayParts.push(`${mm.max_hr_bpm}bpm peak`);
      }
      const interval_takeaway =
        takeawayParts.length > 0 ? takeawayParts.join(' · ') : undefined;
      return {
        kind: 'hiit',
        shape: 'interval',
        total_duration_min: intervalMin,
        intensity: s.intensity,
        headline: buildHeadline({
          kind: 'hiit',
          shape: 'interval',
          minutes: intervalMin,
          modality,
        }),
        interval_takeaway,
      };
    }

    const isZone2 = ['zone2', 'steady_state', 'tempo'].includes(cd.subtype);
    if (isZone2) {
      return {
        kind: 'zone2',
        shape: 'aerobic',
        total_duration_min: totalMin,
        intensity: s.intensity,
        headline: buildHeadline({
          kind: 'zone2',
          shape: 'aerobic',
          minutes: totalMin,
          modality,
        }),
      };
    }

    const isRecovery = [
      'recovery_cardio',
      'mobility',
      'respiratory_training',
      'breathing_warmup',
      'recovery_breathing',
    ].includes(cd.subtype);
    if (isRecovery) {
      return {
        kind: 'recovery',
        shape: 'recovery',
        total_duration_min: totalMin,
        intensity: s.intensity,
        headline: buildHeadline({
          kind: 'recovery',
          shape: 'recovery',
          minutes: totalMin,
        }),
      };
    }
  }

  return {
    kind: 'other',
    shape: 'other',
    total_duration_min: totalMin,
    intensity: s.intensity,
    headline: buildHeadline({ kind: 'other', shape: 'other', minutes: totalMin }),
  };
}

// ---------------------------------------------------------------------------
// Post-session interval coaching note — one interpretive sentence that
// layers over the raw `interval_takeaway` facts. Surfaces ONLY when we
// have enough signal to say something honest: a machine-metrics value,
// a WHOOP recovery, or a suggested-intensity mismatch. Returns null
// when there's nothing meaningful to say (the UI then falls back to
// the raw takeaway alone).
//
// Pure function — no mutation, no WHOOP-store coupling. The UI passes
// whatever context it actually has at render time; if the session is
// historical, the UI passes `ctx` undefined and only session-internal
// signals (HR zone, metrics presence) are used.
// ---------------------------------------------------------------------------

/** Minimal context the note-builder needs from the outside world. */
export interface IntervalCoachingContext {
  /**
   * WHOOP recovery score (0-100) for the session's date. The UI should
   * only pass this when the session is today — historical WHOOP is not
   * reliably available and passing today's recovery to a 5-day-old
   * session would be a lie.
   */
  whoopRecovery?: number;
  /**
   * The intensity the coaching layer recommended for the session's
   * date. Used to build "harder/lighter than suggested" messaging.
   * Derived from WHOOP or planner signals by the caller; this function
   * is agnostic about how it was computed.
   */
  suggestedIntensity?: SessionIntensity;
}

/** Compare two intensities by order rank. Returns -1/0/1. */
function compareIntensity(a: SessionIntensity, b: SessionIntensity): number {
  const rank: Record<SessionIntensity, number> = {
    light: 1,
    moderate: 2,
    hard: 3,
  };
  return Math.sign(rank[a] - rank[b]);
}

/**
 * Build a compact 1-sentence coaching interpretation of a HIIT session,
 * combining protocol, machine metrics, and any available daily context.
 *
 * Returns null when the session is not a HIIT/interval session or when
 * there is insufficient signal to say anything beyond the raw facts.
 */
export function buildIntervalCoachingNote(
  session: TrainingSession,
  ctx?: IntervalCoachingContext,
): string | null {
  if (session.type !== 'conditioning' || !session.conditioning) return null;
  const cd = session.conditioning;
  const isHIIT = ['hiit', 'intervals', 'sprint_intervals', 'circuit'].includes(
    cd.subtype,
  );
  if (!isHIIT || !cd.interval) return null;

  const mm = cd.machine_metrics;
  const rec = ctx?.whoopRecovery;
  const suggested = ctx?.suggestedIntensity;
  const actual = session.intensity;

  // -- Priority 1: suggested-vs-actual mismatch ----------------------------
  // Highest-signal path. Use machine metrics as supporting detail when
  // present, otherwise a generic mismatch note.
  if (suggested && suggested !== actual) {
    const cmp = compareIntensity(actual, suggested);
    if (cmp > 0) {
      // Went harder than suggested.
      if (mm?.distance_m != null && mm.avg_power_w != null) {
        return `Logged ${mm.distance_m}m @ ${mm.avg_power_w}W avg — harder than the suggested ${suggested} day.`;
      }
      if (mm?.distance_m != null) {
        return `Logged ${mm.distance_m}m — harder than the suggested ${suggested} day.`;
      }
      if (mm?.avg_power_w != null) {
        return `Avg ${mm.avg_power_w}W — harder than the suggested ${suggested} day.`;
      }
      if (mm?.max_hr_bpm != null && mm.max_hr_bpm >= 170) {
        return `Peaked at ${mm.max_hr_bpm}bpm — harder than the suggested ${suggested} day.`;
      }
      return `Logged harder than the suggested ${suggested} day — expect a bigger strain hit.`;
    } else {
      // Went lighter than suggested — usually a good thing.
      if (mm?.distance_m != null && mm.avg_power_w != null) {
        return `${mm.distance_m}m @ ${mm.avg_power_w}W — controlled, pulled back from the suggested ${suggested} day.`;
      }
      return `Pulled back from the suggested ${suggested} day — controlled effort.`;
    }
  }

  // -- Priority 2: low recovery + hard effort (strain warning) -------------
  if (rec != null && rec < 34 && actual === 'hard') {
    if (mm?.avg_power_w != null) {
      return `Hard ${mm.avg_power_w}W avg on low recovery (${Math.round(rec)}%) — expect a bigger strain hit.`;
    }
    return `Hard session on low recovery (${Math.round(rec)}%) — expect a bigger strain hit.`;
  }

  // -- Priority 3: high recovery + light effort (had room) -----------------
  if (rec != null && rec >= 67 && actual === 'light') {
    return `Recovery was high (${Math.round(rec)}%) — room to push harder next time if you want.`;
  }

  // -- Priority 4: matched the suggested day (positive reinforcement) ------
  if (suggested && suggested === actual) {
    if (mm?.distance_m != null && mm.avg_power_w != null) {
      return `${mm.distance_m}m @ ${mm.avg_power_w}W — matched the suggested ${suggested} recommendation.`;
    }
    if (mm?.distance_m != null) {
      return `${mm.distance_m}m logged — matched the suggested ${suggested} recommendation.`;
    }
  }

  // -- Priority 5: HR zone interpretation (no external context needed) ----
  // Only when avg HR is present and sits clearly in one zone — avoid
  // fake precision in the middle bands.
  if (mm?.avg_hr_bpm != null) {
    const bpm = mm.avg_hr_bpm;
    if (bpm >= 165) {
      return `Avg HR ${bpm}bpm — sustained threshold effort, high strain likely.`;
    }
    if (bpm >= 145) {
      return `Avg HR ${bpm}bpm — tempo zone, controlled hard effort.`;
    }
    if (bpm <= 130 && bpm >= 90) {
      return `Avg HR ${bpm}bpm — aerobic, low-strain session.`;
    }
  }

  // -- Priority 6: machine output without physiology ----------------------
  // Last-resort shape note so sessions with partial metrics still get
  // something beyond the raw facts line.
  if (mm?.avg_power_w != null && cd.interval) {
    const iv = cd.interval;
    const workRatio = iv.work_duration_s / (iv.work_duration_s + iv.rest_duration_s);
    if (workRatio >= 0.5) {
      return `${mm.avg_power_w}W avg across ${iv.rounds} rounds — high work-to-rest ratio, expect fatigue.`;
    }
  }

  return null;
}
