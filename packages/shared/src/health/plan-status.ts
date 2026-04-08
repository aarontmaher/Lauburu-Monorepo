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

/** Check if an actual session matches a planned session by type */
function sessionMatchesPlan(session: TrainingSession, planned: PlannedSession): boolean {
  // Direct type match
  if (session.type === planned.type) return true;
  // Conditioning subtype match
  if (session.type === 'conditioning' && planned.type === 'conditioning') return true;
  // Class/open_mat can match drilling/sparring/positional plans
  if (session.type === 'class' && ['drilling', 'sparring', 'positional', 'open_mat'].includes(planned.type)) return true;
  return false;
}
