/**
 * Hub-first contextual readiness — the PRIMARY readiness model.
 *
 * Uses Health Connect / Apple Health / Samsung Health / Polar-via-HC
 * as the default backlog + trend inputs. Produces a structured
 * "contextual readiness" output that is useful for training decisions
 * WITHOUT requiring direct WHOOP.
 *
 * Explicitly labeled as CONTEXTUAL readiness, never "live readiness"
 * or "clearance." The output tells the athlete what the hub data
 * shows about their recent state — sleep quality, resting HR trend,
 * training load, recovery proxy signals — but never claims to replace
 * the deeper physiological readiness that direct WHOOP provides.
 *
 * When direct WHOOP IS available, this layer still runs as support
 * context alongside the WHOOP-gated `analyseReadiness()`.
 *
 * Pure function. No network calls. No cross-athlete reads.
 */

import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';

export type ContextualReadinessLevel =
  | 'looks_good'       // Hub signals suggest the athlete is well-rested
  | 'moderate'         // Mixed signals — some caution warranted
  | 'caution'          // Multiple signals suggest fatigue or load
  | 'insufficient'     // Not enough hub data to form any opinion
  ;

export interface ContextualReadinessInput {
  athleteId: string;
  date: string;
  /** Recent normalized days from hub sources (HC / Samsung / Polar / AH). */
  recentDays: NormalizedDailyMetrics[];
  /** Today's normalized record, if available. */
  today: NormalizedDailyMetrics | null;
  /** Which hub sources contributed to these records. */
  hubSources: string[];
  /** Number of HIIT sessions in last 7 days. */
  hiitSessionsLast7Days: number;
  /** Number of grappling sessions in last 7 days. */
  grapplingSessionsLast7Days: number;
  /** Whether nutrition was logged today. */
  nutritionLoggedToday: boolean;
  /** Whether direct WHOOP is also available (changes output framing). */
  hasDirectWhoop: boolean;
  /** History scope for framing. */
  historyScope: 'full_history' | 'limited_history' | 'unknown';
}

export interface ContextualReadinessResult {
  athleteId: string;
  date: string;
  mode: 'contextual'; // Always 'contextual' — never 'live'
  level: ContextualReadinessLevel;
  confidence: 'low' | 'medium' | 'high';

  /** Compact summary for mobile display. */
  summary: string;
  /** What signals grounded this assessment. */
  signals: ContextualSignal[];
  /** What would make this assessment stronger. */
  gaps: string[];
  /** Disclaimer — always present. */
  disclaimer: string;
  /** Whether direct WHOOP would add deeper readiness fields. */
  whoopWouldAdd: string[];
}

export interface ContextualSignal {
  domain: string;
  label: string;
  direction: 'positive' | 'neutral' | 'negative' | 'unknown';
  value: string;
  /** How many days of data ground this signal. */
  dataPoints: number;
}

const DISCLAIMER = 'Contextual readiness from your health hubs — not a direct physiological clearance. Use as informed training context.';

function mean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function trend(values: number[]): 'rising' | 'falling' | 'stable' | 'unknown' {
  if (values.length < 3) return 'unknown';
  const first = mean(values.slice(0, Math.floor(values.length / 2)));
  const second = mean(values.slice(Math.floor(values.length / 2)));
  const delta = second - first;
  const threshold = Math.abs(first) * 0.05; // 5% change threshold
  if (delta > threshold) return 'rising';
  if (delta < -threshold) return 'falling';
  return 'stable';
}

export function analyseContextualReadiness(
  input: ContextualReadinessInput,
): ContextualReadinessResult {
  const { athleteId, date, recentDays, today, hubSources, hiitSessionsLast7Days,
    grapplingSessionsLast7Days, nutritionLoggedToday, hasDirectWhoop, historyScope } = input;

  const signals: ContextualSignal[] = [];
  const gaps: string[] = [];
  let positives = 0;
  let negatives = 0;

  const sorted = [...recentDays].sort((a, b) => a.date.localeCompare(b.date));

  // 1. Sleep analysis
  const sleepValues = sorted.map(d => d.totalSleepHours).filter((v): v is number => v != null);
  if (sleepValues.length >= 3) {
    const avg = mean(sleepValues);
    const lastNight = today?.totalSleepHours ?? sleepValues[sleepValues.length - 1];
    const sleepTrend = trend(sleepValues);
    const isGood = lastNight != null && lastNight >= 7;
    if (isGood) positives++; else if (lastNight != null && lastNight < 6) negatives++;
    signals.push({
      domain: 'sleep',
      label: lastNight != null
        ? `Last night: ${lastNight.toFixed(1)}h (avg ${avg.toFixed(1)}h, ${sleepTrend})`
        : `Average sleep: ${avg.toFixed(1)}h (${sleepTrend})`,
      direction: isGood ? 'positive' : lastNight != null && lastNight < 6 ? 'negative' : 'neutral',
      value: lastNight?.toFixed(1) ?? avg.toFixed(1),
      dataPoints: sleepValues.length,
    });
  } else {
    gaps.push('Sleep: fewer than 3 nights logged — sleep trends unavailable.');
  }

  // 2. Resting HR trend
  const rhrValues = sorted.map(d => d.restingHrBpm).filter((v): v is number => v != null);
  if (rhrValues.length >= 3) {
    const avg = mean(rhrValues);
    const rhrTrend = trend(rhrValues);
    const latest = today?.restingHrBpm ?? rhrValues[rhrValues.length - 1];
    const elevated = latest != null && latest > avg * 1.1;
    if (elevated) negatives++;
    else if (rhrTrend === 'falling' || rhrTrend === 'stable') positives++;
    signals.push({
      domain: 'resting_hr',
      label: `Resting HR: ${latest ?? avg.toFixed(0)} bpm (avg ${avg.toFixed(0)}, ${rhrTrend})${elevated ? ' — elevated' : ''}`,
      direction: elevated ? 'negative' : rhrTrend === 'falling' ? 'positive' : 'neutral',
      value: `${latest ?? avg.toFixed(0)} bpm`,
      dataPoints: rhrValues.length,
    });
  } else if (rhrValues.length > 0) {
    signals.push({
      domain: 'resting_hr',
      label: `Resting HR: ${rhrValues[rhrValues.length - 1]} bpm (limited data)`,
      direction: 'unknown',
      value: `${rhrValues[rhrValues.length - 1]} bpm`,
      dataPoints: rhrValues.length,
    });
  } else {
    gaps.push('Resting HR: no data — heart-rate trends unavailable.');
  }

  // 3. Training load (workout frequency)
  const workoutDays = sorted.filter(d => (d.workoutCount ?? 0) > 0).length;
  const totalSessions = hiitSessionsLast7Days + grapplingSessionsLast7Days;
  if (workoutDays > 0 || totalSessions > 0) {
    const loadNote = totalSessions >= 5 ? 'high load' : totalSessions >= 3 ? 'moderate load' : 'light load';
    if (totalSessions >= 5) negatives++;
    else if (totalSessions >= 2) positives++;
    signals.push({
      domain: 'training_load',
      label: `${workoutDays} workout days + ${hiitSessionsLast7Days} HIIT + ${grapplingSessionsLast7Days} grappling in last 7d (${loadNote})`,
      direction: totalSessions >= 5 ? 'negative' : totalSessions <= 1 ? 'neutral' : 'positive',
      value: `${totalSessions} sessions`,
      dataPoints: sorted.length,
    });
  } else {
    gaps.push('Training load: no workouts or sessions logged in window.');
  }

  // 4. HRV (if available from hub — rare without WHOOP, but Samsung/Polar may provide)
  const hrvValues = sorted.map(d => d.hrvMs).filter((v): v is number => v != null);
  if (hrvValues.length >= 3) {
    const avg = mean(hrvValues);
    const hrvTrend = trend(hrvValues);
    const latest = today?.hrvMs ?? hrvValues[hrvValues.length - 1];
    const depressed = latest != null && latest < avg * 0.85;
    if (depressed) negatives++;
    else if (hrvTrend === 'rising' || hrvTrend === 'stable') positives++;
    signals.push({
      domain: 'hrv',
      label: `HRV: ${latest?.toFixed(0) ?? avg.toFixed(0)} ms (avg ${avg.toFixed(0)}, ${hrvTrend})${depressed ? ' — below baseline' : ''}`,
      direction: depressed ? 'negative' : hrvTrend === 'rising' ? 'positive' : 'neutral',
      value: `${latest?.toFixed(0) ?? avg.toFixed(0)} ms`,
      dataPoints: hrvValues.length,
    });
  }

  // 5. Nutrition
  if (nutritionLoggedToday) {
    const kcal = today?.nutritionCalories;
    signals.push({
      domain: 'nutrition',
      label: kcal != null ? `Nutrition today: ${kcal} kcal logged` : 'Nutrition logged today',
      direction: 'positive',
      value: kcal != null ? `${kcal} kcal` : 'logged',
      dataPoints: 1,
    });
    positives++;
  }

  // 6. Active calories / steps as general activity
  const stepsValues = sorted.map(d => (d as any).stepCount ?? 0).filter((v: number) => v > 0);
  if (stepsValues.length >= 3) {
    const avg = mean(stepsValues);
    signals.push({
      domain: 'activity',
      label: `Average daily steps: ${Math.round(avg).toLocaleString()} (${stepsValues.length} days)`,
      direction: avg >= 6000 ? 'positive' : 'neutral',
      value: `${Math.round(avg)}`,
      dataPoints: stepsValues.length,
    });
  }

  // Derive level
  let level: ContextualReadinessLevel;
  const totalSignals = signals.length;
  if (totalSignals === 0) {
    level = 'insufficient';
  } else if (negatives >= 2) {
    level = 'caution';
  } else if (negatives >= 1 && positives <= negatives) {
    level = 'moderate';
  } else if (positives >= 2) {
    level = 'looks_good';
  } else {
    level = 'moderate';
  }

  const confidence: 'low' | 'medium' | 'high' =
    totalSignals >= 4 && sorted.length >= 7 ? 'high' :
    totalSignals >= 2 ? 'medium' : 'low';

  // Summary
  const levelLabel = level === 'looks_good' ? 'Hub signals look good' :
    level === 'moderate' ? 'Mixed signals — moderate caution' :
    level === 'caution' ? 'Multiple caution signals' : 'Not enough data yet';
  const sourceList = hubSources.length > 0 ? hubSources.join(', ') : 'health hubs';
  const summary = `${levelLabel} (from ${sourceList}). ${signals.slice(0, 2).map(s => s.label).join('. ')}.`;

  // What WHOOP would add
  const whoopWouldAdd: string[] = [];
  if (!hasDirectWhoop) {
    whoopWouldAdd.push('Recovery score (direct physiological readiness)');
    whoopWouldAdd.push('WHOOP-native HRV with nightly baseline');
    whoopWouldAdd.push('Daily strain score');
    whoopWouldAdd.push('Sleep performance score');
    whoopWouldAdd.push('Direct readiness clearance for high-intensity training');
  }

  if (historyScope === 'limited_history') {
    gaps.push('Health Connect history limited to ~30 days. Grant full history permission for deeper trends.');
  }

  return {
    athleteId,
    date,
    mode: 'contextual',
    level,
    confidence,
    summary,
    signals,
    gaps,
    disclaimer: DISCLAIMER,
    whoopWouldAdd,
  };
}
