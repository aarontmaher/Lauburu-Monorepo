import type { HealthProvider, ReadinessState } from '../constants/enums';

/** Workout entry — matches website workout shape */
export interface Workout {
  type: string;
  duration_min: number;
  strain?: number;
  avg_hr?: number;
  max_hr?: number;
  is_grappling: boolean;
}

/** Grappling session details */
export interface GrapplingSession {
  type: string;
  intensity: string;
  duration_min: number;
  rounds?: number;
  techniques_practiced?: string[];
  positions_worked?: string[];
  rpe?: number;
  notes?: string;
}

/** Nutrition data (Cronometer-compatible) */
export interface Nutrition {
  calories?: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
  water_ml?: number;
}

/** Subjective wellness */
export interface SubjectiveData {
  mood?: number; // 1-5
  perceived_exertion?: number; // 1-10
  energy?: number; // 1-5
  notes?: string;
}

/** Substance tracking */
export interface SubstanceEvent {
  name: string;
  amount: number;
  unit: string;
  time: string;
  category: string;
}

/**
 * Canonical daily metrics shape — matches website daily_metrics exactly.
 * All health providers normalize to this shape.
 */
export interface DailyMetrics {
  user_id: string;
  date: string; // YYYY-MM-DD
  provider: HealthProvider;
  recovery_score?: number; // 0-100
  hrv_ms?: number;
  resting_hr?: number;
  sleep_hours?: number;
  sleep_performance_pct?: number; // 0-100
  daily_strain?: number; // 0-100
  readiness_state?: ReadinessState;
  workouts?: Workout[];
  grappling_session?: GrapplingSession;
  nutrition?: Nutrition;
  subjective?: SubjectiveData;
  substances?: SubstanceEvent[];
  last_updated?: string;
}

/**
 * Row shape from Supabase daily_metrics table.
 * Subset of DailyMetrics — the DB stores flattened fields.
 */
export interface DailyMetricsRow {
  user_id: string;
  date: string;
  provider: string;
  recovery_score: number | null;
  hrv_ms: number | null;
  resting_hr: number | null;
  sleep_hours: number | null;
  sleep_performance_pct: number | null;
  daily_strain: number | null;
  readiness_label: string | null;
  last_updated: string;
}
