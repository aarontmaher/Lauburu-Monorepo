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
  | 'upper'
  | 'lower'
  | 'full_body'
  | 'pull'
  | 'push'
  | 'posterior_chain'
  | 'power'
  | 'hypertrophy'
  | 'other';

export const LIFTING_FOCUS_LABELS: Record<LiftingFocus, string> = {
  upper: 'Upper',
  lower: 'Lower',
  full_body: 'Full Body',
  pull: 'Pull',
  push: 'Push',
  posterior_chain: 'Posterior Chain',
  power: 'Power',
  hypertrophy: 'Hypertrophy',
  other: 'Other',
};

export type RespiratoryType = 'inspiratory' | 'expiratory' | 'mixed';

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
}

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

/** A single segment within a session */
export interface SessionSegment {
  id: string;
  type: SegmentType;
  duration_min: number;
  intensity?: SessionIntensity;
  tags: string[];
  notes?: string;
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
