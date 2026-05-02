/**
 * Mirror writer for `public.normalized_daily_metrics` in Supabase.
 *
 * Same trust model as `sourceConnectionStateSink.ts` — fire-and-forget,
 * UUID-gated, never blocks Railway primary writes. Authentication is
 * server-only via `SUPABASE_SERVICE_ROLE_KEY`. RLS policies on the
 * destination table enforce select-own; this service-role write path
 * bypasses RLS for ingest, but every row carries `user_id` so the
 * client read path remains scoped.
 *
 * Schema (migration 0001_durable_account_storage.sql):
 *   user_id uuid not null
 *   local_date date not null
 *   timezone text
 *   recovery_score numeric, hrv_ms numeric, rhr_bpm numeric,
 *   sleep_hours numeric, sleep_performance_pct numeric,
 *   day_strain numeric, active_kcal numeric,
 *   workout_count int, hiit_minutes numeric, grappling_minutes numeric,
 *   source_coverage jsonb, missing_fields jsonb,
 *   computed_from_hash text, computed_at timestamptz
 *   unique (user_id, local_date)
 *
 * Railway primary remains the source of truth. Supabase mirror is
 * redundancy + future cross-stack reads (web, exports). If env is
 * missing or Supabase rejects, primary writes are unaffected.
 *
 * NEVER expose the service role key to mobile / web bundles. This
 * file is `chat-app/`-scoped only.
 */

import { supabaseUpsert, type SupabaseRestResult } from './supabaseRest';
import type { NormalizedDailyMetrics } from '../../../../packages/shared/src/backend/contracts/normalized-daily.types';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Mirror one NormalizedDailyMetrics record into Supabase.
 *
 * `userId` MUST be the Supabase auth.users.id (UUID). For the dev
 * `dev-athlete` path or non-UUID athleteIds, this returns
 * `{ ok: false, error: 'user_id_not_uuid' }` and writes nothing —
 * primary Railway storage is unaffected.
 */
export async function mirrorNormalizedDay(
  userId: string | null,
  record: NormalizedDailyMetrics,
): Promise<SupabaseRestResult> {
  if (!userId || !UUID_RE.test(userId)) {
    return { ok: false, error: 'user_id_not_uuid' };
  }
  if (!record?.date) {
    return { ok: false, error: 'no_local_date' };
  }
  // Sleep performance % may live on either `sleepEfficiencyPct` or
  // `sleepPerformancePct` depending on source — Supabase column is
  // `sleep_performance_pct`. Prefer the explicit perf score; fall
  // back to efficiency where perf isn't reported.
  const sleepPerfPct: number | null =
    (record as any).sleepPerformancePct ?? record.sleepEfficiencyPct ?? null;

  // Provenance into source_coverage: which provider(s) contributed.
  const sourceCoverage = {
    provider: record.provider ?? null,
    record_ids: record.sourceRecordIds ?? [],
    refs: record.sourceRefs ?? [],
    completeness: record.completeness,
    source_age_hours: record.sourceAgeHours ?? null,
  };

  const row: Record<string, unknown> = {
    user_id: userId,
    local_date: record.date, // YYYY-MM-DD
    timezone: null, // mobile may pass IANA tz in a future extension
    recovery_score: numOrNull(record.recoveryScore),
    hrv_ms: numOrNull(record.hrvMs),
    rhr_bpm: numOrNull(record.restingHrBpm),
    sleep_hours: numOrNull(record.totalSleepHours),
    sleep_performance_pct: numOrNull(sleepPerfPct),
    day_strain: numOrNull(record.dailyStrain),
    active_kcal: numOrNull(record.activeCaloriesKcal),
    workout_count: typeof record.workoutCount === 'number' ? record.workoutCount : 0,
    hiit_minutes: null, // not yet tracked separately on NormalizedDailyMetrics
    grappling_minutes: null, // ditto — derive from grapplingSessionCount × avg
    source_coverage: sourceCoverage,
    missing_fields: record.missingFields ?? [],
    computed_from_hash: null,
    computed_at: record.updatedAt ?? new Date().toISOString(),
  };

  return supabaseUpsert('normalized_daily_metrics', [row], 'user_id,local_date');
}

function numOrNull(v: unknown): number | null {
  if (v == null) return null;
  if (typeof v !== 'number') return null;
  if (!Number.isFinite(v)) return null;
  return v;
}
