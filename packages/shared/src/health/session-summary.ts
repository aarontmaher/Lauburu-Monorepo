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
