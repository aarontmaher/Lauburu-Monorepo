/**
 * Manual training session entry types.
 * NO-GI ONLY — this app does not track gi training.
 */

// ---------------------------------------------------------------------------
// Session types
// ---------------------------------------------------------------------------

export type SessionType =
  | 'class'
  | 'sparring'
  | 'drilling'
  | 'wrestling'
  | 'comp'
  | 'open_mat'
  | 'conditioning'
  | 'other';

export type SessionIntensity = 'light' | 'moderate' | 'hard';

export const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  class: 'Class',
  sparring: 'Sparring',
  drilling: 'Drilling',
  wrestling: 'Wrestling',
  comp: 'Competition',
  open_mat: 'Open Mat',
  conditioning: 'Conditioning',
  other: 'Other',
};

export const INTENSITY_LABELS: Record<SessionIntensity, string> = {
  light: 'Light',
  moderate: 'Moderate',
  hard: 'Hard',
};

export const TAG_OPTIONS = [
  'no-gi',
  'wrestling',
  'takedowns',
  'scrambling',
  'positional',
  'technique',
  'comp-prep',
  'flow',
] as const;

// ---------------------------------------------------------------------------
// Conditioning subtypes
// ---------------------------------------------------------------------------

export type ConditioningSubtype =
  | 'hiit'
  | 'steady_state'
  | 'intervals'
  | 'sprint_intervals'
  | 'tempo'
  | 'zone2'
  | 'weight_training'
  | 'circuit'
  | 'mobility'
  | 'recovery_cardio'
  | 'respiratory_training'
  | 'breathing_warmup'
  | 'recovery_breathing'
  | 'other';

export const CONDITIONING_SUBTYPE_LABELS: Record<ConditioningSubtype, string> = {
  hiit: 'HIIT',
  steady_state: 'Steady State',
  intervals: 'Intervals',
  sprint_intervals: 'Sprint Intervals',
  tempo: 'Tempo',
  zone2: 'Zone 2',
  weight_training: 'Weight Training',
  circuit: 'Circuit',
  mobility: 'Mobility',
  recovery_cardio: 'Recovery Cardio',
  respiratory_training: 'Respiratory',
  breathing_warmup: 'Breathing Warmup',
  recovery_breathing: 'Recovery Breathing',
  other: 'Other',
};

export type Modality =
  | 'assault_bike'
  | 'rower'
  | 'skierg'
  | 'running'
  | 'bike'
  | 'bodyweight'
  | 'kettlebell'
  | 'barbell'
  | 'other';

export const MODALITY_LABELS: Record<Modality, string> = {
  assault_bike: 'Assault Bike',
  rower: 'Rower',
  skierg: 'SkiErg',
  running: 'Running',
  bike: 'Bike',
  bodyweight: 'Bodyweight',
  kettlebell: 'Kettlebell',
  barbell: 'Barbell',
  other: 'Other',
};

export type LiftingFocus =
  | 'strength'
  | 'functional_muscle'
  | 'rehab';

export const LIFTING_FOCUS_LABELS: Record<LiftingFocus, string> = {
  strength: 'Strength',
  functional_muscle: 'Functional muscle building',
  rehab: 'Rehab',
};

export type RespiratoryType = 'inspiratory' | 'expiratory' | 'mixed';

export type RespiratoryDevice = 'airofit' | 'wello2' | 'other' | 'none';

export const RESPIRATORY_DEVICE_LABELS: Record<RespiratoryDevice, string> = {
  none: 'No device',
  airofit: 'Airofit',
  wello2: 'WellO2',
  other: 'Other',
};

// ---------------------------------------------------------------------------
// Conditioning detail — subtype-specific fields
// ---------------------------------------------------------------------------

/** HIIT / intervals structure */
export interface IntervalDetail {
  work_duration_s: number;
  rest_duration_s: number;
  rounds: number;
  sets?: number;
  modality?: Modality;
  /** Preset ID if a standard protocol was used */
  preset_id?: string;
  /** Optional user-provided label for this protocol ("Tabata", "Bike HIIT"). */
  label?: string;
  /** Per-interval machine metrics when a connected or parsed machine is used. */
  per_interval?: IntervalMachineSample[];
}

/** Per-interval machine sample — one entry per completed work interval. */
export interface IntervalMachineSample {
  /** 1-indexed interval number within the session. */
  index: number;
  /** Actual work duration in seconds (may differ from planned if manually cut). */
  work_duration_s?: number;
  /** Distance covered during this interval (metres). */
  distance_m?: number;
  /** Calories burned during this interval (kcal). */
  calories?: number;
  /** Average power during this interval (watts). */
  avg_power_w?: number;
  /** Peak power during this interval (watts). */
  max_power_w?: number;
  /** Average cadence (rpm for bikes, spm for rowers, stride for running). */
  avg_cadence?: number;
  /** Peak cadence (same units as avg_cadence). */
  max_cadence?: number;
  /** Average HR during this interval (bpm). Chest strap or paired machine. */
  avg_hr_bpm?: number;
  /** Peak HR during this interval (bpm). */
  max_hr_bpm?: number;
}

// ---------------------------------------------------------------------------
// Machine-originated session data
// ---------------------------------------------------------------------------

/**
 * Where the workout detail came from. Explicit provenance matters because
 * the app combines WHOOP (readiness / physiology) with machine output —
 * the two are complementary sources, not the same source, and honest
 * provenance keeps coaching decisions auditable.
 */
export type WorkoutSource =
  | 'phone_timer' // App's built-in interval timer — no machine detail
  | 'machine_connected' // Live BLE/FTMS connection (future, stub today)
  | 'manual_machine_entry' // User typed the machine's end-of-session numbers
  | 'imported'; // Pulled from a third-party file/import (future)

export const WORKOUT_SOURCE_LABELS: Record<WorkoutSource, string> = {
  phone_timer: 'Phone timer',
  machine_connected: 'Machine connected',
  manual_machine_entry: 'Manual entry',
  imported: 'Imported',
};

/**
 * Whole-session machine metrics captured from a cardio machine.
 *
 * Every field is optional — different machines expose different subsets
 * (e.g. the Assault Bike exposes power + cadence + calories + distance
 * but not pace; a rower exposes pace + stroke rate + distance; a
 * treadmill exposes distance + speed + cadence). We store what's
 * available and leave the rest null. NO field is synthesised.
 *
 * This layer is deliberately WHOOP-independent: WHOOP is the readiness
 * and physiology trend source; the cardio machine is the workout-
 * execution source. Both can be present simultaneously.
 */
export interface MachineMetrics {
  /** Total distance covered (metres). Rower, bike, treadmill, skierg. */
  distance_m?: number;
  /** Total calories (kcal). Most machines expose this. */
  calories?: number;
  /** Total work output (kJ). Rower-specific but some bikes expose too. */
  kilojoules?: number;
  /** Average power across the session (watts). */
  avg_power_w?: number;
  /** Peak power (watts). */
  max_power_w?: number;
  /** Average pace (seconds per 500m for rowers, seconds per km for running). */
  avg_pace_s?: number;
  /** Best pace (same units as avg_pace_s). */
  max_pace_s?: number;
  /** Average cadence — rpm for bikes, spm for rowers, stride/min running. */
  avg_cadence?: number;
  /** Peak cadence (same units). */
  max_cadence?: number;
  /** Average speed (km/h). Treadmill, bike, skierg. */
  avg_speed_kmh?: number;
  /** Peak speed (km/h). */
  max_speed_kmh?: number;
  /** Average HR across the session (bpm). Paired chest strap or machine. */
  avg_hr_bpm?: number;
  /** Peak HR (bpm). */
  max_hr_bpm?: number;
  /** Total stroke count (rower-specific). */
  strokes?: number;
}

/** Standard HIIT interval presets */
export interface HIITPreset {
  id: string;
  label: string;
  work_s: number;
  rest_s: number;
  rounds: number;
  description: string;
}

export const HIIT_PRESETS: HIITPreset[] = [
  { id: '15_45', label: '15/45', work_s: 15, rest_s: 45, rounds: 10, description: '10 × 15s work / 45s rest' },
  { id: '30_30', label: '30/30', work_s: 30, rest_s: 30, rounds: 10, description: '10 × 30s work / 30s rest' },
  { id: '15_30', label: '15/30', work_s: 15, rest_s: 30, rounds: 12, description: '12 × 15s work / 30s rest' },
  { id: '4x4', label: '4×4min', work_s: 240, rest_s: 180, rounds: 4, description: '4 × 4min work / 3min rest' },
  { id: 'custom', label: 'Custom', work_s: 30, rest_s: 30, rounds: 10, description: 'Set your own intervals' },
];

/**
 * Conditioning coaching categories — simplified for coach reasoning.
 * Each conditioning subtype maps to one of these.
 */
export type ConditioningCategory = 'hiit' | 'zone2' | 'recovery';

export const CONDITIONING_CATEGORY_MAP: Record<ConditioningSubtype, ConditioningCategory> = {
  hiit: 'hiit',
  intervals: 'hiit',
  sprint_intervals: 'hiit',
  circuit: 'hiit',
  steady_state: 'zone2',
  zone2: 'zone2',
  tempo: 'zone2',
  recovery_cardio: 'recovery',
  weight_training: 'hiit', // strength ≈ high-intensity
  mobility: 'recovery',
  respiratory_training: 'recovery',
  breathing_warmup: 'recovery',
  recovery_breathing: 'recovery',
  other: 'zone2',
};

/** Steady state / zone 2 */
export interface SteadyStateDetail {
  modality?: Modality;
  intensity_note?: string;
}

/** Weight training */
export interface WeightTrainingDetail {
  focus: LiftingFocus;
}

/** Respiratory / breathing training */
export interface RespiratoryDetail {
  respiratory_type: RespiratoryType;
  device_used?: string;
  resistance_level?: number;
  breaths?: number;
  sets?: number;
  duration_minutes?: number;
  timing: 'pre_training' | 'post_training' | 'standalone';
}

/** Union of all conditioning detail types */
export interface ConditioningDetail {
  subtype: ConditioningSubtype;
  modality?: Modality;
  interval?: IntervalDetail;
  steady_state?: SteadyStateDetail;
  weight_training?: WeightTrainingDetail;
  respiratory?: RespiratoryDetail;
  /**
   * Provenance of the workout detail. `phone_timer` is the default for
   * sessions logged through the app's own interval timer. When the user
   * enters numbers read off a cardio machine, or a future BLE/FTMS
   * connection lands, this flips to `manual_machine_entry` or
   * `machine_connected` respectively.
   */
  source?: WorkoutSource;
  /**
   * Whole-session metrics captured from the cardio machine. Complementary
   * to WHOOP — WHOOP gives readiness and post-session strain; this gives
   * the in-session output detail that WHOOP cannot see.
   */
  machine_metrics?: MachineMetrics;
}

// ---------------------------------------------------------------------------
// Training session
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Session segments — parts of a mixed session
// ---------------------------------------------------------------------------

export type SegmentType =
  | 'technique'
  | 'drilling'
  | 'positional'
  | 'wrestling'
  | 'takedowns'
  | 'live_rounds'
  | 'open_mat'
  | 'comp_prep'
  | 'conditioning_finisher'
  | 'other';

export const SEGMENT_TYPE_LABELS: Record<SegmentType, string> = {
  technique: 'Technique',
  drilling: 'Drilling',
  positional: 'Positional',
  wrestling: 'Wrestling',
  takedowns: 'Takedowns',
  live_rounds: 'Live Rounds',
  open_mat: 'Open Mat',
  comp_prep: 'Comp Prep',
  conditioning_finisher: 'Finisher',
  other: 'Other',
};

export type PartnerFormat =
  | 'group_training'
  | 'group_of_3'
  | 'one_partner'
  | 'rotating_partners'
  | 'solo'
  | 'other';

export const PARTNER_FORMAT_LABELS: Record<PartnerFormat, string> = {
  group_training: 'Group',
  group_of_3: 'Group of 3',
  one_partner: 'One partner',
  rotating_partners: 'Rotating',
  solo: 'Solo',
  other: 'Other',
};

/** A single segment within a session */
export interface SessionSegment {
  id: string;
  type: SegmentType;
  duration_min: number;
  intensity?: SessionIntensity;
  tags: string[];
  notes?: string;

  /** Optional deeper detail — progressive disclosure */
  partner_format?: PartnerFormat;
  rounds?: number;
  round_length_min?: number;
  topic_worked?: string;
  positional_scenario?: string;

  /**
   * Future mapping to grappling map / control centre.
   * Not populated yet — insertion point for future integration.
   * When populated, links this segment to a specific technique/position
   * in the Lauburu Grappling Map.
   */
  map_ref?: {
    technique_key?: string;
    position_key?: string;
    node_id?: string;
  };
}

/** Default auto-detected grappling session structure */
export const DEFAULT_GRAPPLING_SEGMENTS: Omit<SessionSegment, 'id'>[] = [
  { type: 'technique', duration_min: 25, tags: [] },
  { type: 'positional', duration_min: 20, tags: [] },
  { type: 'live_rounds', duration_min: 25, tags: [] },
];

/** Generate segments with IDs */
export function createDefaultSegments(): SessionSegment[] {
  return DEFAULT_GRAPPLING_SEGMENTS.map((s, i) => ({
    ...s,
    id: `seg-${Date.now()}-${i}`,
  }));
}

// ---------------------------------------------------------------------------
// Session presets — common grappling class structures
// ---------------------------------------------------------------------------

export interface SessionPreset {
  id: string;
  label: string;
  description: string;
  segments: Omit<SessionSegment, 'id'>[];
  totalDuration: number;
}

export const SESSION_PRESETS: SessionPreset[] = [
  {
    id: 'class',
    label: 'Class',
    description: 'Technique → Positional → Live rounds',
    totalDuration: 90,
    segments: [
      { type: 'technique', duration_min: 30, intensity: 'light', tags: [] },
      { type: 'positional', duration_min: 20, intensity: 'moderate', tags: [] },
      { type: 'live_rounds', duration_min: 30, intensity: 'hard', tags: [] },
    ],
  },
  {
    id: 'wrestling_heavy',
    label: 'Wrestling Heavy',
    description: 'Takedowns → Wrestling → Live rounds',
    totalDuration: 75,
    segments: [
      { type: 'takedowns', duration_min: 20, intensity: 'moderate', tags: ['wrestling'] },
      { type: 'wrestling', duration_min: 25, intensity: 'hard', tags: ['wrestling'] },
      { type: 'live_rounds', duration_min: 20, intensity: 'hard', tags: [] },
    ],
  },
  {
    id: 'positional_heavy',
    label: 'Positional',
    description: 'Technique → Positional drilling → Flow',
    totalDuration: 60,
    segments: [
      { type: 'technique', duration_min: 20, intensity: 'light', tags: ['positional'] },
      { type: 'positional', duration_min: 25, intensity: 'moderate', tags: ['positional'] },
      { type: 'drilling', duration_min: 15, intensity: 'moderate', tags: [] },
    ],
  },
  {
    id: 'comp_prep',
    label: 'Comp Prep',
    description: 'Drilling → Hard rounds → Finisher',
    totalDuration: 90,
    segments: [
      { type: 'drilling', duration_min: 20, intensity: 'moderate', tags: ['comp-prep'] },
      { type: 'live_rounds', duration_min: 40, intensity: 'hard', tags: ['comp-prep'] },
      { type: 'conditioning_finisher', duration_min: 15, intensity: 'hard', tags: [] },
    ],
  },
  {
    id: 'open_mat',
    label: 'Open Mat',
    description: 'Free rolling / flow',
    totalDuration: 60,
    segments: [
      { type: 'open_mat', duration_min: 60, intensity: 'moderate', tags: ['flow'] },
    ],
  },
];

// ---------------------------------------------------------------------------
// Training session — now with optional segments
// ---------------------------------------------------------------------------

export interface TrainingSession {
  id: string;
  created_at: string;
  date: string;
  type: SessionType;
  intensity: SessionIntensity;
  duration_min: number;
  rounds?: number;
  rpe?: number;
  tags: string[];
  notes: string;
  persisted: boolean;

  /** Conditioning-specific detail (only when type === 'conditioning') */
  conditioning?: ConditioningDetail;

  /** Session segments — ordered parts of a mixed session (grappling) */
  segments?: SessionSegment[];

  /** Preset used, if any */
  preset_id?: string;
}

export interface TrainingSessionInput {
  date: string;
  type: SessionType;
  intensity: SessionIntensity;
  duration_min: number;
  rounds?: number;
  rpe?: number;
  tags?: string[];
  notes?: string;
  conditioning?: ConditioningDetail;
  segments?: SessionSegment[];
  preset_id?: string;
}
