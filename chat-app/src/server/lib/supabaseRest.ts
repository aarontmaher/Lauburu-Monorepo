/**
 * Tiny Supabase REST client — service-role only, server-side only.
 *
 * Uses raw fetch against PostgREST so no `@supabase/supabase-js`
 * dependency is required in chat-app/package.json. The service role
 * key is read from env at request time; if missing, every helper
 * returns a no-op `{ ok: false }` so any caller is safe to fire-and-
 * forget without breaking the ingest path.
 *
 * NEVER expose the service role key to mobile / web bundles. This
 * file is `chat-app/`-scoped only.
 */

export interface SupabaseRestResult {
  ok: boolean;
  status?: number;
  error?: string;
}

function getEnv(): { url: string; key: string } | null {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  return { url, key };
}

/**
 * Upsert one or more rows into a public table using PostgREST's
 * `Prefer: resolution=merge-duplicates` semantics. The caller is
 * responsible for providing a unique-constraint-compatible payload
 * (e.g. for source_connection_state, `(user_id, source)`).
 *
 * Fire-and-forget safe: on any error (missing env, network, 4xx, 5xx)
 * returns `{ ok: false }` instead of throwing. Internal endpoint
 * routes can `void supabaseUpsert(...)` without try/catch.
 */
export async function supabaseUpsert(
  table: string,
  rows: Record<string, unknown>[],
  onConflict?: string,
): Promise<SupabaseRestResult> {
  const env = getEnv();
  if (!env) return { ok: false, error: 'supabase_env_missing' };
  if (!Array.isArray(rows) || rows.length === 0) return { ok: false, error: 'empty_payload' };
  try {
    const qs = onConflict ? `?on_conflict=${encodeURIComponent(onConflict)}` : '';
    const res = await fetch(`${env.url}/rest/v1/${table}${qs}`, {
      method: 'POST',
      headers: {
        apikey: env.key,
        Authorization: `Bearer ${env.key}`,
        'Content-Type': 'application/json',
        'Content-Profile': 'public',
        Prefer: 'resolution=merge-duplicates,return=minimal',
      },
      body: JSON.stringify(rows),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => '');
      return { ok: false, status: res.status, error: body.slice(0, 200) || `HTTP ${res.status}` };
    }
    return { ok: true, status: res.status };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'fetch_failed' };
  }
}

/**
 * Diagnostic — caller can branch on whether Supabase is reachable
 * to avoid printing scary "mirror not configured" copy when it IS
 * configured but a particular row failed.
 */
export function isSupabaseEnvConfigured(): boolean {
  return getEnv() !== null;
}
