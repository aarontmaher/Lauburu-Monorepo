/**
 * User coaching preferences + weekly training schedule.
 * NO-GI ONLY — no gi session types.
 */

// ---------------------------------------------------------------------------
// Weekly schedule
// ---------------------------------------------------------------------------

export type DayOfWeek = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';

export type ScheduleSessionType =
  | 'drilling'
  | 'sparring'
  | 'wrestling'
  | 'takedowns'
  | 'positional'
  | 'open_mat'
  | 'comp_prep'
  | 'conditioning'
  | 'other';

export const SCHEDULE_SESSION_LABELS: Record<ScheduleSessionType, string> = {
  drilling: 'Drilling',
  sparring: 'Sparring',
  wrestling: 'Wrestling',
  takedowns: 'Takedowns',
  positional: 'Positional',
  open_mat: 'Open Mat',
  comp_prep: 'Comp Prep',
  conditioning: 'Conditioning',
  other: 'Other',
};

export const DAY_LABELS: Record<DayOfWeek, string> = {
  mon: 'Mon',
  tue: 'Tue',
  wed: 'Wed',
  thu: 'Thu',
  fri: 'Fri',
  sat: 'Sat',
  sun: 'Sun',
};

export const DAYS_ORDER: DayOfWeek[] = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];

/** A single planned session slot within a day */
export interface PlannedSession {
  id: string;
  type: ScheduleSessionType;
  time?: string; // HH:MM or empty
  intensity?: 'light' | 'moderate' | 'hard';
  notes?: string;
  enabled: boolean;
}

/** A day's planned sessions */
export interface DayPlan {
  day: DayOfWeek;
  sessions: PlannedSession[];
}

/** Full weekly training schedule */
export type WeeklySchedule = Record<DayOfWeek, PlannedSession[]>;

export const EMPTY_SCHEDULE: WeeklySchedule = {
  mon: [],
  tue: [],
  wed: [],
  thu: [],
  fri: [],
  sat: [],
  sun: [],
};

/** Derive target_sessions_per_week from schedule */
export function countPlannedSessions(schedule: WeeklySchedule): number {
  return DAYS_ORDER.reduce(
    (n, day) => n + schedule[day].filter((s) => s.enabled).length,
    0,
  );
}

/** Get today's planned sessions */
export function getTodayPlan(schedule: WeeklySchedule): PlannedSession[] {
  const dayIndex = new Date().getDay(); // 0=Sun
  const dayMap: DayOfWeek[] = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
  return schedule[dayMap[dayIndex]].filter((s) => s.enabled);
}

/** Count planned training days (days with at least one enabled session) */
export function countTrainingDays(schedule: WeeklySchedule): number {
  return DAYS_ORDER.filter((day) => schedule[day].some((s) => s.enabled)).length;
}

/** Count planned rest days */
export function countRestDays(schedule: WeeklySchedule): number {
  return 7 - countTrainingDays(schedule);
}

// ---------------------------------------------------------------------------
// Coaching preferences
// ---------------------------------------------------------------------------

export interface CoachingPreferences {
  recovery_conservatism: 'conservative' | 'moderate' | 'aggressive';
  tone: 'direct' | 'encouraging' | 'analytical';
  comp_prep: boolean;
  hard_day_bias: 'train_through' | 'balanced' | 'err_on_rest';
  goal: 'general_fitness' | 'competition' | 'skill_development' | 'weight_management';

  /** Weekly training schedule (replaces target_sessions_per_week) */
  schedule: WeeklySchedule;
}

/** Backwards-compatible: derive target_sessions_per_week from schedule */
export function getTargetSessionsPerWeek(prefs: CoachingPreferences): number {
  return countPlannedSessions(prefs.schedule);
}

export const DEFAULT_SCHEDULE: WeeklySchedule = {
  mon: [{ id: 'mon-1', type: 'drilling', time: '18:00', enabled: true }],
  tue: [],
  wed: [{ id: 'wed-1', type: 'sparring', time: '18:00', enabled: true }],
  thu: [],
  fri: [{ id: 'fri-1', type: 'drilling', time: '18:00', enabled: true }],
  sat: [{ id: 'sat-1', type: 'open_mat', time: '11:00', enabled: true }],
  sun: [],
};

export const DEFAULT_PREFERENCES: CoachingPreferences = {
  recovery_conservatism: 'moderate',
  tone: 'direct',
  comp_prep: false,
  hard_day_bias: 'balanced',
  goal: 'skill_development',
  schedule: DEFAULT_SCHEDULE,
};
