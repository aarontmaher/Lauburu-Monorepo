/**
 * Per-user trend candidate detection for the first-run backlog
 * analysis. Pure function. No network calls. No cross-athlete reads.
 *
 * Safety invariants enforced here (not by the caller):
 *
 *   - Readiness-style trends (recovery, HRV, strain) are ONLY emitted
 *     when direct user-owned WHOOP data is part of the input. The
 *     caller passes `hasDirectWhoopData` as an explicit gate — we
 *     refuse to synthesise readiness patterns from Health Connect or
 *     Polar-via-HC data alone.
 *   - Confidence is grounded in observation count. A single week is
 *     never 'high' even if every day lines up.
 *   - `eligibleForMemoryProposal` requires confidence ≥ medium AND at
 *     least 14 days of supporting observations AND the trend kind is
 *     not a readiness claim.
 */

import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';
import type {
  BacklogTrendCandidate,
  TrendKind,
} from '../../contracts/backlog-analysis.types';
import type { HIITWorkoutRecord } from '../../../types/hiit-workout';

export interface FindTrendCandidatesInput {
  athleteId: string;
  windowStart: string;
  windowEnd: string;
  normalizedDays: NormalizedDailyMetrics[];
  hiitSessions: HIITWorkoutRecord[];
  /**
   * True iff the normalized days include fresh DIRECT user-owned WHOOP
   * fields (recovery, HRV, strain). Polar-via-HC and generic Health
   * Connect never flip this flag regardless of their own freshness.
   */
  hasDirectWhoopData: boolean;
  /** True if the normalized days include grappling/session counts. */
  hasGrapplingSessions: boolean;
}

let _counter = 0;
function newId(kind: TrendKind, windowStart: string): string {
  return `trend_${kind}_${windowStart}_${Date.now()}_${++_counter}`;
}

const READINESS_KINDS: Set<TrendKind> = new Set([
  'recovery_trend',
  'hrv_trend',
  'strain_trend',
]);

function isReadinessKind(kind: TrendKind): boolean {
  return READINESS_KINDS.has(kind);
}

function confidenceFromObservations(count: number, span: number): 'low' | 'medium' | 'high' {
  if (count < 5 || span < 7) return 'low';
  if (count < 14 || span < 14) return 'medium';
  return 'high';
}

function stdev(values: number[]): number {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function spanDays(days: NormalizedDailyMetrics[]): number {
  if (days.length === 0) return 0;
  const start = new Date(days[0].date).getTime();
  const end = new Date(days[days.length - 1].date).getTime();
  return Math.round((end - start) / 86_400_000) + 1;
}

export function findTrendCandidates(input: FindTrendCandidatesInput): BacklogTrendCandidate[] {
  const now = new Date().toISOString();
  const { athleteId, windowStart, windowEnd, normalizedDays, hiitSessions } = input;
  const candidates: BacklogTrendCandidate[] = [];

  const sortedDays = [...normalizedDays].sort((a, b) => a.date.localeCompare(b.date));
  const span = spanDays(sortedDays);

  // Helper to push, honouring the readiness gate.
  const push = (candidate: Omit<BacklogTrendCandidate, 'id' | 'athleteId' | 'createdAt' | 'eligibleForMemoryProposal'>) => {
    if (isReadinessKind(candidate.kind) && !input.hasDirectWhoopData) return;
    const eligible =
      !isReadinessKind(candidate.kind) &&
      (candidate.confidence === 'medium' || candidate.confidence === 'high') &&
      candidate.observationCount >= 14;
    candidates.push({
      id: newId(candidate.kind, windowStart),
      athleteId,
      createdAt: now,
      eligibleForMemoryProposal: eligible,
      ...candidate,
    });
  };

  // 1. Sleep consistency
  const sleepHours = sortedDays
    .map((d) => d.totalSleepHours)
    .filter((v): v is number => typeof v === 'number');
  if (sleepHours.length >= 5) {
    const avg = mean(sleepHours);
    const sd = stdev(sleepHours);
    const cv = avg > 0 ? sd / avg : 0;
    const confidence = confidenceFromObservations(sleepHours.length, span);
    push({
      kind: 'sleep_consistency',
      statement:
        cv < 0.1
          ? `Sleep duration is consistent: averaging ${avg.toFixed(1)}h (±${sd.toFixed(1)}h) across ${sleepHours.length} logged nights.`
          : `Sleep duration varies widely: averaging ${avg.toFixed(1)}h with spread of ±${sd.toFixed(1)}h across ${sleepHours.length} logged nights.`,
      evidenceFields: ['totalSleepHours'],
      windowStart,
      windowEnd,
      observationCount: sleepHours.length,
      confidence,
      missingnessNote: sleepHours.length < 14 ? 'More nights logged will strengthen this pattern.' : null,
    });
  }

  // 2. Training frequency (workout count / span weeks)
  const workoutDays = sortedDays.filter((d) => (d.workoutCount ?? 0) > 0);
  if (workoutDays.length >= 3) {
    const weeks = Math.max(1, span / 7);
    const perWeek = workoutDays.length / weeks;
    const confidence = confidenceFromObservations(workoutDays.length, span);
    push({
      kind: 'training_frequency',
      statement: `Training activity on ${workoutDays.length} of ${sortedDays.length} days (≈${perWeek.toFixed(1)}/week).`,
      evidenceFields: ['workoutCount'],
      windowStart,
      windowEnd,
      observationCount: workoutDays.length,
      confidence,
      missingnessNote: workoutDays.length < 14 ? 'Add more logged workouts to sharpen the pattern.' : null,
    });
  }

  // 3. HIIT frequency (from session logs)
  if (hiitSessions.length > 0) {
    const weeks = Math.max(1, span / 7);
    const hiitPerWeek = hiitSessions.length / weeks;
    const confidence = confidenceFromObservations(hiitSessions.length, span);
    push({
      kind: 'hiit_frequency',
      statement: `Logged ${hiitSessions.length} HIIT session${hiitSessions.length === 1 ? '' : 's'} in the last ${span} days (≈${hiitPerWeek.toFixed(1)}/week).`,
      evidenceFields: ['hiit_session_count'],
      windowStart,
      windowEnd,
      observationCount: hiitSessions.length,
      confidence,
      missingnessNote: hiitSessions.length < 6 ? 'Short HIIT history — pattern will harden after more sessions.' : null,
    });
  }

  // 4. Zone 2 vs HIIT balance — require at least 2 workouts AND at least 1 HIIT.
  if (workoutDays.length >= 4 && hiitSessions.length >= 1) {
    const hiitShare = hiitSessions.length / (workoutDays.length + hiitSessions.length);
    const balance = hiitShare >= 0.5 ? 'HIIT-heavy' : hiitShare >= 0.25 ? 'balanced' : 'zone-2-heavy';
    const confidence = confidenceFromObservations(workoutDays.length + hiitSessions.length, span);
    push({
      kind: 'zone2_vs_hiit_balance',
      statement: `Training mix reads ${balance}: ${hiitSessions.length} HIIT vs ${workoutDays.length} other workouts.`,
      evidenceFields: ['workoutCount', 'hiit_session_count'],
      windowStart,
      windowEnd,
      observationCount: workoutDays.length + hiitSessions.length,
      confidence,
      missingnessNote: span < 14 ? 'Short window — balance may shift across a full month.' : null,
    });
  }

  // 5. Grappling session load (only if any grappling sessions logged)
  const grapplingCounts = sortedDays.map((d) => d.grapplingSessionCount ?? 0);
  const grapplingTotal = grapplingCounts.reduce((a, b) => a + b, 0);
  if (input.hasGrapplingSessions && grapplingTotal > 0) {
    const weeks = Math.max(1, span / 7);
    const confidence = confidenceFromObservations(grapplingTotal, span);
    push({
      kind: 'grappling_session_load',
      statement: `${grapplingTotal} grappling session${grapplingTotal === 1 ? '' : 's'} logged in ${span} days (≈${(grapplingTotal / weeks).toFixed(1)}/week).`,
      evidenceFields: ['grapplingSessionCount'],
      windowStart,
      windowEnd,
      observationCount: grapplingTotal,
      confidence,
      missingnessNote: grapplingTotal < 4 ? 'Light grappling history — tracking will sharpen with more sessions.' : null,
    });
  }

  // 6. Resting HR trend (context only, NOT gated as readiness)
  const rhrDays = sortedDays.filter((d) => typeof d.restingHrBpm === 'number');
  if (rhrDays.length >= 5) {
    const first = rhrDays.slice(0, Math.floor(rhrDays.length / 2)).map((d) => d.restingHrBpm as number);
    const second = rhrDays.slice(Math.floor(rhrDays.length / 2)).map((d) => d.restingHrBpm as number);
    const firstMean = mean(first);
    const secondMean = mean(second);
    const delta = secondMean - firstMean;
    const direction = delta > 1 ? 'drifting upward' : delta < -1 ? 'trending downward' : 'stable';
    const confidence = confidenceFromObservations(rhrDays.length, span);
    push({
      kind: 'heart_rate_resting_trend',
      statement: `Resting heart rate is ${direction} across ${rhrDays.length} observations (${firstMean.toFixed(0)} → ${secondMean.toFixed(0)} bpm).`,
      evidenceFields: ['restingHrBpm'],
      windowStart,
      windowEnd,
      observationCount: rhrDays.length,
      confidence,
      missingnessNote: rhrDays.length < 14 ? 'Contextual only — not a readiness claim.' : 'Context only; not a direct readiness signal.',
    });
  }

  // 7. Workout duration trend
  const durations = sortedDays.map((d) => d.workoutMinutesTotal ?? 0).filter((v) => v > 0);
  if (durations.length >= 4) {
    const avg = mean(durations);
    const confidence = confidenceFromObservations(durations.length, span);
    push({
      kind: 'workout_duration_trend',
      statement: `Average workout duration is ${avg.toFixed(0)} minutes across ${durations.length} logged days.`,
      evidenceFields: ['workoutMinutesTotal'],
      windowStart,
      windowEnd,
      observationCount: durations.length,
      confidence,
      missingnessNote: null,
    });
  }

  // 8 + 9 + 10. Nutrition consistency / protein / calories coverage
  const nutritionDays = sortedDays.filter((d) => d.nutritionCoverage && d.nutritionCoverage !== 'none');
  if (nutritionDays.length >= 3) {
    const proteinDays = nutritionDays.filter((d) => typeof d.nutritionProteinGrams === 'number');
    const calorieDays = nutritionDays.filter((d) => typeof d.nutritionCalories === 'number');
    const coverageRate = nutritionDays.length / sortedDays.length;
    const confidence = confidenceFromObservations(nutritionDays.length, span);

    push({
      kind: 'nutrition_consistency',
      statement: `Nutrition logged on ${nutritionDays.length} of ${sortedDays.length} days (${(coverageRate * 100).toFixed(0)}%).`,
      evidenceFields: ['nutritionCoverage'],
      windowStart,
      windowEnd,
      observationCount: nutritionDays.length,
      confidence,
      missingnessNote: coverageRate < 0.5 ? 'Intermittent logging — pattern quality limited.' : null,
    });

    if (proteinDays.length >= 3) {
      const avg = mean(proteinDays.map((d) => d.nutritionProteinGrams as number));
      push({
        kind: 'nutrition_protein_coverage',
        statement: `Average logged protein: ${avg.toFixed(0)}g over ${proteinDays.length} days.`,
        evidenceFields: ['nutritionProteinGrams'],
        windowStart,
        windowEnd,
        observationCount: proteinDays.length,
        confidence,
        missingnessNote: proteinDays.length < 14 ? 'More logged meals will sharpen this.' : null,
      });
    }

    if (calorieDays.length >= 3) {
      const avg = mean(calorieDays.map((d) => d.nutritionCalories as number));
      push({
        kind: 'nutrition_calories_coverage',
        statement: `Average logged calories: ${avg.toFixed(0)} kcal over ${calorieDays.length} days.`,
        evidenceFields: ['nutritionCalories'],
        windowStart,
        windowEnd,
        observationCount: calorieDays.length,
        confidence,
        missingnessNote: calorieDays.length < 14 ? 'More logged meals will sharpen this.' : null,
      });
    }
  }

  // 11. Logging completeness — tells user how much they've recorded.
  const anyFieldDays = sortedDays.filter((d) => d.presentFields && d.presentFields.length > 0);
  if (anyFieldDays.length > 0) {
    const avgFields = mean(anyFieldDays.map((d) => d.presentFields.length));
    const confidence = confidenceFromObservations(anyFieldDays.length, span);
    push({
      kind: 'logging_completeness',
      statement: `Average ${avgFields.toFixed(1)} fields logged per day across ${anyFieldDays.length} days in the window.`,
      evidenceFields: ['presentFields'],
      windowStart,
      windowEnd,
      observationCount: anyFieldDays.length,
      confidence,
      missingnessNote: 'Raw logging completeness — helps calibrate how much Coach can rely on trends.',
    });
  }

  // 12, 13, 14. Readiness-gated trends. Only enabled when direct WHOOP
  // data is present for this athlete. Polar-via-HC and generic HC
  // never cross this gate regardless of their own freshness.
  if (input.hasDirectWhoopData) {
    const recoveryDays = sortedDays.filter((d) => typeof d.recoveryScore === 'number');
    if (recoveryDays.length >= 5) {
      const confidence = confidenceFromObservations(recoveryDays.length, span);
      const avg = mean(recoveryDays.map((d) => d.recoveryScore as number));
      push({
        kind: 'recovery_trend',
        statement: `Average WHOOP recovery: ${avg.toFixed(0)}% across ${recoveryDays.length} days.`,
        evidenceFields: ['recoveryScore'],
        windowStart,
        windowEnd,
        observationCount: recoveryDays.length,
        confidence,
        missingnessNote: null,
      });
    }

    const hrvDays = sortedDays.filter((d) => typeof d.hrvMs === 'number');
    if (hrvDays.length >= 5) {
      const confidence = confidenceFromObservations(hrvDays.length, span);
      const avg = mean(hrvDays.map((d) => d.hrvMs as number));
      push({
        kind: 'hrv_trend',
        statement: `Average HRV: ${avg.toFixed(0)} ms across ${hrvDays.length} days.`,
        evidenceFields: ['hrvMs'],
        windowStart,
        windowEnd,
        observationCount: hrvDays.length,
        confidence,
        missingnessNote: null,
      });
    }

    const strainDays = sortedDays.filter((d) => typeof d.dailyStrain === 'number');
    if (strainDays.length >= 5) {
      const confidence = confidenceFromObservations(strainDays.length, span);
      const avg = mean(strainDays.map((d) => d.dailyStrain as number));
      push({
        kind: 'strain_trend',
        statement: `Average daily strain: ${avg.toFixed(1)} across ${strainDays.length} days.`,
        evidenceFields: ['dailyStrain'],
        windowStart,
        windowEnd,
        observationCount: strainDays.length,
        confidence,
        missingnessNote: null,
      });
    }
  }

  return candidates;
}
