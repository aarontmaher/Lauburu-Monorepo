/**
 * Lauburu Readiness — custom grappling-aware readiness score.
 *
 * Combines today's normalized metrics with a personal baseline and
 * recent training-load context to produce a 0-100 score, status,
 * top contributing factors, and a plain-English explanation.
 *
 * Each signal contributes ONLY when its baseline window has enough
 * data; missing signals are surfaced as explicit gaps, not silently
 * ignored. Confidence scales with number of contributing signals +
 * baseline depth + data freshness.
 *
 * NOT MEDICAL ADVICE. Source-dependent. Conservative — low
 * confidence and insufficient_data states are surfaced explicitly.
 * No diagnosis. No supplement/drug recommendations. No claim of
 * medical validity.
 */

import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';

export type ReadinessStatus =
  | 'high'
  | 'normal'
  | 'caution'
  | 'recovery_bias'
  | 'insufficient_data';

export type ReadinessConfidence = 'high' | 'medium' | 'low' | 'insufficient';

export type TrainingBias =
  | 'hard_training_possible'
  | 'normal_training'
  | 'technical_light'
  | 'recovery_biased'
  | 'insufficient_data';

export interface ReadinessFactor {
  /** Stable signal id. */
  signal: 'hrv' | 'rhr' | 'sleep_hours' | 'source_recovery' | 'acute_chronic_ratio' | 'sleep_consistency';
  /** Personal-baseline z-score where applicable. Null for non-z signals. */
  z: number | null;
  /** This signal's 0-100 contribution score (pre-weighting). */
  contribution_score: number;
  /** Weight in the final blend (0..1). */
  weight: number;
  /** Plain-English description of what this signal is saying today. */
  detail: string;
}

export interface LauburuReadinessOutput {
  /** 0..100 final blended score, or null if insufficient_data. */
  score: number | null;
  status: ReadinessStatus;
  confidence: ReadinessConfidence;
  training_bias: TrainingBias;
  /** Up to 3 highest-contributing positive factors (above-baseline). */
  positive_factors: ReadinessFactor[];
  /** Up to 3 highest-contributing negative factors (below-baseline). */
  negative_factors: ReadinessFactor[];
  /** Signal ids not available today; populating these would improve confidence. */
  missing_data: string[];
  /** Stale-data, source-conflict, low-baseline-depth notes. */
  caveats: string[];
  /** 1-2 sentence plain-English summary; honest, non-prescriptive. */
  explanation: string;
  /** Number of signals that actually contributed to the score. */
  inputs_used: number;
  /** Days of normalized history available for baselines. */
  baseline_depth_days: number;
  /** When this score was computed. */
  computed_at: string;
  /** Always true — explicit safety marker for any consumer. */
  not_medical_advice: true;
  /** Always true — explicit experimental marker. */
  experimental: true;
}

export interface ComputeReadinessInput {
  /** Today's normalized metrics. May be null (insufficient_data). */
  today: NormalizedDailyMetrics | null;
  /** Personal baseline window. Today should NOT be in this list. */
  baseline: NormalizedDailyMetrics[];
  /** Acute training load — rolling sum/avg of strain over last ~7 days. */
  acuteLoad?: { sum: number; avg: number; days: number } | null;
  /** Chronic training load — rolling avg of strain over last ~28 days. */
  chronicLoad?: { avg: number; days: number } | null;
  /** Hours since the most-recent source sync. >36h penalizes confidence. */
  staleHours?: number | null;
}

const WEIGHTS = {
  hrv: 0.25,
  rhr: 0.15,
  sleep_hours: 0.30,
  source_recovery: 0.20,
  acute_chronic_ratio: 0.10,
};

/**
 * Map a z-score to a 0-100 contribution.
 *   z =  0  → 50
 *   z = +1  → 65 (when higher = better)
 *   z = +2  → 80
 *   z = -1  → 35
 * Saturated at [0, 100].
 */
function zToScore(z: number, higherBetter: boolean): number {
  const polarity = higherBetter ? 1 : -1;
  return Math.max(0, Math.min(100, 50 + polarity * z * 15));
}

function meanAndStdev(values: number[]): { mean: number; stdev: number } {
  if (values.length === 0) return { mean: 0, stdev: 0 };
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
  return { mean, stdev: Math.sqrt(variance) };
}

function pullBaseline(
  baseline: NormalizedDailyMetrics[],
  pick: (r: NormalizedDailyMetrics) => number | null,
): { values: number[]; mean: number; stdev: number } {
  const values: number[] = [];
  for (const r of baseline) {
    const v = pick(r);
    if (typeof v === 'number' && Number.isFinite(v)) values.push(v);
  }
  const { mean, stdev } = meanAndStdev(values);
  return { values, mean, stdev };
}

function clampNumber(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export function computeLauburuReadiness(input: ComputeReadinessInput): LauburuReadinessOutput {
  const computedAt = new Date().toISOString();
  const baseline = input.baseline ?? [];
  const today = input.today;
  const baselineDepth = baseline.length;

  // Bail early if we have nothing to work with.
  if (!today || baselineDepth < 3) {
    return {
      score: null,
      status: 'insufficient_data',
      confidence: 'insufficient',
      training_bias: 'insufficient_data',
      positive_factors: [],
      negative_factors: [],
      missing_data: [
        ...(today ? [] : ['todays_metrics']),
        ...(baselineDepth < 3 ? ['personal_baseline_min_3_days'] : []),
      ],
      caveats: [
        baselineDepth < 3
          ? `Only ${baselineDepth} day(s) of personal baseline available — need 3+ for any score; 7+ for medium confidence; 14+ for high confidence.`
          : 'No metrics available for today.',
      ],
      explanation:
        'Not enough personal baseline yet to compute readiness. Sync your health source for a few days; the score becomes available once 3+ days of baseline exist.',
      inputs_used: 0,
      baseline_depth_days: baselineDepth,
      computed_at: computedAt,
      not_medical_advice: true,
      experimental: true,
    };
  }

  const factors: ReadinessFactor[] = [];
  const missing: string[] = [];
  const caveats: string[] = [];

  // ── HRV (higher = better) ────────────────────────────────────
  const hrvBaseline = pullBaseline(baseline, (r) => r.hrvMs);
  if (typeof today.hrvMs === 'number' && hrvBaseline.values.length >= 3 && hrvBaseline.stdev > 0) {
    const z = (today.hrvMs - hrvBaseline.mean) / hrvBaseline.stdev;
    const contributionScore = zToScore(z, true);
    factors.push({
      signal: 'hrv',
      z: Number(z.toFixed(2)),
      contribution_score: Number(contributionScore.toFixed(1)),
      weight: WEIGHTS.hrv,
      detail:
        z > 0.5
          ? `HRV ${today.hrvMs.toFixed(0)} ms is elevated vs ${hrvBaseline.mean.toFixed(0)} ms baseline (+${z.toFixed(1)}σ).`
          : z < -0.5
          ? `HRV ${today.hrvMs.toFixed(0)} ms is suppressed vs ${hrvBaseline.mean.toFixed(0)} ms baseline (${z.toFixed(1)}σ).`
          : `HRV ${today.hrvMs.toFixed(0)} ms is near baseline (${hrvBaseline.mean.toFixed(0)} ms).`,
    });
  } else {
    missing.push('hrv');
  }

  // ── Resting HR (lower = better) ─────────────────────────────
  const rhrBaseline = pullBaseline(baseline, (r) => r.restingHrBpm);
  if (typeof today.restingHrBpm === 'number' && rhrBaseline.values.length >= 3 && rhrBaseline.stdev > 0) {
    const z = (today.restingHrBpm - rhrBaseline.mean) / rhrBaseline.stdev;
    const contributionScore = zToScore(z, false);
    factors.push({
      signal: 'rhr',
      z: Number(z.toFixed(2)),
      contribution_score: Number(contributionScore.toFixed(1)),
      weight: WEIGHTS.rhr,
      detail:
        z > 0.5
          ? `Resting HR ${today.restingHrBpm.toFixed(0)} bpm is elevated vs ${rhrBaseline.mean.toFixed(0)} bpm baseline (+${z.toFixed(1)}σ).`
          : z < -0.5
          ? `Resting HR ${today.restingHrBpm.toFixed(0)} bpm is below baseline (${z.toFixed(1)}σ) — favourable.`
          : `Resting HR ${today.restingHrBpm.toFixed(0)} bpm is near baseline (${rhrBaseline.mean.toFixed(0)} bpm).`,
    });
  } else {
    missing.push('rhr');
  }

  // ── Sleep hours (higher = better, soft-capped near 8h) ──────
  // Use a hybrid: z vs baseline AND absolute hours floor (anything
  // <5h is penalised regardless of personal baseline).
  const sleepBaseline = pullBaseline(baseline, (r) => r.totalSleepHours);
  if (typeof today.totalSleepHours === 'number' && sleepBaseline.values.length >= 3) {
    const stdev = sleepBaseline.stdev > 0 ? sleepBaseline.stdev : 1.0;
    const z = (today.totalSleepHours - sleepBaseline.mean) / stdev;
    let contributionScore = zToScore(z, true);
    // Hard penalty if absolute sleep is under 5 hours regardless of z.
    if (today.totalSleepHours < 5) contributionScore = Math.min(contributionScore, 25);
    if (today.totalSleepHours < 4) contributionScore = Math.min(contributionScore, 10);
    factors.push({
      signal: 'sleep_hours',
      z: Number(z.toFixed(2)),
      contribution_score: Number(contributionScore.toFixed(1)),
      weight: WEIGHTS.sleep_hours,
      detail:
        today.totalSleepHours < 5
          ? `Sleep ${today.totalSleepHours.toFixed(1)}h is short — lower readiness regardless of baseline.`
          : z > 0.5
          ? `Sleep ${today.totalSleepHours.toFixed(1)}h is above your ${sleepBaseline.mean.toFixed(1)}h baseline.`
          : z < -0.5
          ? `Sleep ${today.totalSleepHours.toFixed(1)}h is below your ${sleepBaseline.mean.toFixed(1)}h baseline.`
          : `Sleep ${today.totalSleepHours.toFixed(1)}h is near your ${sleepBaseline.mean.toFixed(1)}h baseline.`,
    });
  } else {
    missing.push('sleep_hours');
  }

  // ── Source-supplied recovery score (e.g. WHOOP / Apple) ─────
  // Some sources return a 0-100 recovery already; trust it directly
  // but still attach to the blend with reduced weight when source
  // is single-vendor (we can't validate cross-source here).
  if (typeof today.recoveryScore === 'number' && today.recoveryScore >= 0 && today.recoveryScore <= 100) {
    factors.push({
      signal: 'source_recovery',
      z: null,
      contribution_score: Number(today.recoveryScore.toFixed(1)),
      weight: WEIGHTS.source_recovery,
      detail: `Source recovery score ${today.recoveryScore.toFixed(0)}/100 (${today.provider ?? 'unknown source'}).`,
    });
  } else {
    missing.push('source_recovery');
  }

  // ── Acute / chronic load ratio ──────────────────────────────
  // Banister-style training-stress balance, simplified:
  //   ratio = acute7d / chronic28d
  //   ratio in [0.8, 1.3] is "in the zone" → score 65
  //   ratio > 1.5 = acute spike → score 30
  //   ratio < 0.5 = under-trained → score 50 (neutral, not penalised)
  if (input.acuteLoad?.avg != null && input.chronicLoad?.avg != null && input.chronicLoad.avg > 0) {
    const ratio = input.acuteLoad.avg / input.chronicLoad.avg;
    let contributionScore = 65;
    if (ratio > 1.5) contributionScore = 30;
    else if (ratio > 1.3) contributionScore = 45;
    else if (ratio < 0.5) contributionScore = 50;
    factors.push({
      signal: 'acute_chronic_ratio',
      z: null,
      contribution_score: Number(contributionScore.toFixed(1)),
      weight: WEIGHTS.acute_chronic_ratio,
      detail: `Acute:chronic load ratio ${ratio.toFixed(2)} (${input.acuteLoad.days}d acute / ${input.chronicLoad.days}d chronic).`,
    });
  } else {
    missing.push('acute_chronic_ratio');
  }

  // ── Stale data / freshness penalty ──────────────────────────
  if (typeof input.staleHours === 'number' && input.staleHours > 36) {
    caveats.push(`Latest source data is ${Math.round(input.staleHours)}h old — readiness may not reflect current state.`);
  }

  // ── Baseline depth caveat ───────────────────────────────────
  if (baselineDepth < 7) {
    caveats.push(`Only ${baselineDepth} days of personal baseline — confidence capped at low until you have 7+ days.`);
  } else if (baselineDepth < 14) {
    caveats.push(`Personal baseline is ${baselineDepth} days — medium confidence; high confidence after 14+ days.`);
  }

  if (factors.length === 0) {
    return {
      score: null,
      status: 'insufficient_data',
      confidence: 'insufficient',
      training_bias: 'insufficient_data',
      positive_factors: [],
      negative_factors: [],
      missing_data: missing,
      caveats: [...caveats, 'No usable signals today. Sync your health source.'],
      explanation: 'No signals contributed to a readiness score today. Connect/sync your health source to populate metrics.',
      inputs_used: 0,
      baseline_depth_days: baselineDepth,
      computed_at: computedAt,
      not_medical_advice: true,
      experimental: true,
    };
  }

  // ── Blend signals into 0-100 ────────────────────────────────
  const totalWeight = factors.reduce((s, f) => s + f.weight, 0);
  const weightedSum = factors.reduce((s, f) => s + f.contribution_score * f.weight, 0);
  const score = totalWeight > 0 ? clampNumber(weightedSum / totalWeight, 0, 100) : null;

  // ── Status ──────────────────────────────────────────────────
  let status: ReadinessStatus = 'normal';
  if (score == null) status = 'insufficient_data';
  else if (score >= 70) status = 'high';
  else if (score >= 50) status = 'normal';
  else if (score >= 30) status = 'caution';
  else status = 'recovery_bias';

  // ── Confidence ─────────────────────────────────────────────
  let confidence: ReadinessConfidence = 'low';
  if (factors.length >= 3 && baselineDepth >= 14) confidence = 'high';
  else if (factors.length >= 2 && baselineDepth >= 7) confidence = 'medium';
  else confidence = 'low';
  if (typeof input.staleHours === 'number' && input.staleHours > 72) {
    // Stale > 3 days drops one tier.
    confidence = confidence === 'high' ? 'medium' : confidence === 'medium' ? 'low' : 'insufficient';
  }

  // ── Training bias ──────────────────────────────────────────
  let trainingBias: TrainingBias = 'normal_training';
  if (status === 'insufficient_data') trainingBias = 'insufficient_data';
  else if (status === 'high' && confidence !== 'low') trainingBias = 'hard_training_possible';
  else if (status === 'normal') trainingBias = 'normal_training';
  else if (status === 'caution') trainingBias = 'technical_light';
  else if (status === 'recovery_bias') trainingBias = 'recovery_biased';

  // ── Top factors (split positive/negative, rank by abs delta from 50) ──
  const ranked = [...factors].sort(
    (a, b) => Math.abs(b.contribution_score - 50) - Math.abs(a.contribution_score - 50),
  );
  const positives = ranked.filter((f) => f.contribution_score > 50).slice(0, 3);
  const negatives = ranked.filter((f) => f.contribution_score < 50).slice(0, 3);

  // ── Plain-English explanation (deterministic, conservative) ──
  const reasonsBits: string[] = [];
  if (negatives.length > 0) {
    reasonsBits.push(negatives.map((n) => n.detail).join(' '));
  } else if (positives.length > 0) {
    reasonsBits.push(positives.map((p) => p.detail).join(' '));
  }
  const biasPlainEnglish: Record<TrainingBias, string> = {
    hard_training_possible: 'Hard rounds look reasonable today.',
    normal_training: 'Normal training is appropriate today.',
    technical_light: 'Bias toward technical drilling or lighter rounds today.',
    recovery_biased: 'Recovery-biased day suggested.',
    insufficient_data: 'Not enough data yet.',
  };
  const explanation = `${biasPlainEnglish[trainingBias]} ${reasonsBits[0] ?? ''}${
    confidence === 'low' || confidence === 'insufficient'
      ? ' Treat as low-confidence — collect more days for a stronger read.'
      : ''
  }`.trim();

  return {
    score: score == null ? null : Number(score.toFixed(1)),
    status,
    confidence,
    training_bias: trainingBias,
    positive_factors: positives,
    negative_factors: negatives,
    missing_data: missing,
    caveats,
    explanation,
    inputs_used: factors.length,
    baseline_depth_days: baselineDepth,
    computed_at: computedAt,
    not_medical_advice: true,
    experimental: true,
  };
}
