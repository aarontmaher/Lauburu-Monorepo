/**
 * Manual training session entry types.
 *
 * These coexist with health-derived workouts in the unified model.
 * Source is always 'manual' — never confused with HealthKit/HC workouts.
 */

export type SessionType = 'class' | 'sparring' | 'drilling' | 'comp' | 'open_mat' | 'other';
export type SessionIntensity = 'light' | 'moderate' | 'hard';

/**
 * A manually logged training session.
 * Stored locally and optionally persisted to backend.
 */
export interface TrainingSession {
  /** Unique ID (uuid-style) */
  id: string;

  /** When entered */
  created_at: string;

  /** Session date (YYYY-MM-DD) */
  date: string;

  /** What kind of session */
  type: SessionType;

  /** Intensity level */
  intensity: SessionIntensity;

  /** Duration in minutes */
  duration_min: number;

  /** Number of rounds (sparring/comp) */
  rounds?: number;

  /** Rate of perceived exertion 1-10 */
  rpe?: number;

  /** Tags for categorization */
  tags: string[];

  /** Free-text notes */
  notes: string;

  /** Whether this has been persisted to backend */
  persisted: boolean;
}

/** Input shape for creating a new session (id and timestamps are auto-generated) */
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
  comp: 'Competition',
  open_mat: 'Open Mat',
  other: 'Other',
};

export const INTENSITY_LABELS: Record<SessionIntensity, string> = {
  light: 'Light',
  moderate: 'Moderate',
  hard: 'Hard',
};
