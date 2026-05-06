# MCP control centre — phone-first runbook

How Aaron (or ChatGPT) checks Claude / Codex lane status from the
phone — no Termius screenshots required.

This runbook is the bridge between three pieces:

1. **Local tmux bridge** —
   `scripts/bridge-snapshot-lanes.sh` reads the `lauburu` and
   `codex-lauburu` tmux sessions, classifies each lane, sanitises
   the output, and writes JSON artifacts to
   `data/agent-status/lanes/`.
2. **Cloudflare Worker** —
   `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/`
   exposes 5 admin-token-gated MCP read routes. Reads from
   Supabase when configured; falls back to a placeholder payload
   with explicit `dataSource.schemaRequired` otherwise.
3. **Mobile app Admin/Dev** —
   `apps/mobile/src/services/connector-status-client.ts` calls
   the Worker via `EXPO_PUBLIC_MCP_BASE_URL` and renders the
   four lane summaries.

Updated 2026-05-07.

## Refresh bridge status (laptop)

```sh
npm run bridge:snapshot
```

Wraps `./scripts/bridge-snapshot-lanes.sh`. Writes:

- `data/agent-status/lanes/coder_lanes.json` (CoderLanes aggregate)
- `data/agent-status/lanes/<laneId>.json` (per-lane CoderLaneRow)
- `data/agent-status/lanes/terminal_summary.json` (TerminalSummary)
- `data/agent-status/lanes/handoff.json` (Handoff)

If `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present in
the bridge's environment, the script ALSO upserts the same
payloads to the four `connector_*` tables in Supabase using
hardcoded paths only. When the env vars are unset (default), the
bridge logs `supabase: skip (env_missing)` and stays
local-artifact-only. To enable the upsert path:

```sh
export SUPABASE_URL="https://rejalrfmievikabgsakf.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="…paste from Supabase dashboard…"
npm run bridge:snapshot
# supabase: upserting to https://…
#   connector_work_status: HTTP 201
#   connector_coder_lanes: HTTP 201
#   connector_handoff: HTTP 201
#   connector_terminal_summary: HTTP 201 (entries=N)
```

Don't paste the service-role key into shell history files;
prefer a sourced env file or a keychain helper. The bridge runs
from Aaron's Mac only — never from CI, never from the phone.

Validate the local artifacts against the canonical TS types:

```sh
npm run bridge:verify
```

Both scripts are pure-read on the local repo apart from the
optional Supabase upsert: `tmux capture-pane`, `git status`,
`git rev-parse`, plus PostgREST POSTs to the four hardcoded
`connector_*` paths. No `eval`. No build dispatch. No
caller-supplied table name reaches Supabase.

## How the phone consumes MCP routes

The mobile app's
`apps/mobile/src/services/connector-status-client.ts` reads from
either:

- The Cloudflare Worker, when `EXPO_PUBLIC_MCP_BASE_URL` is set
  in the EAS env (or `.env.development` for dev builds).
- The legacy Railway public backend otherwise (deprecated; the
  Railway service is in `FAILED` state since 2026-04-28).

To point the next mobile build at the Worker (no version bump
required — env-only):

```
EXPO_PUBLIC_MCP_BASE_URL=https://lauburu-mcp-preview.lauburu-aaron.workers.dev/api
```

The trailing `/api` is required — the mobile client's path
constructor produces e.g. `${baseUrl}/work_status`, and the
Worker's allowlist serves under the `/api/*` prefix.

The same admin token used today (`EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`)
is sent in the `x-athlete-memory-token` header. No new secret
needed.

## Direct curl from phone / ChatGPT

For headless usage (ChatGPT or any HTTP client that supports
custom headers):

```sh
export MCP="https://lauburu-mcp-preview.lauburu-aaron.workers.dev"
export TOKEN="<paste from Mac Keychain — same as EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN>"

curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/api/work_status"     | jq
curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/api/coder_lanes"     | jq
curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/api/build_status"    | jq
curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/api/handoff"         | jq
curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/api/terminal_summary"| jq
```

Each response carries a `dataSource` field:

- `{ source: 'supabase', table: 'connector_*' }` — live data
  loaded from Supabase. This is the goal state.
- `{ source: 'placeholder', reason: 'env_missing', ..., schemaRequired: { table, envelope, migration } }` —
  fallback. Tells the caller exactly what's missing on the
  Worker side. The four placeholder routes still return
  schema-shaped payloads so consumers can render UI without
  branching.

A `403 Forbidden admin access.` response means the
`x-athlete-memory-token` header is missing or wrong.

## Live vs repo-only

| Component | Status |
|---|---|
| Cloudflare Worker (`lauburu-mcp-preview`) | LIVE — `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/` |
| Worker admin-token gating | LIVE |
| Worker routes `/api/*` (5 connector routes) | LIVE — placeholder fallback when Supabase unset |
| `ATHLETE_MEMORY_API_TOKEN` Worker secret | LIVE |
| Local tmux bridge (`scripts/bridge-snapshot-lanes.sh`) | LIVE — local artifacts always; Supabase upsert when env vars present |
| Bridge → Supabase upsert | LIVE (env-gated) — hardcoded `connector_*` paths only, gated on `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` in env |
| Worker → Supabase reads (5 fetch helpers, fallback path) | LIVE — code returns Supabase data when secrets set; placeholder otherwise |
| `connector_*` Supabase tables | LIVE — applied via `supabase/migrations/0003_connector_status_tables.sql`; seeded with bridge artifacts |
| `SUPABASE_URL` Worker secret | NOT YET — Aaron pastes via `wrangler secret put` |
| `SUPABASE_SERVICE_ROLE_KEY` Worker secret | NOT YET — Aaron pastes via `wrangler secret put` |
| Mobile `EXPO_PUBLIC_MCP_BASE_URL` switch | LIVE in code (`apps/mobile/src/services/ai-backend-config.ts`); env-var unset in current released build |

## Manual Supabase steps (final remaining)

Step 1 (apply the migration) is **DONE** — the five
`connector_*` tables exist in project `rejalrfmievikabgsakf`,
seeded with the current bridge snapshot. Only the two Worker
secrets remain:

1. ~~**Apply the migration.**~~ DONE.
2. **Set the Worker secrets.** This is the single remaining
   blocker for screenshot-free MCP reads.
   ```sh
   cd cloudflare-worker
   npx wrangler secret put SUPABASE_URL --name lauburu-mcp-preview
   # paste: https://rejalrfmievikabgsakf.supabase.co
   npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY --name lauburu-mcp-preview
   # paste: service_role JWT from Supabase → Project Settings → API
   npx wrangler deploy --env preview
   ```
3. **Verify.**
   ```sh
   curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/supabase/health" | jq
   # Expected: supabase.configured = true, supabase.ping.ok = true
   curl -sS -H "x-athlete-memory-token: $TOKEN" "$MCP/api/coder_lanes" | jq '.dataSource.source'
   # Expected: "supabase" (was "placeholder" before secrets)
   ```

Until step 2 lands, the routes return
`dataSource: { source: 'placeholder', schemaRequired: ... }`
even though Supabase is fully populated — the Worker has no way
to authenticate to Supabase without the service-role key. That
is the only thing standing between today's state and full
screenshot-free MCP reads.

## Safety model (cross-reference)

The Supabase service-role key bypasses RLS. Real safety comes
from:

- **Worker-only secret** — `SUPABASE_SERVICE_ROLE_KEY` lives only
  on the Worker. Never bundled into the mobile app.
- **Strict route allowlist** — exactly five connector routes;
  every other path returns 404.
- **No arbitrary Supabase queries** — the adapter only exposes
  hardcoded `fetch<TableName>` helpers targeting the four named
  `connector_*` tables.
- **Connector-table-only code paths** — no read path from the
  Worker to athlete data tables.
- **Admin-token gate on every route** —
  `x-athlete-memory-token` required.

See `docs/CONNECTOR_SUPABASE_SCHEMA.md` § Safety model for the
full discussion.

## Next safe phase: predefined action queue

Stage 5 of `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md` covers the
Tailscale bridge daemon + a fixed allowlist of "tap from phone,
execute on laptop" actions. The current Stage 1 read producer is
the prerequisite. The action queue stays planned-only until:

1. Supabase tables + Worker secrets are live (above).
2. The bridge daemon has Tailscale reachability + biometric auth
   on the phone.
3. Each action is an entry in
   `docs/LOCAL_BRIDGE_COMMAND_ALLOWLIST.md` with explicit
   inputs / effects / rejection criteria.

Until those three hold, the phone reads MCP state but cannot
write actions through the bridge. The owner-tap surfaces in the
mobile app (Admin/Dev → Primary actions → Workflow dispatch /
Mark agent done) remain the only write path.
