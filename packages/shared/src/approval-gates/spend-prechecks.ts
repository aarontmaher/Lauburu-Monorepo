/**
 * Deterministic prechecks for AI spend gates. Each precheck takes
 * a context object, returns a non-AI summary string, and a verdict
 * — `precheck_only` (no AI needed) or `requires_ai` (precheck
 * couldn't answer; spend approval required).
 *
 * No precheck is a clinical claim, no precheck is a medical recommendation,
 * no precheck infers causation. Output is associations / counts / shape only.
 */

export type PrecheckVerdict = 'precheck_only' | 'requires_ai';

export interface PrecheckOutput {
  ruleId: string;
  triggerType: string;
  summary: string;
  verdict: PrecheckVerdict;
  reasonForAi: string | null;
}

// ── 1. Journal import ────────────────────────────────────────────────
// "User pasted N lines of notes. Parser produced K rows. M need
// confirmation. Are any rows ambiguous enough that an AI re-read is
// worth it?" — answer is almost always NO; the parser's output is
// the source of truth and the confirmation flow is the user's
// review step. AI is only worth it when the parser flagged
// `low confidence` for > some threshold of rows.

export interface JournalImportPrecheckInput {
  totalRows: number;
  needsConfirmationCount: number;
  lowConfidenceCount: number;
  /** True when more than half the rows are missing date / item / amount. */
  highlyAmbiguous: boolean;
}

const JOURNAL_AMBIGUOUS_THRESHOLD = 0.4;

export function precheckJournalImport(input: JournalImportPrecheckInput): PrecheckOutput {
  const { totalRows, needsConfirmationCount, lowConfidenceCount, highlyAmbiguous } = input;
  const lowConfRatio = totalRows > 0 ? lowConfidenceCount / totalRows : 0;
  const verdict: PrecheckVerdict = highlyAmbiguous && lowConfRatio >= JOURNAL_AMBIGUOUS_THRESHOLD
    ? 'requires_ai'
    : 'precheck_only';
  const summary = [
    `Journal import: ${totalRows} parsed row${totalRows === 1 ? '' : 's'}.`,
    `${needsConfirmationCount} need user confirmation, ${lowConfidenceCount} low-confidence.`,
    highlyAmbiguous ? 'Most rows missing required fields.' : 'Most rows have date + item + amount.',
    'No medical advice. No causation. The user reviews each row before save.',
  ].join(' ');
  const reasonForAi = verdict === 'requires_ai'
    ? `Highly ambiguous paste (${Math.round(lowConfRatio * 100)}% low-confidence + missing required fields). Parser cannot guess; an AI re-read of the raw text MAY recover more rows.`
    : null;
  return { ruleId: 'precheck-journal-import-v1', triggerType: 'journal_import', summary, verdict, reasonForAi };
}

// ── 2. Readiness anomaly ─────────────────────────────────────────────
// "Today's readiness drop is N points vs the rolling 7-day baseline.
// Is the drop explainable by yesterday's training load + sleep?"
// — answer with deterministic thresholds first; only escalate to AI
// when neither training nor sleep nor a self-reported journal event
// covers the gap.

export interface ReadinessAnomalyPrecheckInput {
  todayScore: number | null;
  baselineScore: number | null;
  yesterdayStrain: number | null;
  yesterdaySleepHours: number | null;
  /** Whether the user logged a journal event in the last 48h that
   *  the heuristic flags as relevant (sickness / heavy training /
   *  travel). */
  hasRelevantJournalEvent: boolean;
}

const READINESS_DROP_TRIGGER = 15;       // points
const HEAVY_STRAIN_TRIGGER = 16;         // WHOOP-like 21-pt scale
const LOW_SLEEP_TRIGGER = 6.5;           // hours

export function precheckReadinessAnomaly(input: ReadinessAnomalyPrecheckInput): PrecheckOutput {
  const { todayScore, baselineScore, yesterdayStrain, yesterdaySleepHours, hasRelevantJournalEvent } = input;
  if (todayScore == null || baselineScore == null) {
    const summary = 'Readiness anomaly precheck: missing today or baseline score; deterministic heuristic cannot run. Surface the missing inputs to the user before any AI call.';
    return { ruleId: 'precheck-readiness-anomaly-v1', triggerType: 'readiness_anomaly', summary, verdict: 'precheck_only', reasonForAi: null };
  }
  const drop = baselineScore - todayScore;
  if (drop < READINESS_DROP_TRIGGER) {
    const summary = `Readiness drop ${drop.toFixed(0)} pts < ${READINESS_DROP_TRIGGER}-pt trigger; precheck does not flag an anomaly. No AI call needed.`;
    return { ruleId: 'precheck-readiness-anomaly-v1', triggerType: 'readiness_anomaly', summary, verdict: 'precheck_only', reasonForAi: null };
  }
  const strainExplains = (yesterdayStrain ?? 0) >= HEAVY_STRAIN_TRIGGER;
  const sleepExplains = (yesterdaySleepHours ?? Number.POSITIVE_INFINITY) < LOW_SLEEP_TRIGGER;
  const journalExplains = hasRelevantJournalEvent;
  const verdict: PrecheckVerdict = strainExplains || sleepExplains || journalExplains ? 'precheck_only' : 'requires_ai';
  const explanations: string[] = [];
  if (strainExplains) explanations.push(`yesterday strain ${yesterdayStrain ?? '—'} ≥ ${HEAVY_STRAIN_TRIGGER}`);
  if (sleepExplains) explanations.push(`sleep ${yesterdaySleepHours ?? '—'}h < ${LOW_SLEEP_TRIGGER}h`);
  if (journalExplains) explanations.push('relevant journal event in last 48h');
  const summary = [
    `Readiness drop ${drop.toFixed(0)} pts vs baseline ${baselineScore}. Today ${todayScore}.`,
    explanations.length > 0
      ? `Drop is associated with: ${explanations.join('; ')}. Associations only — not causation.`
      : 'No deterministic explanatory signal in training, sleep, or journal.',
    'No medical advice. No clinical thresholds.',
  ].join(' ');
  const reasonForAi = verdict === 'requires_ai'
    ? 'Drop ≥ trigger and no deterministic explanatory signal. AI MAY help spot a multi-day pattern the heuristic missed; deterministic answer remains the source of truth.'
    : null;
  return { ruleId: 'precheck-readiness-anomaly-v1', triggerType: 'readiness_anomaly', summary, verdict, reasonForAi };
}

// ── 3. Health trend ──────────────────────────────────────────────────
// "Resting HR has trended +N bpm over the last K days. Is the trend
// large enough to be worth describing in narrative form?" — strictly
// counts and slopes; refuse to phrase any clinical interpretation.

export interface HealthTrendPrecheckInput {
  metric: string;
  windowDays: number;
  earliestValue: number | null;
  latestValue: number | null;
  /** True when the slope direction is consistent across the window
   *  (no flips). */
  monotonic: boolean;
  /** Domain-aware trigger (caller supplies). */
  significantDeltaAbs: number;
}

export function precheckHealthTrend(input: HealthTrendPrecheckInput): PrecheckOutput {
  const { metric, windowDays, earliestValue, latestValue, monotonic, significantDeltaAbs } = input;
  if (earliestValue == null || latestValue == null) {
    const summary = `Health trend precheck (${metric}): missing earliest or latest value over ${windowDays}d; cannot compute slope. Surface gap to user.`;
    return { ruleId: 'precheck-health-trend-v1', triggerType: 'health_trend', summary, verdict: 'precheck_only', reasonForAi: null };
  }
  const delta = latestValue - earliestValue;
  const absDelta = Math.abs(delta);
  if (absDelta < significantDeltaAbs) {
    const summary = `${metric} change ${delta >= 0 ? '+' : ''}${delta.toFixed(2)} over ${windowDays}d is below the ${significantDeltaAbs} trigger. No narrative needed; raw numbers stand.`;
    return { ruleId: 'precheck-health-trend-v1', triggerType: 'health_trend', summary, verdict: 'precheck_only', reasonForAi: null };
  }
  const verdict: PrecheckVerdict = monotonic ? 'requires_ai' : 'precheck_only';
  const summary = [
    `${metric} change ${delta >= 0 ? '+' : ''}${delta.toFixed(2)} over ${windowDays}d.`,
    monotonic ? 'Slope is consistent across the window.' : 'Slope flips inside the window — non-monotonic; precheck declines to summarise.',
    'No medical advice. No causation. Numbers are descriptive only.',
  ].join(' ');
  const reasonForAi = verdict === 'requires_ai'
    ? `Monotonic ${metric} shift over ${windowDays}d exceeds ${significantDeltaAbs}. AI MAY phrase a one-line association narrative; precheck explicitly forbids clinical interpretation.`
    : null;
  return { ruleId: 'precheck-health-trend-v1', triggerType: 'health_trend', summary, verdict, reasonForAi };
}
