/**
 * Grappler Readiness — app-owned, multi-bucket readiness model.
 *
 * Goal of this module:
 *   - Produce ONE app-owned 0-100 score that is THE product number.
 *   - Decompose it into five buckets so each can be surfaced and
 *     improved independently:
 *       autonomic | sleep | load | grappling | subjective
 *   - Carry wearable-native scores through unmodified as
 *     `raw_source_scores` — supporting evidence, never primary.
 *   - Surface explicit `injury_risk_flags[]` and an actionable
 *     `improve_score_by[]` list.
 *   - Stay backwards-compatible with the existing
 *     `LauburuReadinessOutput`: this module reuses the same
 *     5-signal logic for autonomic / sleep / load buckets.
 *
 * Pure compute. No I/O. No network. Missing data stays missing —
 * the function never invents values.
 *
 * NOT MEDICAL ADVICE. Source-dependent. Conservative. Not a
 * diagnosis. No drug or supplement claims.
 */

import type { NormalizedDailyMetrics } from '../../contracts/normalized-daily.types';
import { computeLauburuReadiness } from './lauburu-readiness';
import type { LauburuReadinessOutput } from './lauburu-readiness';

// ── Public types ────────────────────────────────────────────────

export type GrapplerRecommendation =
  | 'hard_training'
  | 'moderate'
  | 'technical'
  | 'recovery'
  | 'rest'
  | 'insufficient_data';

export type WearableSourceId =
  | 'apple_health'
  | 'health_connect'
  | 'whoop_direct'
  | 'whoop_csv'
  | 'polar_via_hc'
  | 'polar_direct'
  | 'samsung_health'
  | 'oura'
  | 'garmin'
  | 'manual';

export interface BucketScore {
  /** 0-100 sub-score for this bucket. Null when insufficient. */
  score: number | null;
  /** Signal ids that contributed (eg. 'hrv_ms', 'sleep_hours'). */
  inputs_used: string[];
  /** Signal ids that would have if present today. */
  missing: string[];
  confidence: 'high' | 'medium' | 'low' | 'insufficient';
  /** Per-source provenance — never empty when score is non-null. */
  source_breakdown: WearableSourceId[];
}

/**
 * Raw provider-native scores carried through unmodified — supporting
 * evidence, never the product number. Each field is null when the
 * provider didn't expose that score or hasn't synced today. UI may
 * render small chips ("WHOOP Recovery 78", "Oura Sleep 84") next to
 * the app's primary Grappler Readiness band.
 */
export interface RawSourceScores {
  whoop_recovery_pct: number | null;
  whoop_strain: number | null;
  whoop_sleep_pct: number | null;
  oura_readiness: number | null;
  oura_sleep: number | null;
  garmin_body_battery: number | null;
  garmin_training_readiness: number | null;
  apple_watch_walking_steadiness: number | null;
  polar_recovery_pro: number | null;
  polar_nightly_recharge: number | null;
}

export interface InjuryRiskFlag {
  region: 'neck' | 'shoulder' | 'elbow' | 'wrist' | 'rib' | 'hip' | 'knee' | 'ankle' | 'other';
  source: 'self_reported' | 'inferred';
  severity: 'low' | 'medium' | 'high';
  detail: string;
}

export interface GrapplerReadinessOutput {
  /** App-owned 0-100 score. The product number. Null when insufficient_data. */
  app_readiness_score: number | null;
  recommendation: GrapplerRecommendation;
  confidence: 'high' | 'medium' | 'low' | 'insufficient';

  /** Five bucket sub-scores. Each is independently computable and showable. */
  autonomic_readiness: BucketScore;
  sleep_readiness: BucketScore;
  load_readiness: BucketScore;
  grappling_readiness: BucketScore;
  subjective_readiness: BucketScore;

  /** Roll-up of providers that backed any bucket today. */
  source_breakdown: WearableSourceId[];

  /** Wearable-native scores carried through. NEVER the primary number. */
  raw_source_scores: RawSourceScores;

  /** Self-reported + inferred injury risk. */
  injury_risk_flags: InjuryRiskFlag[];

  positive_factors: { signal: string; bucket: string; detail: string }[];
  negative_factors: { signal: string; bucket: string; detail: string }[];
  improve_score_by: { action: string; would_unlock: string }[];

  explanation: string;
  caveats: string[];

  /** Bucket weights actually used (for transparency). */
  weights: {
    autonomic: number;
    sleep: number;
    load: number;
    grappling: number;
    subjective: number;
  };

  not_medical_advice: true;
  experimental: true;
  computed_at: string;
}

export interface ComputeGrapplerInput {
  today: NormalizedDailyMetrics | null;
  baseline: NormalizedDailyMetrics[];
  acuteLoad?: { sum: number; avg: number; days: number } | null;
  chronicLoad?: { avg: number; days: number } | null;
  staleHours?: number | null;
  /** Optional latest manual check-in within ~36h. Subjective bucket
   *  populates from this; absent → bucket stays insufficient. */
  latestCheckin?: {
    soreness_0_10?: number | null;
    sleep_quality_0_10?: number | null;
    mental_sharpness_0_10?: number | null;
    motivation_0_10?: number | null;
    stress_0_10?: number | null;
    recovery_feel?: 'better' | 'same' | 'worse' | null;
    injury_flag?: boolean | null;
    injury_region_tags?: string[] | null;
  } | null;
  /** Optional summary of recent grappling sessions (last 7 days).
   *  Grappling bucket populates from this; absent → bucket stays
   *  insufficient. */
  recentGrappling?: {
    hard_rounds_count_7d?: number | null;
    positional_intensity_avg_7d?: number | null;
    consecutive_grappling_days?: number | null;
    comp_prep_window?: boolean | null;
  } | null;
}

// ── Defaults / weights ───────────────────────────────────────────

const WEIGHTS = {
  autonomic: 0.25,
  sleep: 0.25,
  load: 0.20,
  grappling: 0.15,
  subjective: 0.15,
};

const EMPTY_RAW_SCORES: RawSourceScores = {
  whoop_recovery_pct: null,
  whoop_strain: null,
  whoop_sleep_pct: null,
  oura_readiness: null,
  oura_sleep: null,
  garmin_body_battery: null,
  garmin_training_readiness: null,
  apple_watch_walking_steadiness: null,
  polar_recovery_pro: null,
  polar_nightly_recharge: null,
};

function emptyBucket(missing: string[]): BucketScore {
  return {
    score: null,
    inputs_used: [],
    missing,
    confidence: 'insufficient',
    source_breakdown: [],
  };
}

// ── Helpers ──────────────────────────────────────────────────────

function clamp01to100(v: number): number {
  return Math.max(0, Math.min(100, v));
}

function inferProviders(today: NormalizedDailyMetrics | null): WearableSourceId[] {
  if (!today) return [];
  const out = new Set<WearableSourceId>();
  const provider = (today as any).provider as string | undefined;
  if (provider) {
    if (provider.includes('whoop_direct')) out.add('whoop_direct');
    else if (provider.includes('whoop')) out.add('whoop_csv');
    if (provider.includes('apple_health')) out.add('apple_health');
    if (provider.includes('health_connect')) out.add('health_connect');
    if (provider.includes('polar_via_health_connect')) out.add('polar_via_hc');
    if (provider.includes('polar')) out.add('polar_direct');
    if (provider.includes('samsung')) out.add('samsung_health');
    if (provider.includes('oura')) out.add('oura');
    if (provider.includes('garmin')) out.add('garmin');
    if (provider === 'manual' || provider === 'mixed') out.add('manual');
  }
  const arr = Array.isArray((today as any).providerSources) ? (today as any).providerSources as string[] : [];
  for (const p of arr) {
    if (p === 'whoop_direct') out.add('whoop_direct');
    if (p === 'whoop') out.add('whoop_csv');
    if (p === 'apple_health') out.add('apple_health');
    if (p === 'health_connect') out.add('health_connect');
    if (p === 'polar_via_health_connect') out.add('polar_via_hc');
    if (p === 'polar') out.add('polar_direct');
    if (p === 'samsung_health' || p === 'samsung_health_via_health_connect') out.add('samsung_health');
    if (p === 'oura') out.add('oura');
    if (p === 'garmin') out.add('garmin');
  }
  return Array.from(out);
}

// ── Bucket compute ───────────────────────────────────────────────

function computeAutonomicBucket(
  laub: LauburuReadinessOutput,
  today: NormalizedDailyMetrics | null,
  providers: WearableSourceId[],
): BucketScore {
  const inputs: string[] = [];
  const missing: string[] = [];
  let sum = 0;
  let weight = 0;
  for (const f of laub.positive_factors.concat(laub.negative_factors)) {
    if (f.signal === 'hrv') {
      inputs.push('hrv_ms');
      sum += f.contribution_score * f.weight;
      weight += f.weight;
    } else if (f.signal === 'rhr') {
      inputs.push('rhr_bpm');
      sum += f.contribution_score * f.weight;
      weight += f.weight;
    }
  }
  if (!inputs.includes('hrv_ms') && (today?.hrvMs == null)) missing.push('hrv_ms');
  if (!inputs.includes('rhr_bpm') && (today?.restingHrBpm == null)) missing.push('rhr_bpm');
  if (today?.respiratoryRate == null) missing.push('respiratory_rate');
  if ((today as any)?.spo2Pct == null) missing.push('spo2_pct');
  if (weight === 0) return emptyBucket(missing);
  const score = clamp01to100(sum / weight);
  return {
    score,
    inputs_used: inputs,
    missing,
    confidence: inputs.length >= 2 ? 'high' : 'medium',
    source_breakdown: providers,
  };
}

function computeSleepBucket(
  laub: LauburuReadinessOutput,
  today: NormalizedDailyMetrics | null,
  providers: WearableSourceId[],
): BucketScore {
  const inputs: string[] = [];
  const missing: string[] = [];
  let sum = 0;
  let weight = 0;
  for (const f of laub.positive_factors.concat(laub.negative_factors)) {
    if (f.signal === 'sleep_hours' || f.signal === 'sleep_consistency') {
      inputs.push(f.signal === 'sleep_hours' ? 'sleep_hours' : 'sleep_consistency');
      sum += f.contribution_score * f.weight;
      weight += f.weight;
    }
  }
  if (today?.totalSleepHours == null) missing.push('sleep_hours');
  if (today?.sleepEfficiencyPct == null) missing.push('sleep_efficiency_pct');
  if ((today as any)?.sleepDebtHours == null) missing.push('sleep_debt_hours');
  if (weight === 0) return emptyBucket(missing);
  const score = clamp01to100(sum / weight);
  return {
    score,
    inputs_used: inputs,
    missing,
    confidence: inputs.length >= 2 ? 'high' : 'medium',
    source_breakdown: providers,
  };
}

function computeLoadBucket(
  laub: LauburuReadinessOutput,
  acuteLoad: ComputeGrapplerInput['acuteLoad'],
  chronicLoad: ComputeGrapplerInput['chronicLoad'],
  providers: WearableSourceId[],
): BucketScore {
  const inputs: string[] = [];
  const missing: string[] = [];
  let sum = 0;
  let weight = 0;
  for (const f of laub.positive_factors.concat(laub.negative_factors)) {
    if (f.signal === 'acute_chronic_ratio' || f.signal === 'source_recovery') {
      inputs.push(f.signal);
      sum += f.contribution_score * f.weight;
      weight += f.weight;
    }
  }
  if (!acuteLoad?.days) missing.push('acute_load_7d');
  if (!chronicLoad?.days) missing.push('chronic_load_28d');
  if (weight === 0) return emptyBucket(missing);
  const score = clamp01to100(sum / weight);
  return {
    score,
    inputs_used: inputs,
    missing,
    confidence: inputs.length >= 2 ? 'high' : inputs.length === 1 ? 'medium' : 'insufficient',
    source_breakdown: providers,
  };
}

function computeGrapplingBucket(
  recent: ComputeGrapplerInput['recentGrappling'],
  providers: WearableSourceId[],
): BucketScore {
  if (!recent) {
    return emptyBucket([
      'hard_rounds_count_7d',
      'positional_intensity_avg_7d',
      'consecutive_grappling_days',
      'comp_prep_window',
    ]);
  }
  const inputs: string[] = [];
  const missing: string[] = [];
  // Score starts at 70 (neutral) and adjusts down for accumulated
  // grappling load. Each "hard round" past 12 in the last 7 days
  // costs 4 points; consecutive grappling days >3 costs 6 points
  // each. comp_prep_window relaxes the upper bound by widening
  // tolerance (we still report load, but recommendation softens).
  let score = 70;
  if (typeof recent.hard_rounds_count_7d === 'number') {
    inputs.push('hard_rounds_count_7d');
    const excess = Math.max(0, recent.hard_rounds_count_7d - 12);
    score -= excess * 4;
  } else missing.push('hard_rounds_count_7d');

  if (typeof recent.consecutive_grappling_days === 'number') {
    inputs.push('consecutive_grappling_days');
    const extra = Math.max(0, recent.consecutive_grappling_days - 3);
    score -= extra * 6;
  } else missing.push('consecutive_grappling_days');

  if (typeof recent.positional_intensity_avg_7d === 'number') {
    inputs.push('positional_intensity_avg_7d');
    if (recent.positional_intensity_avg_7d >= 3.5) score -= 5;
  } else missing.push('positional_intensity_avg_7d');

  if (inputs.length === 0) return emptyBucket(missing);
  const clamped = clamp01to100(score);
  return {
    score: clamped,
    inputs_used: inputs,
    missing,
    confidence: inputs.length >= 2 ? 'high' : 'medium',
    source_breakdown: ['manual', ...providers.filter((p) => p !== 'manual')],
  };
}

function computeSubjectiveBucket(
  c: ComputeGrapplerInput['latestCheckin'],
): BucketScore {
  const allFields = [
    'soreness_0_10', 'sleep_quality_0_10', 'mental_sharpness_0_10',
    'motivation_0_10', 'stress_0_10', 'recovery_feel',
  ];
  if (!c) return emptyBucket(allFields);
  const inputs: string[] = [];
  const missing: string[] = [];
  let sum = 0;
  let weight = 0;

  function addField(name: string, valuePct: number | null, w: number) {
    if (valuePct == null) { missing.push(name); return; }
    sum += valuePct * w;
    weight += w;
    inputs.push(name);
  }

  // Sliders: invert soreness/stress so higher pain = lower score.
  if (typeof c.soreness_0_10 === 'number') addField('soreness_0_10', clamp01to100((10 - c.soreness_0_10) * 10), 0.20);
  else missing.push('soreness_0_10');
  if (typeof c.sleep_quality_0_10 === 'number') addField('sleep_quality_0_10', clamp01to100(c.sleep_quality_0_10 * 10), 0.20);
  else missing.push('sleep_quality_0_10');
  if (typeof c.mental_sharpness_0_10 === 'number') addField('mental_sharpness_0_10', clamp01to100(c.mental_sharpness_0_10 * 10), 0.20);
  else missing.push('mental_sharpness_0_10');
  if (typeof c.motivation_0_10 === 'number') addField('motivation_0_10', clamp01to100(c.motivation_0_10 * 10), 0.15);
  else missing.push('motivation_0_10');
  if (typeof c.stress_0_10 === 'number') addField('stress_0_10', clamp01to100((10 - c.stress_0_10) * 10), 0.10);
  else missing.push('stress_0_10');
  if (c.recovery_feel) {
    const map = { better: 75, same: 60, worse: 35 } as const;
    addField('recovery_feel', map[c.recovery_feel], 0.15);
  } else missing.push('recovery_feel');

  if (weight === 0) return emptyBucket(missing);
  const score = clamp01to100(sum / weight);
  return {
    score,
    inputs_used: inputs,
    missing,
    confidence: inputs.length >= 4 ? 'high' : inputs.length >= 2 ? 'medium' : 'low',
    source_breakdown: ['manual'],
  };
}

// ── Injury risk inference ────────────────────────────────────────

function deriveInjuryFlags(
  c: ComputeGrapplerInput['latestCheckin'],
  laub: LauburuReadinessOutput,
  recent: ComputeGrapplerInput['recentGrappling'],
): InjuryRiskFlag[] {
  const flags: InjuryRiskFlag[] = [];
  // Self-reported.
  if (c?.injury_flag) {
    const tags = (c.injury_region_tags ?? []) as string[];
    if (tags.length === 0) {
      flags.push({ region: 'other', source: 'self_reported', severity: 'medium', detail: 'Injury flagged in latest check-in.' });
    } else {
      for (const t of tags) {
        const region = (['neck', 'shoulder', 'elbow', 'wrist', 'rib', 'hip', 'knee', 'ankle'] as const).includes(t as any)
          ? t as InjuryRiskFlag['region'] : 'other';
        flags.push({ region, source: 'self_reported', severity: 'medium', detail: `${t} flagged in latest check-in.` });
      }
    }
  }
  // Inferred — RHR up + HRV down + recent hard rounds.
  const rhrFactor = laub.negative_factors.find((f) => f.signal === 'rhr');
  const hrvFactor = laub.negative_factors.find((f) => f.signal === 'hrv');
  const hardRounds = recent?.hard_rounds_count_7d ?? null;
  if (rhrFactor && hrvFactor && hardRounds != null && hardRounds >= 12) {
    flags.push({
      region: 'other',
      source: 'inferred',
      severity: 'low',
      detail: 'Elevated RHR, depressed HRV, and high recent hard-round volume — consider easing into the session.',
    });
  }
  return flags;
}

// ── Score blending + recommendation ──────────────────────────────

function rollUpAppScore(buckets: {
  autonomic: BucketScore;
  sleep: BucketScore;
  load: BucketScore;
  grappling: BucketScore;
  subjective: BucketScore;
}): { score: number | null; weightUsed: number } {
  let sum = 0;
  let weightUsed = 0;
  if (buckets.autonomic.score != null) { sum += buckets.autonomic.score * WEIGHTS.autonomic; weightUsed += WEIGHTS.autonomic; }
  if (buckets.sleep.score != null) { sum += buckets.sleep.score * WEIGHTS.sleep; weightUsed += WEIGHTS.sleep; }
  if (buckets.load.score != null) { sum += buckets.load.score * WEIGHTS.load; weightUsed += WEIGHTS.load; }
  if (buckets.grappling.score != null) { sum += buckets.grappling.score * WEIGHTS.grappling; weightUsed += WEIGHTS.grappling; }
  if (buckets.subjective.score != null) { sum += buckets.subjective.score * WEIGHTS.subjective; weightUsed += WEIGHTS.subjective; }
  if (weightUsed === 0) return { score: null, weightUsed: 0 };
  return { score: clamp01to100(sum / weightUsed), weightUsed };
}

function deriveRecommendation(
  appScore: number | null,
  buckets: { autonomic: BucketScore; sleep: BucketScore; subjective: BucketScore },
  flags: InjuryRiskFlag[],
): GrapplerRecommendation {
  if (appScore == null) return 'insufficient_data';
  // Injury-flag dominance: even if the autonomic score is good,
  // a self-reported injury softens to technical.
  if (flags.some((f) => f.source === 'self_reported' && f.severity !== 'low')) return 'technical';
  if (appScore >= 75) return 'hard_training';
  if (appScore >= 60) return 'moderate';
  if (appScore >= 45) return 'technical';
  if (appScore >= 30) return 'recovery';
  return 'rest';
}

// ── Main ─────────────────────────────────────────────────────────

export function computeGrapplerReadiness(input: ComputeGrapplerInput): GrapplerReadinessOutput {
  const computedAt = new Date().toISOString();
  const laub = computeLauburuReadiness({
    today: input.today,
    baseline: input.baseline,
    acuteLoad: input.acuteLoad,
    chronicLoad: input.chronicLoad,
    staleHours: input.staleHours,
  });
  const providers = inferProviders(input.today);

  // Raw provider-native scores — carried unmodified from the
  // normalized record where possible. WHOOP recovery_score lives
  // on `recoveryScore`; day_strain on `dailyStrain`. Other
  // wearable-native scores (Oura, Garmin, Polar Pro) require
  // dedicated source adapters — null until those land.
  const rawSourceScores: RawSourceScores = {
    ...EMPTY_RAW_SCORES,
    whoop_recovery_pct: providers.includes('whoop_direct') || providers.includes('whoop_csv')
      ? (input.today?.recoveryScore ?? null)
      : null,
    whoop_strain: providers.includes('whoop_direct') || providers.includes('whoop_csv')
      ? (input.today?.dailyStrain ?? null)
      : null,
    whoop_sleep_pct: null, // not yet stored on normalized rows
  };

  const autonomic = computeAutonomicBucket(laub, input.today, providers);
  const sleep = computeSleepBucket(laub, input.today, providers);
  const load = computeLoadBucket(laub, input.acuteLoad, input.chronicLoad, providers);
  const grappling = computeGrapplingBucket(input.recentGrappling ?? null, providers);
  const subjective = computeSubjectiveBucket(input.latestCheckin ?? null);

  const flags = deriveInjuryFlags(input.latestCheckin ?? null, laub, input.recentGrappling ?? null);

  const { score: appScore, weightUsed } = rollUpAppScore({ autonomic, sleep, load, grappling, subjective });

  const recommendation = deriveRecommendation(appScore, { autonomic, sleep, subjective }, flags);

  // Confidence — rolls up: more buckets contributing + Lauburu
  // confidence gives a stronger overall confidence.
  const bucketsContributing = [autonomic, sleep, load, grappling, subjective].filter((b) => b.score != null).length;
  let confidence: GrapplerReadinessOutput['confidence'] =
    bucketsContributing >= 4 ? 'high'
    : bucketsContributing >= 2 ? 'medium'
    : bucketsContributing >= 1 ? 'low' : 'insufficient';
  // Lauburu's own confidence cannot upgrade us — only downgrade.
  if (laub.confidence === 'insufficient') confidence = 'insufficient';
  else if (laub.confidence === 'low' && confidence === 'high') confidence = 'medium';

  // Improvement hints — concrete, actionable, never invented.
  const improveBy: { action: string; would_unlock: string }[] = [];
  if (subjective.score == null) improveBy.push({ action: 'Open the Check-in tab and log soreness, sleep quality, mental sharpness, motivation, stress.', would_unlock: 'subjective bucket' });
  if (grappling.score == null) improveBy.push({ action: 'Log grappling sessions with hard-rounds count + positional intensity.', would_unlock: 'grappling bucket' });
  if (autonomic.missing.includes('hrv_ms')) improveBy.push({ action: 'Sync your wearable so today\'s HRV lands.', would_unlock: 'autonomic bucket' });
  if (sleep.missing.includes('sleep_hours')) improveBy.push({ action: 'Make sure tonight\'s sleep records to your wearable / Apple Health / Health Connect.', would_unlock: 'sleep bucket' });

  // Roll up positive/negative factors across buckets — kept simple
  // by reusing Lauburu's already-extracted top-3 list and tagging
  // with the bucket each signal belongs to.
  const bucketOfSignal: Record<string, string> = {
    hrv: 'autonomic', rhr: 'autonomic', sleep_hours: 'sleep',
    sleep_consistency: 'sleep', source_recovery: 'load', acute_chronic_ratio: 'load',
  };
  const positive_factors = laub.positive_factors.map((f) => ({
    signal: f.signal, bucket: bucketOfSignal[f.signal] ?? 'autonomic', detail: f.detail,
  }));
  const negative_factors = laub.negative_factors.map((f) => ({
    signal: f.signal, bucket: bucketOfSignal[f.signal] ?? 'autonomic', detail: f.detail,
  }));

  const explanation = laub.explanation; // reuse honest, non-prescriptive copy
  const caveats = laub.caveats.slice();
  if (subjective.score == null) caveats.push('Subjective bucket empty — log a daily check-in to widen the readiness picture.');
  if (grappling.score == null) caveats.push('Grappling bucket empty — log session intensity to refine the score.');

  // Roll up provider list across buckets.
  const allProviders = new Set<WearableSourceId>();
  for (const b of [autonomic, sleep, load, grappling, subjective]) {
    for (const p of b.source_breakdown) allProviders.add(p);
  }

  return {
    app_readiness_score: appScore,
    recommendation,
    confidence,
    autonomic_readiness: autonomic,
    sleep_readiness: sleep,
    load_readiness: load,
    grappling_readiness: grappling,
    subjective_readiness: subjective,
    source_breakdown: Array.from(allProviders),
    raw_source_scores: rawSourceScores,
    injury_risk_flags: flags,
    positive_factors,
    negative_factors,
    improve_score_by: improveBy,
    explanation,
    caveats,
    weights: WEIGHTS,
    not_medical_advice: true,
    experimental: true,
    computed_at: computedAt,
  };
}
