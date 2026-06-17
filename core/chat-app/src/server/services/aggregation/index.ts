/**
 * Anonymized cohort aggregation (skeleton).
 *
 * INACTIVE BY DEFAULT. This module compiles and exports stable
 * functions, but the data path is gated on
 *   (a) `normalizedMetricsStore` reachability — the durable
 *       `normalized_daily_metrics` Supabase table needs to be applied
 *       (`supabase/migrations/0001_durable_account_storage.sql`).
 *   (b) per-user explicit consent flag (`aggregation_consent_at`).
 *   (c) cohort minimum size `K_MIN_COHORT` for any output to surface.
 *
 * Until those preconditions are met every public function here returns
 * `{ ok: false, reason: 'aggregation_not_ready' }`. Coach + mobile can
 * call these safely without changing behaviour: the response is simply
 * inert until the data layer is live.
 *
 * Privacy rules (enforced at every layer below):
 *   - Aggregation only ever touches `normalized_daily_metrics`. Never
 *     `athlete_memory`, `interpreted_*`, raw_source_events.
 *   - Output is bucketed/percentile only — never per-user values, never
 *     names/emails/exact timestamps/device IDs.
 *   - Minimum cohort size of K_MIN_COHORT (default 10) before any
 *     bucket is exposed. Below that → empty response.
 *   - User must have set `aggregation_consent_at` before their rows
 *     contribute. Anyone can opt out at any time; rows from opt-out
 *     users are excluded from the next aggregation pass.
 *   - No cross-user joins return individual baselines. Only counts +
 *     percentile bins per metric per cohort bucket.
 */

export const K_MIN_COHORT = 10;

/** Buckets coarse enough to keep small cohorts non-identifying. */
export type CohortBucket =
  | 'all'
  | 'training_high_freq'   // ≥4 sessions / week recent
  | 'training_low_freq'    // ≤2 sessions / week recent
  | 'sleep_high'           // ≥7h avg recent
  | 'sleep_low';           // <6h avg recent

export type AggregationMetric =
  | 'recovery_score'
  | 'hrv_ms'
  | 'rhr_bpm'
  | 'sleep_hours'
  | 'day_strain'
  | 'active_kcal';

export interface AggregationReadiness {
  /** True only when the normalized table is reachable + at least
   *  K_MIN_COHORT consenting users have a row in the requested
   *  metric/bucket window. */
  ready: boolean;
  reason?: 'aggregation_not_ready' | 'cohort_below_threshold' | 'metric_unavailable';
  cohortSize?: number;
}

export interface PercentileBins {
  metric: AggregationMetric;
  bucket: CohortBucket;
  cohortSize: number;
  /** p10 / p25 / p50 / p75 / p90. Always rounded — no high-precision
   *  values that could re-identify a small cohort. */
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
}

export type AggregationResult<T> =
  | { ok: true; data: T }
  | { ok: false; reason: AggregationReadiness['reason']; cohortSize?: number };

/** Probe whether the durable normalized table is reachable. Returns
 *  false until the migration is applied + the chat-app process has a
 *  Supabase service-role connection configured. The skeleton is
 *  permanently false; the real implementation will check a runtime
 *  config flag like `process.env.AGGREGATION_ENABLED === '1'` plus a
 *  trivial `select 1 from public.normalized_daily_metrics limit 1`. */
export function isAggregationReady(): AggregationReadiness {
  // Skeleton — keep returning not-ready so no stale path can claim
  // success. The Railway service may have AGGREGATION_ENABLED=1
  // already set as forward-prep, but that env flag alone MUST NOT
  // activate aggregation. Activation requires (a) consent migration
  // 0003 applied + per-user consent timestamp populated, (b) mobile
  // consent UI shipped, (c) this function replaced with a real
  // probe (env flag + Supabase reachability + cohort >= K_MIN_COHORT
  // check). Until that whole chain is in place, every public method
  // here returns inert results to protect privacy.
  return { ready: false, reason: 'aggregation_not_ready' };
}

/** Per-user opt-in helper. The real implementation reads the
 *  athlete_profiles.aggregation_consent_at column (or a new column
 *  added in a follow-up migration). Skeleton denies everything. */
export function userHasAggregationConsent(_athleteId: string): boolean {
  return false;
}

/**
 * Compute bucketed percentile bins for a metric. Skeleton always
 * returns `{ ok: false, reason: 'aggregation_not_ready' }` until the
 * durable normalized table is reachable. When activated, it must:
 *   1. Filter rows to consenting users only.
 *   2. Bucket users by recent training/sleep pattern.
 *   3. For each (metric × bucket), require cohortSize >= K_MIN_COHORT.
 *   4. Compute p10/p25/p50/p75/p90 with rounded values.
 *   5. Drop any bucket below threshold from the response entirely.
 */
export async function getCohortPercentiles(
  _input: { metric: AggregationMetric; bucket: CohortBucket; windowDays: number },
): Promise<AggregationResult<PercentileBins>> {
  const ready = isAggregationReady();
  if (!ready.ready) {
    return { ok: false, reason: ready.reason ?? 'aggregation_not_ready' };
  }
  // Real implementation goes here. Until then, never return data.
  return { ok: false, reason: 'aggregation_not_ready' };
}

/**
 * Phrasing helper for Coach. Always returns the cautious anonymized
 * framing — never includes per-user values, never says "users like
 * you did X" without a cohort size. Returns null if not ready.
 */
export function describeCohort(p: PercentileBins | null): string | null {
  if (!p || p.cohortSize < K_MIN_COHORT) return null;
  const median = p.p50 != null ? `~${p.p50}` : null;
  if (median == null) return null;
  return `In the anonymized test cohort (n=${p.cohortSize}), ${p.metric} median is ${median}.`;
}
