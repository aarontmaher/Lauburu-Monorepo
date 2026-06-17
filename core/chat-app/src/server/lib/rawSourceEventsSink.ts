/**
 * Mirror writer for `public.raw_source_events` in Supabase.
 *
 * Same trust model as `sourceConnectionStateSink` and
 * `normalizedMetricsSink` — fire-and-forget, UUID-gated, never blocks
 * Railway primary writes. Service-role key server-only.
 *
 * Schema (migration 0001_durable_account_storage.sql):
 *   user_id uuid not null
 *   source text not null
 *   source_record_id text not null
 *   source_record_type text not null
 *   local_date date
 *   started_at timestamptz
 *   ended_at timestamptz
 *   payload jsonb not null
 *   payload_hash text not null
 *   ingested_at timestamptz not null default now()
 *   provenance jsonb not null default '{}'::jsonb
 *   unique (user_id, source, source_record_id, source_record_type)
 *
 * Idempotent on `(user_id, source, source_record_id, source_record_type)`
 * via PostgREST resolution=merge-duplicates. Re-ingesting the same
 * record updates `ingested_at` + `payload_hash` but doesn't duplicate
 * rows.
 *
 * NEVER expose the service role key to mobile / web bundles.
 */

import { createHash } from 'crypto';
import { supabaseUpsert, type SupabaseRestResult } from './supabaseRest';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export interface MirrorRawEventInput {
  userId: string | null;
  /** One of: whoop / apple_health / health_connect / cronometer / polar /
   *  samsung / manual / hiit / grappling_session — same enum the
   *  source_connection_state.source check enforces. */
  source: string;
  /** Stable id from the source — for whoop daily, the cycleId; for
   *  apple_health daily, the YYYY-MM-DD; for hiit, the sessionId. */
  sourceRecordId: string;
  /** Domain qualifier within the source — e.g. 'daily', 'workout',
   *  'sleep', 'cycle', 'session'. Lets a source mirror multiple
   *  record types per (user, date) without collision. */
  sourceRecordType: string;
  localDate?: string | null;
  startedAt?: string | null;
  endedAt?: string | null;
  /** Raw source payload as stored on Railway primary. Stripped of any
   *  secrets/tokens before passing here. */
  payload: unknown;
  /** Optional caller-supplied provenance (e.g. file_hash for CSV
   *  imports). Default: empty object. */
  provenance?: Record<string, unknown>;
}

export async function mirrorRawSourceEvent(
  input: MirrorRawEventInput,
): Promise<SupabaseRestResult> {
  if (!input.userId || !UUID_RE.test(input.userId)) {
    return { ok: false, error: 'user_id_not_uuid' };
  }
  if (!input.source || !input.sourceRecordId || !input.sourceRecordType) {
    return { ok: false, error: 'missing_required_keys' };
  }
  // Hash the payload deterministically so the mirror table can detect
  // when content changed without storing the full blob in an index.
  const payloadJson = JSON.stringify(input.payload ?? {});
  const payloadHash = createHash('sha256').update(payloadJson).digest('hex');

  const row = {
    user_id: input.userId,
    source: input.source,
    source_record_id: input.sourceRecordId,
    source_record_type: input.sourceRecordType,
    local_date: input.localDate ?? null,
    started_at: input.startedAt ?? null,
    ended_at: input.endedAt ?? null,
    payload: input.payload ?? {},
    payload_hash: payloadHash,
    ingested_at: new Date().toISOString(),
    provenance: input.provenance ?? {},
  };
  return supabaseUpsert(
    'raw_source_events',
    [row],
    'user_id,source,source_record_id,source_record_type',
  );
}
