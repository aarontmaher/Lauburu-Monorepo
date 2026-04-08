/**
 * Merge manual training sessions with health-derived daily metrics.
 *
 * Rules:
 * - Manual sessions are added as grappling_session on the matching date
 * - If the date already has workouts from HealthKit/HC, sessions coexist
 * - Manual sessions are also added to the workouts[] array with source='manual'
 * - No duplicate counting: source field distinguishes manual vs native
 * - The coaching engine sees both and can weight them differently
 */
import type { DailyMetrics, GrapplingSession, Workout } from '../types/health';
import type { TrainingSession } from '../types/training';
import { SESSION_TYPE_LABELS } from '../types/training';

/**
 * Merge manual training sessions into existing daily metrics.
 * Returns a new array — does not mutate the input.
 */
export function mergeTrainingSessions(
  days: DailyMetrics[],
  sessions: TrainingSession[],
): DailyMetrics[] {
  if (sessions.length === 0) return days;

  // Index existing days by date
  const dayMap = new Map<string, DailyMetrics>();
  for (const d of days) {
    dayMap.set(d.date, { ...d });
  }

  // Group sessions by date
  for (const session of sessions) {
    let day = dayMap.get(session.date);

    if (!day) {
      // Create a minimal day record for dates with only manual data
      day = {
        user_id: '', // filled by caller
        date: session.date,
        provider: 'manual' as any,
      };
      dayMap.set(session.date, day);
    }

    // Add as grappling_session (last one wins if multiple on same day)
    day.grappling_session = sessionToGrappling(session);

    // Add as a workout entry (always append — dedup by source_id)
    const existingWorkouts = day.workouts ?? [];
    const alreadyExists = existingWorkouts.some(
      (w) => w.source_id === `manual-${session.id}`,
    );
    if (!alreadyExists) {
      day.workouts = [
        ...existingWorkouts,
        sessionToWorkout(session),
      ];
    }
  }

  // Return sorted by date
  return Array.from(dayMap.values()).sort((a, b) =>
    a.date.localeCompare(b.date),
  );
}

function sessionToGrappling(s: TrainingSession): GrapplingSession {
  const sessionType = s.type === 'wrestling' ? 'wrestling' : 'bjj';
  return {
    type: sessionType,
    intensity: s.intensity,
    duration_min: s.duration_min,
    rounds: s.rounds,
    sparring: s.type === 'sparring' || s.type === 'comp' || s.type === 'wrestling',
    rpe: s.rpe,
    notes: s.notes || undefined,
  };
}

function sessionToWorkout(s: TrainingSession): Workout {
  const isWrestling = s.type === 'wrestling';
  return {
    type: isWrestling ? 'wrestling' : 'martial_arts',
    sport_label: isWrestling ? `Wrestling ${s.intensity}` : `No-gi ${SESSION_TYPE_LABELS[s.type] ?? s.type}`,
    source: 'manual',
    source_id: `manual-${s.id}`,
    duration_min: s.duration_min,
    is_grappling: true,
    notes: s.notes || undefined,
  };
}
