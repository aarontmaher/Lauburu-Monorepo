/**
 * Compare planned schedule against actual sessions for a given day.
 * Produces a status for each planned session and an overall day summary.
 */
import type { PlannedSession, WeeklySchedule, DayOfWeek } from '../types/preferences';
import type { TrainingSession } from '../types/training';

export type PlannedSessionStatus = 'completed' | 'missed' | 'upcoming';

export interface PlannedWithStatus {
  planned: PlannedSession;
  status: PlannedSessionStatus;
  /** The actual session that matched, if any */
  matchedSession?: TrainingSession;
}

export type DayPlanStatus = 'on_plan' | 'under_plan' | 'over_plan' | 'rest_day' | 'no_plan';

export interface DayPlanSummary {
  date: string;
  day: DayOfWeek;
  status: DayPlanStatus;
  planned: PlannedWithStatus[];
  unplannedSessions: TrainingSession[];
  completedCount: number;
  plannedCount: number;
  totalActual: number;
}

const DAY_MAP: DayOfWeek[] = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];

export function getDayOfWeek(date: string): DayOfWeek {
  const d = new Date(date + 'T12:00:00');
  return DAY_MAP[d.getDay()];
}

/**
 * Build plan-vs-actual summary for a specific date.
 */
export function buildDayPlanSummary(
  date: string,
  schedule: WeeklySchedule,
  sessions: TrainingSession[],
  currentHour: number = new Date().getHours(),
): DayPlanSummary {
  const dow = getDayOfWeek(date);
  const planned = schedule[dow].filter((s) => s.enabled);
  const daySessions = sessions.filter((s) => s.date === date);

  if (planned.length === 0 && daySessions.length === 0) {
    return {
      date, day: dow, status: 'rest_day',
      planned: [], unplannedSessions: [], completedCount: 0, plannedCount: 0, totalActual: 0,
    };
  }

  if (planned.length === 0 && daySessions.length > 0) {
    return {
      date, day: dow, status: 'over_plan',
      planned: [], unplannedSessions: daySessions,
      completedCount: 0, plannedCount: 0, totalActual: daySessions.length,
    };
  }

  // Match planned sessions to actual sessions by type
  const matched = new Set<string>();
  const plannedWithStatus: PlannedWithStatus[] = planned.map((p) => {
    // Find a matching actual session (same type, not already matched)
    const match = daySessions.find(
      (s) => !matched.has(s.id) && sessionMatchesPlan(s, p),
    );
    if (match) {
      matched.add(match.id);
      return { planned: p, status: 'completed' as const, matchedSession: match };
    }

    // Check if session time has passed
    const plannedHour = p.time ? parseInt(p.time.split(':')[0], 10) : 23;
    if (currentHour > plannedHour + 1) {
      return { planned: p, status: 'missed' as const };
    }
    return { planned: p, status: 'upcoming' as const };
  });

  const unplanned = daySessions.filter((s) => !matched.has(s.id));
  const completedCount = plannedWithStatus.filter((p) => p.status === 'completed').length;

  let status: DayPlanStatus;
  if (completedCount === planned.length && unplanned.length === 0) {
    status = 'on_plan';
  } else if (completedCount + unplanned.length > planned.length) {
    status = 'over_plan';
  } else if (completedCount < planned.length) {
    status = 'under_plan';
  } else {
    status = 'on_plan';
  }

  return {
    date, day: dow, status,
    planned: plannedWithStatus,
    unplannedSessions: unplanned,
    completedCount,
    plannedCount: planned.length,
    totalActual: daySessions.length,
  };
}

/** Check if an actual session matches a planned session under the new
 *  coarser taxonomy: grappling / conditioning / recovery / other. */
function sessionMatchesPlan(session: TrainingSession, planned: PlannedSession): boolean {
  // Grappling schedule slots match any mat session type from Train logging
  if (planned.type === 'grappling') {
    if (['class', 'sparring', 'drilling', 'wrestling', 'comp', 'open_mat'].includes(session.type)) {
      // If the plan has a specific grappling subtype, prefer a closer match
      if (planned.grappling_subtype === 'wrestling') return session.type === 'wrestling';
      if (planned.grappling_subtype === 'open_mat') return session.type === 'open_mat';
      if (planned.grappling_subtype === 'comp_prep') return session.type === 'comp';
      // jiu_jitsu / class / no-subtype → any grappling type counts
      return true;
    }
    return false;
  }
  // Conditioning plan matches any conditioning session
  if (planned.type === 'conditioning') return session.type === 'conditioning';
  // Recovery plan matches a conditioning session with recovery subtype, or
  // any other session logged at light intensity
  if (planned.type === 'recovery') {
    if (
      session.type === 'conditioning' &&
      session.conditioning?.subtype &&
      ['recovery_cardio', 'mobility', 'recovery_breathing'].includes(
        session.conditioning.subtype,
      )
    ) {
      return true;
    }
    return session.intensity === 'light';
  }
  // Other plan never auto-matches; user reconciles manually
  return false;
}
