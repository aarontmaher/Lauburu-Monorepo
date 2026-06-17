import type { HealthProvider, ReadinessState } from '../constants/enums';

/**
 * Workout entry — normalized shape consumed by both website and AI layer.
 *
 * Design notes:
 * - HealthKit / Health Connect provide the base fields reliably.
 * - Richer workout apps (ErgZone, intervals.icu, Garmin) may provide
 *   detailed interval/structure data later via `detail`.
 * - Apple Health does NOT preserve full interval structure from devices
 *   like Assault Bike — only summary metrics. Model this honestly.
 * - `detail` is a future-proof extension point, not populated by
 *   HealthKit/HC. Leave null until a richer source is wired.
 */
export interface Workout {
  // Identity
  type: string;
  sport_label?: string;
  source?: string; // e.g. 'Apple Watch', 'WHOOP', 'ErgZone'

  // Timing
  start_time?: string; // ISO8601
  end_time?: string; // ISO8601
  duration_min: number;

  // Effort
  strain?: number; // WHOOP 0-21
  avg_hr?: number;
  max_hr?: number;
  calories?: number;

  // Movement
  steps?: number;
  distance_m?: number;

  // Classification
  is_grappling: boolean;

  // Notes / metadata from source
  notes?: string;
  source_id?: string; // upstream workout ID for dedup

  /**
   * Extended workout detail — populated by richer providers later.
   * HealthKit/HC will NOT fill this. It exists so the schema does not
   * need a breaking change when ErgZone, intervals.icu, or a coach
   * platform starts providing structured interval data.
   *
   * When populated, `intervals` contains the work/rest block sequence.
   * Machine-specific metrics (watts, pace, cadence) live per-interval.
   */
  detail?: WorkoutDetail;
}

/**
 * Extended workout structure for richer providers.
 * Not populated by HealthKit or Health Connect — they only provide summaries.
 * Future sources (ErgZone, Garmin, intervals.icu) can populate this.
 */
export interface WorkoutDetail {
  /** Ordered list of work/rest intervals */
  intervals?: WorkoutInterval[];
  /** Machine or modality (e.g. 'assault_bike', 'rower', 'ski_erg') */
  machine_type?: string;
  /** Summary power in watts (if available from device) */
  avg_watts?: number;
  max_watts?: number;
  /** Summary pace (seconds per unit, e.g. /500m for rower) */
  avg_pace_s?: number;
  /** Summary cadence (RPM) */
  avg_cadence?: number;
  /** Raw payload from upstream — preserved for AI training without schema loss */
  raw_payload?: Record<string, unknown>;
}

/**
 * Single interval within a structured workout.
 * Supports work/rest blocks with per-interval metrics.
 */
export interface WorkoutInterval {
  type: 'work' | 'rest' | 'warmup' | 'cooldown';
  duration_s: number;
  /** Heart rate */
  avg_hr?: number;
  max_hr?: number;
  /** Power (watts) */
  avg_watts?: number;
  max_watts?: number;
  /** Pace (seconds per distance unit, e.g. /500m) */
  avg_pace_s?: number;
  /** Cadence (RPM) */
  avg_cadence?: number;
  /** Calories burned in this interval */
  calories?: number;
  /** Distance in meters */
  distance_m?: number;
}

/** Grappling session details */
export interface GrapplingSession {
  type: string;
  intensity: string;
  duration_min: number;
  rounds?: number;
  sparring?: boolean;
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
 * This is also the shape the AI layer consumes via deriveFeatures().
 */
export interface DailyMetrics {
  user_id: string;
  date: string; // YYYY-MM-DD
  provider: HealthProvider;
  provider_record_id?: string;

  // Recovery / readiness
  recovery_score?: number; // 0-100
  readiness_label?: string; // 'high' | 'moderate' | 'low' | 'unknown'
  hrv_ms?: number;
  resting_hr?: number;

  // Sleep
  sleep_hours?: number;
  sleep_performance_pct?: number; // 0-100
  sleep_efficiency_pct?: number;
  sws_hours?: number; // slow-wave sleep
  rem_hours?: number;
  respiratory_rate?: number;

  // Strain / activity
  daily_strain?: number; // 0-21 for WHOOP
  active_calories?: number;
  step_count?: number;

  // Biometrics
  spo2_pct?: number;
  skin_temp_c?: number;
  weight_kg?: number;

  // Structured data
  workouts?: Workout[];
  grappling_session?: GrapplingSession;
  nutrition?: Nutrition;
  subjective?: SubjectiveData;
  substances?: SubstanceEvent[];

  // Metadata
  data_source?: string;
  imported_at?: string;
  last_updated?: string;
}

/**
 * Row shape from Supabase daily_metrics table.
 */
export interface DailyMetricsRow {
  user_id: string;
  date: string;
  provider: string;
  recovery_score: number | null;
  readiness_label: string | null;
  hrv_ms: number | null;
  resting_hr: number | null;
  sleep_hours: number | null;
  sleep_performance_pct: number | null;
  sleep_efficiency_pct: number | null;
  sws_hours: number | null;
  rem_hours: number | null;
  respiratory_rate: number | null;
  daily_strain: number | null;
  step_count: number | null;
  active_calories: number | null;
  spo2_pct: number | null;
  skin_temp_c: number | null;
  weight_kg: number | null;
  workouts: unknown; // JSONB
  grappling_session: unknown; // JSONB
  subjective: unknown; // JSONB
  substances: unknown; // JSONB
  nutrition: unknown; // JSONB
  last_updated: string;
}

// ---------------------------------------------------------------------------
// Health Service Interface — platform-agnostic contract
// ---------------------------------------------------------------------------

/** Permission status for a single metric type */
export type PermissionStatus =
  | 'not_determined'
  | 'authorized'
  | 'denied'
  | 'unavailable';

/** Health data types we request from native platforms */
export type HealthMetricType =
  | 'heart_rate'
  | 'resting_heart_rate'
  | 'hrv'
  | 'sleep'
  | 'steps'
  | 'active_calories'
  | 'workouts';

/** Result of a permission check/request */
export interface HealthPermissions {
  available: boolean; // HealthKit/HC available on device
  permissions: Record<HealthMetricType, PermissionStatus>;
}

/** Raw health sample before normalization */
export interface RawHealthSample {
  metric: HealthMetricType;
  value: number;
  unit: string;
  startDate: string; // ISO8601
  endDate: string; // ISO8601
  source?: string;
}

/** Raw workout from native platform */
export interface RawWorkoutSample {
  type: string; // platform-specific workout type
  name: string; // human-readable name
  duration_min: number;
  calories?: number;
  avg_hr?: number;
  max_hr?: number;
  steps?: number;
  distance_m?: number;
  startDate: string;
  endDate: string;
  source?: string;
  source_id?: string; // platform-specific ID for dedup
}

/** Raw sleep session from native platform */
export interface RawSleepSample {
  stage: string; // 'asleep' | 'deep' | 'rem' | 'light' | 'awake' | 'in_bed'
  startDate: string;
  endDate: string;
  source?: string;
}

/** Date range for queries */
export interface DateRange {
  start: Date;
  end: Date;
}

/**
 * Platform-agnostic health service interface.
 * Implemented separately for iOS (HealthKit) and Android (Health Connect).
 */
export interface IHealthService {
  /** Check if health data is available on this device */
  isAvailable(): Promise<boolean>;

  /** Check current permission status for all metric types */
  checkPermissions(): Promise<HealthPermissions>;

  /** Request read permissions for the metric slice */
  requestPermissions(): Promise<HealthPermissions>;

  /** Fetch raw health samples for a date range */
  fetchSamples(
    metric: HealthMetricType,
    range: DateRange,
  ): Promise<RawHealthSample[]>;

  /** Fetch workout sessions for a date range */
  fetchWorkouts(range: DateRange): Promise<RawWorkoutSample[]>;

  /** Fetch sleep sessions for a date range */
  fetchSleep(range: DateRange): Promise<RawSleepSample[]>;
}

// ---------------------------------------------------------------------------
// AI readiness: fields the intelligence layer needs
// ---------------------------------------------------------------------------

/**
 * Derived features for the AI pipeline.
 * Matches website's deriveFeatures() output shape.
 */
export interface DerivedFeatures {
  today_recovery: number | null;
  today_readiness: string;
  today_strain: number | null;
  today_hrv: number | null;
  today_sleep: number | null;

  baseline_recovery_mean: number | null;
  baseline_hrv_mean: number | null;
  baseline_strain_mean: number | null;
  baseline_sleep_mean: number | null;

  last_7d_recovery_mean: number | null;
  last_7d_strain_mean: number | null;

  workouts: number;
  grappling_sessions: number;
  sleep_detail: boolean;

  recovery_trend: 'improving' | 'declining' | 'stable';
  strain_trend: 'increasing' | 'decreasing' | 'stable';

  missing: {
    grappling_sessions: boolean;
    grappling_workout: boolean;
    sleep_data: boolean;
    sleep_detail: boolean;
    strain_data: boolean;
    hrv_data: boolean;
    workout_detail: boolean;
    subjective_data: boolean;
    insufficient_history: boolean;
  };

  provenance: string[];
}

/**
 * Provider connection state — matches Supabase provider_connections table.
 */
export interface ProviderConnection {
  provider: HealthProvider;
  status: 'connected' | 'manual_import' | 'not_connected';
  connection_mode?: string;
  last_sync_at?: string;
  last_error?: string;
  sync_failed_count?: number;
}
