/**
 * Manual training session entry types.
 * NO-GI ONLY — this app does not track gi training.
 *
 * These coexist with health-derived workouts in the unified model.
 * Source is always 'manual' — never confused with HealthKit/HC workouts.
 */

export type SessionType =
  | 'class'
  | 'sparring'
  | 'drilling'
  | 'wrestling'
  | 'comp'
  | 'open_mat'
  | 'other';

export type SessionIntensity = 'light' | 'moderate' | 'hard';

/**
 * A manually logged training session.
 * Stored locally and optionally persisted to backend.
 */
export interface TrainingSession {
  id: string;
  created_at: string;
  date: string; // YYYY-MM-DD
  type: SessionType;
  intensity: SessionIntensity;
  duration_min: number;
  rounds?: number;
  rpe?: number; // 1-10
  tags: string[];
  notes: string;
  persisted: boolean;
}

/** Input shape for creating a new session */
export interface TrainingSessionInput {
  date: string;
  type: SessionType;
  intensity: SessionIntensity;
  duration_min: number;
  rounds?: number;
  rpe?: number;
  tags?: string[];
  notes?: string;
}

export const SESSION_TYPE_LABELS: Record<SessionType, string> = {
  class: 'Class',
  sparring: 'Sparring',
  drilling: 'Drilling',
  wrestling: 'Wrestling',
  comp: 'Competition',
  open_mat: 'Open Mat',
  other: 'Other',
};

export const INTENSITY_LABELS: Record<SessionIntensity, string> = {
  light: 'Light',
  moderate: 'Moderate',
  hard: 'Hard',
};

/** No-gi + wrestling focused tag options */
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
