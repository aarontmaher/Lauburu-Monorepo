# Connector Supabase schema — required tables for live reads

This is the schema spec the Cloudflare Worker
(`cloudflare-worker/src/supabase.ts`) needs in order to read live
connector state from Supabase. Until these tables exist and the
`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` secrets are set on
the Worker, the connector routes return placeholder payloads
with a `dataSource.schemaRequired` field that mirrors this doc.

**Canonical migration:**
[`supabase/migrations/0003_connector_status_tables.sql`](../supabase/migrations/0003_connector_status_tables.sql)
— this is the SQL Aaron pastes into the Supabase SQL editor (or
runs via `npx supabase db push`). Do not hand-write SQL elsewhere.

Companion to:
- `docs/CLOUDFLARE_MIGRATION.md` (Railway deprecated, Cloudflare
  active, Supabase = state layer)
- `docs/CHATGPT_CONNECTOR_STATE_CONTRACT.md` (5-object spec)
- `docs/CONNECTOR_SANITIZATION_RULES.md` (write-side rules)
- `chat-app/src/server/types/connector.ts` (TS interfaces)

Updated 2026-05-07.

## Why Supabase, why envelope shape

The Worker is stateless. The five connector objects (work_status,
coder_lanes, build_status, handoff, terminal_summary) need a
durable home that survives Worker redeploys, supports owner-tap
upserts, and is reachable from both the Worker (read) and the
local tmux bridge (write, via the future
`POST /api/athlete-memory/admin/lane-status` consumer route).

These tables intentionally use a thin **envelope shape**:

| Column | Purpose |
|---|---|
| `id` (or `lane_id`, or `bigserial`) | primary key |
| `generated_at` timestamptz | when the writer assembled the snapshot |
| `updated_at` timestamptz default `now()` | when the row was last upserted |
| `source` text default `'bridge'` | who wrote the row (`bridge`/`owner`/`worker`/`cli`) |
| `payload` jsonb not null | the typed connector payload |

The TS shapes in `chat-app/src/server/types/connector.ts` are the
source of truth for what's INSIDE `payload`. Keeping the SQL
column set thin lets the connector contract evolve (adding a new
field to `WorkStatus`) without a schema migration; the Worker and
the bridge both read/write through the typed payload.

These tables are **owner / control-centre status** — they
must not contain raw athlete health values, OAuth tokens, env
secrets, or any per-user PII. Athlete data lives in
`normalized_daily_metrics`, `raw_source_events`,
`source_connection_state`, etc., which are outside this doc.

## Safety model

The Supabase service-role key **bypasses RLS**. Enabling RLS on
these tables does NOT gate service-role access. Real safety
comes from these layered controls, not from RLS:

1. **Worker-only secret.** `SUPABASE_SERVICE_ROLE_KEY` lives only
   as a Cloudflare Worker secret (set via `wrangler secret put`),
   and locally in `.dev.vars` (gitignored). It is NEVER bundled
   into the mobile app. The mobile `EXPO_PUBLIC_*` env layer is
   designed to leak to clients; the service-role key is on the
   opposite side of that boundary.
2. **Strict route allowlist.** The Worker exposes exactly five
   connector reads — `/api/work_status`, `/api/coder_lanes`,
   `/api/build_status`, `/api/handoff`, `/api/terminal_summary`.
   Every other path returns 404. There is no SQL passthrough,
   no `query` parameter, no path-traversal opportunity.
3. **No arbitrary Supabase queries.** The adapter in
   `cloudflare-worker/src/supabase.ts` exposes only hardcoded
   `fetch<TableName>` helpers that target the four named
   `connector_*` tables. There is no public method that accepts
   a free-form SQL string or a caller-supplied table name.
4. **Connector-table-only code paths.** All Supabase calls in
   the Worker target the `connector_*` set; there is no read
   path to `auth.users`, `normalized_daily_metrics`,
   `raw_source_events`, or any other user table. A future need
   for those reads requires a new adapter method + doc commit.
5. **Admin-token gate on every connector route.** Even with
   the URL allowlist, every route requires the
   `x-athlete-memory-token` header to match the Worker's
   `ATHLETE_MEMORY_API_TOKEN` secret. Missing/wrong → 403 with
   no body leak.

RLS is still **enabled with no policies** as defence-in-depth: if
a future caller swaps the Worker's service-role key for an
`anon` key by mistake, RLS denies the read instead of silently
returning rows.

The mobile app NEVER reads these tables directly — it only sees
the redacted JSON payloads returned by the Worker after
admin-token gating.

## Tables

### `connector_work_status` (single row, `id = 'current'`)

Holds the `WorkStatus` payload (currentPriority / currentBlocker /
liveStatus / repoStatus / nextAction etc.).

### `connector_coder_lanes` (one row per `lane_id`)

Holds one `CoderLaneRow` payload per lane. The `lane_id` column
is the primary key (the fixed-key equivalent of `id = 'current'`)
and is locked to the `LaneId` enum via a `check` constraint.
Status lives inside the payload jsonb; the Worker filters in
code.

### `connector_build_status` (single row)

Holds the `BuildStatus` payload (Android + iOS release rows).

### `connector_handoff` (single row)

Holds the `Handoff` payload. The `safeToBuild` flag inside the
payload is owner-set only — bridge writers MUST NOT flip it to
`true`.

### `connector_terminal_summary` (append-only)

Holds `TerminalSummaryEntry` rows. Capped at 50 total rows via a
retention sweep at the bottom of the migration file (commented
out by default; uncomment + run via pg_cron or attach to a
Supabase scheduled task).

Index: `connector_terminal_summary_lane_recent (lane_id, generated_at desc)`.

## Required env on the Worker

Set both via `wrangler secret put` only after the migration above
has been applied:

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

Until the migration above is applied and the secrets are set, the
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

- A migration script. The SQL lives in
  `supabase/migrations/0003_connector_status_tables.sql`.
  Running it is Aaron's manual step (Supabase dashboard SQL
  editor or `supabase` CLI). This doc describes the shape; the
  migration enforces it.
- A complete RLS policy set. RLS is enabled on every table; the
  Worker uses the service-role key which bypasses RLS, so per-row
  policies aren't required for connector reads. If a future
  per-user route needs read access without the service-role key,
  policies land in a separate batch.
- A backup or retention plan. Standard Supabase backups apply.
  Connector data is small (≤4 single-row tables + per-lane rows
  + ≤50 terminal entries); no custom retention needed beyond the
  retention sweep documented at the bottom of the migration file.

## Anti-rules

- **No raw athlete health values in any connector_* table.**
  Health rows live in `normalized_daily_metrics` /
  `raw_source_events` and are owner-token-gated by the existing
  per-user routes. Connector tables hold owner-state metadata
  only.
- **No OAuth tokens.** Provider tokens stay in
  `source_connection_state` (or its successor); never duplicate
  into `connector_*`.
- **No env secret values.** Even paths to `.env` files are masked
  per `docs/CONNECTOR_SANITIZATION_RULES.md`.
- **No write paths until the consumer route lands.** The bridge
  writes locally to `data/agent-status/lanes/*.json` today; the
  Supabase upsert path requires the
  `LaneStatusWritePayload` route in chat-app or the Worker, which
  is a separate batch.
