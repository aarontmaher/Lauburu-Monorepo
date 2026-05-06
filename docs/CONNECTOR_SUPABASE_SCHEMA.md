# Connector Supabase schema — required tables for live reads

This is the schema spec the Cloudflare Worker
(`cloudflare-worker/src/supabase.ts`) needs in order to read live
connector state from Supabase. Until these tables exist and the
`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` secrets are set on
the Worker, the connector routes return placeholder payloads
with a `dataSource.schemaRequired` field that mirrors this doc.

Companion to:
- `docs/CLOUDFLARE_MIGRATION.md` (Railway deprecated, Cloudflare
  active, Supabase = state layer)
- `docs/CHATGPT_CONNECTOR_STATE_CONTRACT.md` (5-object spec)
- `docs/CONNECTOR_SANITIZATION_RULES.md` (write-side rules)
- `chat-app/src/server/types/connector.ts` (TS interfaces)

Updated 2026-05-06.

## Why Supabase

The Worker is stateless. The five connector objects (work_status,
coder_lanes, build_status, handoff, terminal_summary) need a
durable home that survives Worker redeploys, supports owner-tap
upserts, and is reachable from both the Worker (read) and the
local tmux bridge (write, via the future
`POST /api/athlete-memory/admin/lane-status` consumer route).

Supabase already hosts the auth + per-user health rows, so adding
connector tables to the same project keeps one auth surface, one
backup story, one row-level-security model.

## Auth model

- Worker reads use the **service-role key** (server-side only;
  never bundled into the mobile app).
- Bridge writes also use the service-role key (the bridge runs on
  Aaron's Mac; the key is held in `.dev.vars` locally and in
  Cloudflare secrets remotely).
- Mobile app NEVER reads these tables directly — it only sees
  the redacted JSON payloads returned by the Worker after
  admin-token gating.

## Required tables

All tables live in the `public` schema unless noted. All `_at`
columns are `timestamptz default now()`. All single-row tables use
`id text primary key default 'current' check (id = 'current')` so
upserts are idempotent and there's never a race over which row to
read.

### `connector_work_status` (single row)

```sql
create table public.connector_work_status (
  id text primary key default 'current' check (id = 'current'),
  updated_at timestamptz not null default now(),
  current_priority text not null check (char_length(current_priority) <= 280),
  current_blocker text check (current_blocker is null or char_length(current_blocker) <= 280),
  next_action text check (next_action is null or char_length(next_action) <= 280),
  live_status jsonb not null,    -- WorkStatusLiveStatus shape
  repo_status jsonb not null     -- WorkStatusRepoStatus shape
);

alter table public.connector_work_status enable row level security;
-- service-role bypasses RLS; no policies needed for non-service callers.
```

### `connector_coder_lanes` (one row per lane)

```sql
create type connector_lane_id as enum ('claude', 'codex', 'claude_chat', 'chatgpt', 'cowork');
create type connector_lane_status as enum ('idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done');
create type connector_typecheck_result as enum ('pass', 'fail', 'unknown');

create table public.connector_coder_lanes (
  lane_id connector_lane_id primary key,
  updated_at timestamptz not null default now(),
  status connector_lane_status not null default 'idle',
  last_seen_at timestamptz,
  current_prompt_id text,
  last_prompt_id text,
  last_summary text check (last_summary is null or char_length(last_summary) <= 1200),
  last_commit text,
  last_typecheck_result connector_typecheck_result,
  dirty_files jsonb not null default '[]'::jsonb,
  next_prompt text
);

alter table public.connector_coder_lanes enable row level security;
```

### `connector_build_status` (single row)

```sql
create table public.connector_build_status (
  id text primary key default 'current' check (id = 'current'),
  updated_at timestamptz not null default now(),
  android jsonb not null,    -- AndroidBuildStatus shape
  ios jsonb not null         -- IosBuildStatus shape
);

alter table public.connector_build_status enable row level security;
```

### `connector_handoff` (single row)

```sql
create table public.connector_handoff (
  id text primary key default 'current' check (id = 'current'),
  updated_at timestamptz not null default now(),
  latest_claude_prompt text,
  latest_codex_prompt text,
  manual_steps jsonb not null default '[]'::jsonb,
  do_not_touch jsonb not null default '[]'::jsonb,
  safe_to_build boolean not null default false,
  safe_to_build_reason text not null default ''
);

alter table public.connector_handoff enable row level security;
```

### `connector_terminal_summary` (append-only, capped 50 rows total)

```sql
create table public.connector_terminal_summary (
  id bigserial primary key,
  inserted_at timestamptz not null default now(),
  lane_id connector_lane_id not null,
  at timestamptz not null,
  summary text not null check (char_length(summary) <= 1200),
  verification text not null check (char_length(verification) <= 240),
  next_action text not null check (char_length(next_action) <= 240),
  exit_code int
);

create index connector_terminal_summary_lane_at
  on public.connector_terminal_summary (lane_id, inserted_at desc);

alter table public.connector_terminal_summary enable row level security;
```

A nightly cron (Supabase pg_cron extension) trims rows beyond 50
total, ordered by `inserted_at desc`:

```sql
delete from public.connector_terminal_summary
where id not in (
  select id from public.connector_terminal_summary
  order by inserted_at desc
  limit 50
);
```

## Required env on the Worker

Set both via `wrangler secret put` only after the tables above
exist:

```sh
cd cloudflare-worker
npx wrangler secret put SUPABASE_URL --name lauburu-mcp-preview
# Paste: https://YOUR-PROJECT.supabase.co

npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY --name lauburu-mcp-preview
# Paste the service_role JWT from Supabase → Project Settings → API.
```

The adapter validates:
- `SUPABASE_URL` matches `https://[a-z0-9-]+.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY` starts with `eyJ` (JWT shape)

Anything else returns a typed `SupabaseUnavailable` record and the
Worker falls back to the placeholder payload — never fabricates
data.

## Verification curl

```sh
export MCP_WORKER_URL="https://lauburu-mcp-preview.lauburu-aaron.workers.dev"

curl -sS -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$MCP_WORKER_URL/supabase/health" | jq

# Before secrets:
# {
#   "supabaseConfigured": false,
#   ...
#   "supabase": {
#     "configured": false,
#     "reason": "env_missing",
#     "schemaRequirements": { ... mirror of this doc ... }
#   }
# }

# After secrets + tables:
# {
#   "supabaseConfigured": true,
#   ...
#   "supabase": {
#     "configured": true,
#     "host": "https://YOUR-PROJECT.supabase.co",
#     "ping": { "ok": true }
#   }
# }
```

## Local artifact fallback (Stage 1)

Until the tables above exist and the secrets are set, the
Cloudflare Worker connector routes return placeholder payloads
with the `dataSource.schemaRequired` field. The local tmux bridge
(`scripts/bridge-snapshot-lanes.sh`) writes the same
schema-compliant payloads to disk so ChatGPT / Codex / Claude
can read them today via the local filesystem:

```
data/agent-status/lanes/coder_lanes.json       # CoderLanes
data/agent-status/lanes/<laneId>.json          # CoderLaneRow per lane
data/agent-status/lanes/terminal_summary.json  # TerminalSummary
data/agent-status/lanes/handoff.json           # Handoff
```

These are `gitignored` (per-run snapshots; never committed). Run
`./scripts/bridge-snapshot-lanes.sh` to refresh. Validate against
the canonical types with:

```sh
cd chat-app
npx tsx src/server/scripts/test-bridge-artifacts.ts
```

When the tables land and the secrets are set, the Worker reads
the same shapes from Supabase; the local artifacts become a
debug-only mirror.

## What this doc is NOT

- A migration script. SQL above is the spec; running it is
  Aaron's manual step (Supabase dashboard SQL editor or
  `supabase` CLI).
- A complete RLS policy set. RLS is enabled on every table; the
  Worker uses the service-role key which bypasses RLS, so per-row
  policies aren't required for connector reads. If a future
  per-user route needs read access without the service-role key,
  policies land in a separate batch.
- A backup or retention plan. Standard Supabase backups apply.
  Connector data is small (≤6 rows + ≤50 terminal entries); no
  custom retention needed.

## Anti-rules

- **No raw athlete health values in any connector_* table.**
  Health rows live in `normalized_daily_metrics` /
  `raw_source_events` and are owner-token-gated by the existing
  Railway-era routes (now read by chat-app, soon by the Worker).
  Connector tables hold owner-state metadata only.
- **No OAuth tokens.** Provider tokens stay in
  `source_connection_state` (or its successor); never duplicate
  into connector_*.
- **No env secret values.** Even paths to `.env` files are masked
  per `docs/CONNECTOR_SANITIZATION_RULES.md`.
- **No write paths until the consumer route lands.** The bridge
  writes locally to `data/agent-status/lanes/*.json` today; the
  Supabase upsert path requires the
  `LaneStatusWritePayload` route in chat-app or the Worker, which
  is a separate batch.
