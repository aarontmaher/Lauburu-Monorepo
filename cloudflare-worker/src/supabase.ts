/**
 * Supabase adapter for the Lauburu MCP Cloudflare Worker.
 *
 * Stage of build-out: SCAFFOLD ONLY.
 *
 * The Worker is the active replacement for the deprecated Railway
 * backend. Supabase is the durable state layer; this module is the
 * single point through which the Worker reads it. Today the adapter
 * only reports configuration state — no table reads — because the
 * connector-specific tables (`connector_lanes`, `connector_handoff`,
 * `connector_build_status`, `connector_work_status`) do not exist
 * yet. See `docs/CONNECTOR_SUPABASE_SCHEMA.md` for the schema spec
 * the next batch must land before this adapter starts issuing reads.
 *
 * Rules:
 *   - All reads use the service-role key. Never bundle that key
 *     into the mobile app.
 *   - Read-only. Writes go through dedicated owner-confirmed
 *     routes once `LaneStatusWritePayload` etc are wired.
 *   - On any failure (network, schema mismatch, permission), the
 *     adapter returns a typed error and callers fall through to
 *     the placeholder payload. NEVER fabricate data.
 */

import type { Env } from './worker-env';

export interface SupabaseConfig {
  url: string;
  serviceRoleKey: string;
}

export interface SupabaseUnavailable {
  configured: false;
  reason:
    | 'env_missing'
    | 'env_url_invalid'
    | 'env_key_invalid';
  message: string;
}

export interface SupabaseAdapter {
  configured: true;
  config: SupabaseConfig;
  /** Pings PostgREST `/rest/v1/` to confirm reachability + auth. */
  ping(): Promise<{ ok: true } | { ok: false; status: number; body: string }>;
}

/**
 * Returns either a configured adapter or an explicit unavailable
 * record. Callers MUST handle the `configured: false` branch and
 * fall through to placeholder payloads — never fabricate data.
 */
export function getSupabaseAdapter(env: Env): SupabaseAdapter | SupabaseUnavailable {
  const url = env.SUPABASE_URL?.trim() ?? '';
  const key = env.SUPABASE_SERVICE_ROLE_KEY?.trim() ?? '';

  if (!url || !key) {
    return {
      configured: false,
      reason: 'env_missing',
      message:
        'Supabase env vars not set on this Worker. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY via `wrangler secret put` once the connector tables in docs/CONNECTOR_SUPABASE_SCHEMA.md exist.',
    };
  }

  if (!/^https:\/\/[a-z0-9\-]+\.supabase\.co$/i.test(url)) {
    return {
      configured: false,
      reason: 'env_url_invalid',
      message: 'SUPABASE_URL is set but does not match the expected Supabase host shape.',
    };
  }

  if (!key.startsWith('eyJ')) {
    return {
      configured: false,
      reason: 'env_key_invalid',
      message: 'SUPABASE_SERVICE_ROLE_KEY does not look like a Supabase JWT (expected `eyJ…`).',
    };
  }

  const config: SupabaseConfig = { url, serviceRoleKey: key };

  return {
    configured: true,
    config,
    async ping() {
      try {
        const res = await fetch(`${url}/rest/v1/`, {
          headers: {
            apikey: key,
            Authorization: `Bearer ${key}`,
          },
        });
        if (res.ok) return { ok: true } as const;
        const body = await res.text();
        return { ok: false, status: res.status, body: body.slice(0, 200) } as const;
      } catch (err) {
        return { ok: false, status: 0, body: err instanceof Error ? err.message : 'unknown error' } as const;
      }
    },
  };
}

/**
 * Schema requirements the Worker would need before it can start
 * issuing reads against Supabase for each connector route. Surfaced
 * in the response payload when `supabaseConfigured` is false so
 * consumers can self-document why the data is provisional.
 */
export const CONNECTOR_SCHEMA_REQUIREMENTS = {
  work_status: {
    table: 'connector_work_status',
    columns: [
      'id (text, single-row pk = "current")',
      'updated_at (timestamptz)',
      'current_priority (text, ≤ 280)',
      'current_blocker (text, ≤ 280, nullable)',
      'next_action (text, ≤ 280)',
      'live_status (jsonb)',
      'repo_status (jsonb)',
    ],
    notes: 'Single-row table. Owner upsert via service-role key.',
  },
  coder_lanes: {
    table: 'connector_coder_lanes',
    columns: [
      'lane_id (text pk, enum: claude|codex|claude_chat|chatgpt|cowork)',
      'updated_at (timestamptz)',
      'status (text, enum: idle|working|blocked|needs_user|needs_review|done)',
      'last_seen_at (timestamptz, nullable)',
      'current_prompt_id (text, nullable)',
      'last_prompt_id (text, nullable)',
      'last_summary (text ≤ 1200, nullable)',
      'last_commit (text, nullable)',
      'last_typecheck_result (text, enum: pass|fail|unknown, nullable)',
      'dirty_files (jsonb array of repo-relative paths)',
      'next_prompt (text, nullable)',
    ],
    notes:
      'Bridge writer (scripts/bridge-snapshot-lanes.sh + future POST consumer) upserts one row per lane.',
  },
  build_status: {
    table: 'connector_build_status',
    columns: [
      'id (text, single-row pk = "current")',
      'updated_at (timestamptz)',
      'android (jsonb, AndroidBuildStatus shape)',
      'ios (jsonb, IosBuildStatus shape)',
    ],
    notes: 'Owner-tap or release-workflow updates.',
  },
  handoff: {
    table: 'connector_handoff',
    columns: [
      'id (text, single-row pk = "current")',
      'updated_at (timestamptz)',
      'latest_claude_prompt (text, nullable)',
      'latest_codex_prompt (text, nullable)',
      'manual_steps (jsonb array of strings)',
      'do_not_touch (jsonb array of strings)',
      'safe_to_build (boolean)',
      'safe_to_build_reason (text)',
    ],
    notes: 'Owner-tap only; safeToBuild flip to true requires owner confirmation.',
  },
} as const;

export type ConnectorRouteKey = keyof typeof CONNECTOR_SCHEMA_REQUIREMENTS;
