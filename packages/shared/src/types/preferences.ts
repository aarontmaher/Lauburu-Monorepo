/**
 * User coaching preferences + weekly training schedule.
 * NO-GI ONLY — no gi session types.
 */

// ---------------------------------------------------------------------------
// Weekly schedule
// ---------------------------------------------------------------------------

export type DayOfWeek = 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun';

/**
 * Top-level weekly schedule categories.
 *
 * Deliberately coarse: schedule is for broad weekly planning, not for
 * logging session contents. Granular things like sparring, takedowns,
 * and positional drilling belong in session segment detail when logged,
 * not on the calendar.
 *
 * Grappling is the parent category for all mat sessions. When the user
 * picks grappling, an optional `grappling_subtype` gives the flavour
 * (Jiu Jitsu / Wrestling / Open Mat / Comp Prep / Normal Class) so the
 * calendar stays useful without exploding the top-level list.
 */
export type ScheduleSessionType =
  | 'grappling'
  | 'conditioning'
  | 'recovery'
  | 'other';

/** Subtype for grappling-category sessions. Optional. */
export type GrapplingScheduleSubtype =
  | 'jiu_jitsu'
  | 'wrestling'
  | 'open_mat'
  | 'comp_prep'
  | 'class';

export const SCHEDULE_SESSION_LABELS: Record<ScheduleSessionType, string> = {
  grappling: 'Grappling',
  conditioning: 'Conditioning',
  recovery: 'Recovery',
  other: 'Other',
};

export const GRAPPLING_SCHEDULE_SUBTYPE_LABELS: Record<GrapplingScheduleSubtype, string> = {
  jiu_jitsu: 'Jiu Jitsu',
  wrestling: 'Wrestling',
  open_mat: 'Open Mat',
  comp_prep: 'Comp Prep',
  class: 'Normal Class',
};

/** Ordered for UI picker presentation. */
export const GRAPPLING_SCHEDULE_SUBTYPES: GrapplingScheduleSubtype[] = [
  'jiu_jitsu',
  'wrestling',
  'open_mat',
  'comp_prep',
  'class',
];

/**
 * Legacy schedule type strings we used to persist. Kept here as the
 * authoritative migration table for rows loaded from older storage.
 */
const LEGACY_TO_NEW: Record<
  string,
  { type: ScheduleSessionType; grappling_subtype?: GrapplingScheduleSubtype }
> = {
  drilling: { type: 'grappling', grappling_subtype: 'class' },
  sparring: { type: 'grappling', grappling_subtype: 'jiu_jitsu' },
  wrestling: { type: 'grappling', grappling_subtype: 'wrestling' },
  takedowns: { type: 'grappling', grappling_subtype: 'wrestling' },
  positional: { type: 'grappling', grappling_subtype: 'jiu_jitsu' },
  open_mat: { type: 'grappling', grappling_subtype: 'open_mat' },
  comp_prep: { type: 'grappling', grappling_subtype: 'comp_prep' },
};

/**
 * Migrate a single schedule row from the old flat taxonomy into the
 * new grappling-parent + subtype shape. Safe to call on already-migrated
 * rows (they pass through unchanged). Loss-free where possible.
 */
export function migrateLegacyPlannedSession(
  raw: Record<string, any>,
): { type: ScheduleSessionType; grappling_subtype?: GrapplingScheduleSubtype } {
  const t = String(raw?.type ?? '');
  if (t in LEGACY_TO_NEW) {
    return LEGACY_TO_NEW[t];
  }
  // Already-new values pass through. Anything else becomes 'other'.
  if (t === 'grappling' || t === 'conditioning' || t === 'recovery' || t === 'other') {
    return {
      type: t,
      grappling_subtype: raw?.grappling_subtype as GrapplingScheduleSubtype | undefined,
    };
  }
  return { type: 'other' };
}

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
  /** Only meaningful when type === 'grappling'. Optional. */
  grappling_subtype?: GrapplingScheduleSubtype;
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
  mon: [{ id: 'mon-1', type: 'grappling', grappling_subtype: 'class', time: '18:00', enabled: true }],
  tue: [],
  wed: [{ id: 'wed-1', type: 'grappling', grappling_subtype: 'jiu_jitsu', time: '18:00', enabled: true }],
  thu: [],
  fri: [{ id: 'fri-1', type: 'grappling', grappling_subtype: 'class', time: '18:00', enabled: true }],
  sat: [{ id: 'sat-1', type: 'grappling', grappling_subtype: 'open_mat', time: '11:00', enabled: true }],
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
