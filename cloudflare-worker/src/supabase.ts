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
  /**
   * Fetches the single-row envelope payload for tables keyed by
   * `id = 'current'`. Returns `null` on any failure — never throws.
   * Callers fall through to the placeholder. NEVER fabricate data.
   */
  fetchSingleRowPayload(table: string): Promise<unknown | null>;
  /**
   * Fetches every row for a key-per-row envelope (e.g.
   * connector_coder_lanes keyed by lane_id). Returns the raw payload
   * jsonb plus the row's lane_id / status so callers can synthesise
   * a CoderLanes aggregate.
   */
  fetchCoderLaneRows(): Promise<Array<{ lane_id: string; status: string; payload: unknown }> | null>;
  /**
   * Fetches the most recent N entries from connector_terminal_summary,
   * ordered by created_at desc.
   */
  fetchTerminalEntries(limit: number): Promise<unknown[] | null>;
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

  const headers = {
    apikey: key,
    Authorization: `Bearer ${key}`,
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };

  async function safeJson<T>(path: string): Promise<T | null> {
    try {
      const res = await fetch(`${url}/rest/v1/${path}`, { headers });
      if (!res.ok) return null;
      return (await res.json()) as T;
    } catch {
      return null;
    }
  }

  return {
    configured: true,
    config,
    async ping() {
      try {
        const res = await fetch(`${url}/rest/v1/`, { headers });
        if (res.ok) return { ok: true } as const;
        const body = await res.text();
        return { ok: false, status: res.status, body: body.slice(0, 200) } as const;
      } catch (err) {
        return { ok: false, status: 0, body: err instanceof Error ? err.message : 'unknown error' } as const;
      }
    },
    async fetchSingleRowPayload(table: string) {
      const rows = await safeJson<Array<{ payload: unknown }>>(
        `${encodeURIComponent(table)}?id=eq.current&select=payload&limit=1`,
      );
      if (!rows || rows.length === 0) return null;
      return rows[0]?.payload ?? null;
    },
    async fetchCoderLaneRows() {
      return safeJson<Array<{ lane_id: string; status: string; payload: unknown }>>(
        'connector_coder_lanes?select=lane_id,status,payload&order=lane_id.asc',
      );
    },
    async fetchTerminalEntries(limit: number) {
      const safeLimit = Math.max(1, Math.min(50, Math.floor(limit)));
      const rows = await safeJson<Array<{ payload: unknown }>>(
        `connector_terminal_summary?select=payload&order=created_at.desc&limit=${safeLimit}`,
      );
      if (!rows) return null;
      return rows.map((r) => r.payload);
    },
  };
}

/**
 * Schema requirements the Worker would need before it can start
 * issuing reads against Supabase for each connector route. Surfaced
 * in the response payload when `supabaseConfigured` is false so
 * consumers can self-document why the data is provisional.
 *
 * Tables follow a thin envelope shape (id / scope / payload jsonb /
 * source / created_at / updated_at), defined in
 * `supabase/migrations/0003_connector_status_tables.sql`. The TS
 * shapes inside `payload` come from
 * `chat-app/src/server/types/connector.ts`.
 */
export const CONNECTOR_SCHEMA_REQUIREMENTS = {
  work_status: {
    table: 'connector_work_status',
    envelope: ['id', 'generated_at', 'updated_at', 'source', 'payload (jsonb = WorkStatus)'],
    migration: 'supabase/migrations/0003_connector_status_tables.sql',
    notes: 'Single-row envelope (id = "current"). Owner / bridge upsert via service-role key.',
  },
  coder_lanes: {
    table: 'connector_coder_lanes',
    envelope: [
      'lane_id (pk, enum: claude|codex|claude_chat|chatgpt|cowork)',
      'generated_at',
      'updated_at',
      'source',
      'payload (jsonb = CoderLaneRow)',
    ],
    migration: 'supabase/migrations/0003_connector_status_tables.sql',
    notes:
      'Bridge writer (scripts/bridge-snapshot-lanes.sh + future POST consumer) upserts one row per lane.',
  },
  build_status: {
    table: 'connector_build_status',
    envelope: ['id', 'generated_at', 'updated_at', 'source', 'payload (jsonb = BuildStatus)'],
    migration: 'supabase/migrations/0003_connector_status_tables.sql',
    notes: 'Single-row envelope. Owner-tap or release-workflow updates.',
  },
  handoff: {
    table: 'connector_handoff',
    envelope: ['id', 'generated_at', 'updated_at', 'source', 'payload (jsonb = Handoff)'],
    migration: 'supabase/migrations/0003_connector_status_tables.sql',
    notes:
      'Single-row envelope. Owner-tap only; safeToBuild flip to true requires owner confirmation.',
  },
  terminal_summary: {
    table: 'connector_terminal_summary',
    envelope: ['id (bigserial)', 'lane_id', 'generated_at', 'updated_at', 'source', 'payload (jsonb = TerminalSummaryEntry)'],
    migration: 'supabase/migrations/0003_connector_status_tables.sql',
    notes: 'Append-only event log. Cap 50 rows via retention sweep at the bottom of the migration file.',
  },
} as const;

export type ConnectorRouteKey = keyof typeof CONNECTOR_SCHEMA_REQUIREMENTS;
