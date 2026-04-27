/**
 * Mirror writer for `public.source_connection_state` in Supabase.
 *
 * Fire-and-forget: callers should `void recordSourceConnectionState(...)`
 * so that Railway-side primary writes never block on the Supabase mirror.
 * On any error (env missing, network, RLS, schema), the underlying
 * `supabaseUpsert` returns `{ ok: false }` and we swallow it.
 *
 * Schema (see supabase/migrations/0001_durable_account_storage.sql):
 *   source IN ('whoop','apple_health','health_connect','cronometer',
 *              'polar','samsung','manual','hiit','grappling_session')
 *   status IN ('connected','stale','missing_permission','auth_required',
 *              'partial','error','not_connected')
 *   unique (user_id, source)
 *
 * NOTE: `user_id` here MUST be the Supabase auth.users.id (UUID) — not
 * the athlete-memory athleteId used internally by chat-app. Callers
 * that only have an athleteId should look up the corresponding auth
 * user_id, or pass `null` to no-op safely.
 */

import { supabaseUpsert, type SupabaseRestResult } from './supabaseRest';

export type SourceName =
  | 'whoop'
  | 'apple_health'
  | 'health_connect'
  | 'cronometer'
  | 'polar'
  | 'samsung'
  | 'manual'
  | 'hiit'
  | 'grappling_session';

export type SourceStatus =
  | 'connected'
  | 'stale'
  | 'missing_permission'
  | 'auth_required'
  | 'partial'
  | 'error'
  | 'not_connected';

export interface RecordSourceConnectionStateInput {
  userId: string | null;
  source: SourceName;
  status: SourceStatus;
  lastIngestedAt?: string | null;
  lastSuccessAt?: string | null;
  lastFailureAt?: string | null;
  lastFailureReason?: string | null;
  metadata?: Record<string, unknown>;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function recordSourceConnectionState(
  input: RecordSourceConnectionStateInput,
): Promise<SupabaseRestResult> {
  if (!input.userId || !UUID_RE.test(input.userId)) {
    return { ok: false, error: 'user_id_not_uuid' };
  }
  const row = {
    user_id: input.userId,
    source: input.source,
    status: input.status,
    last_ingested_at: input.lastIngestedAt ?? null,
    last_success_at: input.lastSuccessAt ?? null,
    last_failure_at: input.lastFailureAt ?? null,
    last_failure_reason: input.lastFailureReason ?? null,
    metadata: input.metadata ?? {},
    updated_at: new Date().toISOString(),
  };
  return supabaseUpsert('source_connection_state', [row], 'user_id,source');
}
