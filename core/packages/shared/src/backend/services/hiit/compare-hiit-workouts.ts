/**
 * HIIT workout progress comparison — deterministic comparison
 * of current vs previous session for the same template.
 * Pure function. No interpretation beyond raw deltas.
 */

import type { HIITWorkoutRecord, HIITProgressComparison } from '../../../types/hiit-workout';

export function compareHiitWorkouts(
  current: HIITWorkoutRecord,
  previous: HIITWorkoutRecord | null,
): HIITProgressComparison {
  const workSets = current.sets.filter((s) => s.type === 'work');
  const prevWorkSets = previous?.sets.filter((s) => s.type === 'work') ?? [];

  const setComparisons = workSets.map((set, i) => {
    const prev = prevWorkSets[i];
    return {
      setIndex: set.setIndex,
      currentWatts: set.avgWatts,
      previousWatts: prev?.avgWatts ?? null,
      deltaWatts: set.avgWatts != null && prev?.avgWatts != null ? set.avgWatts - prev.avgWatts : null,
      currentHrAvg: set.hrAvg,
      previousHrAvg: prev?.hrAvg ?? null,
      deltaHr: set.hrAvg != null && prev?.hrAvg != null ? set.hrAvg - prev.hrAvg : null,
      currentCalories: set.calories,
      previousCalories: prev?.calories ?? null,
    };
  });

  // Session-level deltas
  const avgWattsDelta = current.avgWatts != null && previous?.avgWatts != null
    ? current.avgWatts - previous.avgWatts : null;
  const peakWattsDelta = current.peakWatts != null && previous?.peakWatts != null
    ? current.peakWatts - previous.peakWatts : null;
  const avgHrDelta = current.avgHr != null && previous?.avgHr != null
    ? current.avgHr - previous.avgHr : null;
  const totalCaloriesDelta = current.totalCalories != null && previous?.totalCalories != null
    ? current.totalCalories - previous.totalCalories : null;

  // Fatigue: watts drop-off from first to last work set
  const firstWatts = workSets[0]?.avgWatts;
  const lastWatts = workSets[workSets.length - 1]?.avgWatts;
  const wattsDropOffPct = firstWatts != null && lastWatts != null && firstWatts > 0
    ? Math.round(((lastWatts - firstWatts) / firstWatts) * 100) : null;

  // HR drift: increase from first to last work set
  const firstHr = workSets[0]?.hrAvg;
  const lastHr = workSets[workSets.length - 1]?.hrAvg;
  const hrDriftPct = firstHr != null && lastHr != null && firstHr > 0
    ? Math.round(((lastHr - firstHr) / firstHr) * 100) : null;

  return {
    templateId: current.templateId ?? current.protocolFormat,
    currentWorkoutId: current.id,
    previousWorkoutId: previous?.id ?? null,
    setComparisons,
    avgWattsDelta,
    peakWattsDelta,
    avgHrDelta,
    totalCaloriesDelta,
    wattsDropOffPct,
    hrDriftPct,
  };
}
