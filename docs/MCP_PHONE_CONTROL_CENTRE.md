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
EXPO_PUBLIC_MCP_BASE_URL=https://lauburu-mcp-preview.lauburu-aaron.workers.dev
```

The mobile `connectorApiBase()` helper auto-appends `/api` if
the env value doesn't already end with it, so either form works
(`…workers.dev` or `…workers.dev/api`).

The same admin token used today
(`EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`) is sent in the
`x-athlete-memory-token` header. No new secret needed; the same
value is also the Worker's `ATHLETE_MEMORY_API_TOKEN` secret.

## Quick reference for ChatGPT / HTTP consumers

The screenshot-free read path is **live**. Any HTTP client that
sends the admin token in a custom header can read live Claude /
Codex lane status, the latest handoff, the terminal summary log,
and the build / work_status snapshots — no Termius screenshots.

**Base URL:** `https://lauburu-mcp-preview.lauburu-aaron.workers.dev`

**Auth header:** `x-athlete-memory-token: <ATHLETE_MEMORY_API_TOKEN>`
(same value as the mobile app's `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`,
also stored in Mac Keychain under the same name).

**Live endpoints** (all `GET`, all admin-token-gated, all return
JSON):

| Path | Returns | Source |
|---|---|---|
| `/health` | public liveness + Worker meta | (no auth required) |
| `/status` | public meta + endpoints listing | (no auth required) |
| `/supabase/health` | adapter configured? PostgREST ping ok? | admin |
| `/api/work_status` | `WorkStatus` (current priority, blocker, next action, repo state) | admin |
| `/api/coder_lanes` | `CoderLanes` (one row per active lane: claude / codex etc) | admin |
| `/api/build_status` | `BuildStatus` (Android + iOS release rows) | admin |
| `/api/handoff` | `Handoff` (latest prompts, manual steps, doNotTouch, safeToBuild) | admin |
| `/api/terminal_summary` | `TerminalSummary` (mark-agent-done log, ≤50 entries) | admin |

Every admin response carries a `dataSource` field:

- `{ source: 'supabase', table: 'connector_…' }` — live row
  from Supabase.
- `{ source: 'placeholder', reason, message, schemaRequired }` —
  fallback. `reason` is one of:
  - `env_missing` / `env_url_invalid` / `env_key_invalid` —
    Worker secrets not (validly) set.
  - `table_empty` — adapter is configured but the table has no
    row matching the route's key. Routes still return
    schema-shaped placeholders so consumers don't have to
    branch.

A `403 Forbidden admin access.` response means the
`x-athlete-memory-token` header is missing or wrong. A `404 Route
not found.` means the path isn't on the allowlist (every other
path on the host returns 404).

Schemas live in
`chat-app/src/server/types/connector.ts` — TS interfaces are the
canonical shape. The
`chat-app/src/server/scripts/test-mcp-worker-live.ts` script (run
via `npm run mcp:test:live` with `MCP_WORKER_URL` and
`ATHLETE_MEMORY_TOKEN` in env) asserts every route's auth gate
and the terminal_summary schema against the live Worker.

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
| Worker → Supabase reads (5 fetch helpers, fallback path) | LIVE — returns real Supabase data, placeholder + `table_empty` when row missing |
| `connector_*` Supabase tables | LIVE — migration applied; all five tables seeded |
| `SUPABASE_URL` Worker secret | LIVE |
| `SUPABASE_SERVICE_ROLE_KEY` Worker secret | LIVE (`sb_secret_…` format accepted alongside legacy `eyJ…` JWTs) |
| `/api/work_status` | LIVE — `dataSource.source = supabase` |
| `/api/coder_lanes` | LIVE — `dataSource.source = supabase`, returns claude + codex bridge rows |
| `/api/build_status` | LIVE — `dataSource.source = supabase` (seeded from latest paired build) |
| `/api/handoff` | LIVE — `dataSource.source = supabase` |
| `/api/terminal_summary` | LIVE — `dataSource.source = supabase` |
| Mobile `EXPO_PUBLIC_MCP_BASE_URL` switch | LIVE in code (`apps/mobile/src/services/ai-backend-config.ts`); env-var unset in current released build |

## Manual Supabase steps (DONE)

All three steps are complete. Tables applied, all three Worker
secrets installed, all five connector tables seeded, all five
`/api/*` routes serving live Supabase data.

The remaining work is operational, not gating:

- **Mobile env flip.** Set `EXPO_PUBLIC_MCP_BASE_URL=https://lauburu-mcp-preview.lauburu-aaron.workers.dev`
  in EAS env (or `.env.development` for dev builds) so the
  next paired mobile build's Admin/Dev cards read from the
  Worker instead of legacy Railway. The mobile client
  auto-appends `/api`, so trailing-slash and `/api` are both
  acceptable.
- **Bridge cron.** Today the bridge runs on `npm run
  bridge:snapshot` from the laptop. A future batch can
  schedule it (cron / launchd / a small daemon) so coder_lanes
  and terminal_summary refresh without manual invocation.
- **Build_status writer.** `connector_build_status` was seeded
  with the latest paired build's IDs as a one-time backfill.
  A future batch should attach an upsert to the release
  workflow so each build refreshes the row.

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
