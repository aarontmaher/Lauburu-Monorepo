# Railway connector tools — read examples

How ChatGPT, Claude Code, and Codex talk to the Lauburu Railway
backend safely. This is the **practical curl guide**; the broader
contract sits in `CONNECTOR_BACKLOG_TOOLS_PLAN.md` and the
security rules sit in `CONNECTOR_SECURITY_MODEL.md`.

Updated 2026-05-06.

## Host

```
https://lauburu-ai-backend-production.up.railway.app
```

All admin connector routes live under `/api/athlete-memory/admin/`.

## Auth

Every admin connector call sends the shared admin token in the
`x-athlete-memory-token` header. The same token gates the Admin/Dev
in-app surface — there is no separate connector token. Production
must NEVER set `ALLOW_SHARED_TOKEN_ONLY=1` (explicit comment in
the code), but the connector path doesn't need a per-user JWT
because the routes return owner-state, not athlete data.

```sh
export RAILWAY_API_BASE="https://lauburu-ai-backend-production.up.railway.app"
export ATHLETE_MEMORY_TOKEN="…"   # from Railway env, never committed
```

## Read-only tools (live + planned)

### `get_work_status` — LIVE (this batch)

Single source of truth for owner-state. Connector reads this on
every poll to know currentPriority / currentBlocker / nextAction
/ androidReleaseStatus / iosReleaseStatus / healthSourceStatus /
adminDevStatus / feedbackSummary / backlogSummary / manualSteps /
canDeleteFromNotes / doNotDeleteYet.

```sh
curl -sS \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status" \
  | jq '.currentPriority, .currentBlocker, .nextAction'
```

Response fields are stable: new fields can be added at the end,
but existing fields never change meaning. See the route
implementation in
`chat-app/src/server/routes/athleteMemory.ts`.

### `get_release_status` — LIVE (subset of work-status / admin/status)

```sh
curl -sS \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status" \
  | jq '.androidReleaseStatus, .iosReleaseStatus'
```

### `get_health_source_status` — LIVE (subset)

```sh
curl -sS \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status" \
  | jq '.healthSourceStatus'
```

### `get_feedback_queue` — LIVE (admin-gated, commit `4e567b7`)

```sh
curl -sS \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/feedback/recent" \
  | jq '.records | length, .hidden_count'
```

### `get_handoff` — TODO

Future route: `GET /api/athlete-memory/admin/handoff`. Returns
the most-recent saved CHATGPT_STATUS block. Reserved field name
in `work-status.reserved.handoffReadRoute`.

### `get_backlog` — TODO

Future route: `GET /api/athlete-memory/admin/backlog`. Returns
the merged owner backlog + tester-feedback view per
`IN_APP_DEV_BACKLOG_PLAN.md` Option A. Reserved field name in
`work-status.reserved.backlogReadRoute`.

## Claude Code curl check

Quick liveness check from Claude Code's terminal:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status"
```

Expected: `200`. Anything else = the route hasn't deployed yet
or the token is wrong. Without the header: `403 Forbidden admin
access.`

## Codex curl check

Codex agents run in their own sandbox. Same call shape:

```sh
curl -sS \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status" \
  > work_status.json

jq '.currentPriority' work_status.json
```

The Codex agent should refuse to write to any unreserved field
or to any route not listed in this document.

## ChatGPT connector / MCP read-only tool mapping

When ChatGPT (or Claude.ai's Connectors UI) wires this up
MCP-style, the tool surface is:

```jsonc
{
  "tools": [
    {
      "name": "get_work_status",
      "description": "Owner-state summary of Lauburu app work.",
      "inputSchema": { "type": "object", "properties": {} },
      "endpoint": "GET /api/athlete-memory/admin/work-status",
      "auth": "x-athlete-memory-token header"
    },
    {
      "name": "get_release_status",
      "description": "Subset of get_work_status focused on Android v / iOS Build state.",
      "endpoint": "GET /api/athlete-memory/admin/work-status",
      "select": ".androidReleaseStatus, .iosReleaseStatus"
    },
    {
      "name": "get_health_source_status",
      "description": "Per-source connection state for Apple Health, Health Connect, WHOOP, Polar etc.",
      "endpoint": "GET /api/athlete-memory/admin/work-status",
      "select": ".healthSourceStatus"
    },
    {
      "name": "get_feedback_queue",
      "description": "Recent tester feedback rows (admin-gated).",
      "endpoint": "GET /api/feedback/recent",
      "auth": "x-athlete-memory-token header"
    }
  ]
}
```

Until ChatGPT's Connectors UI / Claude.ai MCP wire-up is set up,
the same calls run from the laptop terminal as curl checks above.

## What the connector NEVER calls

- `/v1/internal/*` — server-to-server only, requires
  `INTERNAL_API_TOKEN` which the connector does not hold.
- `POST /api/athlete-memory/admin/workflows/:id/dispatch` — build
  dispatch is a human tap. ChatGPT cannot hit this route from
  this connector configuration.
- Direct Supabase REST.
- Any `:athleteId/*` route — those are per-user JWT-gated and
  serve athlete data, which the connector intentionally cannot
  read.

## Verification

```sh
# 1. Liveness + auth
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status"
# Expected: 200

# 2. Refused without header
curl -sS -o /dev/null -w '%{http_code}\n' \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status"
# Expected: 403

# 3. Refused for non-admin tokens
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "x-athlete-memory-token: not-the-real-token" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status"
# Expected: 403

# 4. Required field present
curl -sS \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/athlete-memory/admin/work-status" \
  | jq -e '.currentPriority and .currentBlocker and .nextAction'
# Expected: true (jq exits 0)
```

Run after the next Railway deploy to confirm the route is live.

## MCP connector routes (`/api/*` — added in commit `b6fe1ad`)

Mounted under `/api/` (snake_case, distinct from the kebab-case
`/api/athlete-memory/admin/*` family). Same admin token,
different URL form. All four are GET-only today; the bridge
writers (`POST /lane-status`, `POST /terminal-summary`) land
when the tmux producer ships.

```sh
export RAILWAY_API_BASE="https://lauburu-ai-backend-production.up.railway.app"
# ATHLETE_MEMORY_TOKEN: never paste in chat — load from your local
# password manager / Mac Keychain.

# 1. Work status
curl -sS \
  -H "Accept: application/json" \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/work_status" | jq

# Expected (admin token elided, dummy data while bridge is offline):
# {
#   "schemaVersion": 1,
#   "generatedAt": "2026-05-06T...Z",
#   "currentPriority": "Backend/API connector dummy routes ...",
#   "currentBlocker": "tmux bridge is not operational yet; ...",
#   "liveStatus": {
#     "androidVersionCode": 17,
#     "iosBuildNumber": "18",
#     "androidPlayTrack": "internal",
#     "iosTestflightGroup": "Team (Expo)",
#     "lastRailwayDeployAt": null,
#     "cloudflareWorkerDeployed": false
#   },
#   "repoStatus": { "head": "unknown", ... },
#   "nextAction": "Connect tmux bridge producer, ..."
# }

# 2. Coder lanes
curl -sS \
  -H "Accept: application/json" \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/coder_lanes" | jq '.lanes[] | {laneId, status, nextPrompt}'

# Expected (placeholder while bridge is offline):
# { "laneId": "claude", "status": "idle",    "nextPrompt": "CLAUDE-REVIEW-MCP-DUMMY-ROUTES-01" }
# { "laneId": "codex",  "status": "working", "nextPrompt": null }

# 3. Build status
curl -sS \
  -H "Accept: application/json" \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/build_status" | jq

# 4. Handoff
curl -sS \
  -H "Accept: application/json" \
  -H "x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN" \
  "$RAILWAY_API_BASE/api/handoff" | jq

# 5. Refused without admin token
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H "Accept: application/json" \
  "$RAILWAY_API_BASE/api/work_status"
# Expected: 403

# 6. Disabled when ATHLETE_MEMORY_API_TOKEN env unset on the server
# Expected: 503 with `{ ok: false, error: 'Connector routes disabled until ATHLETE_MEMORY_API_TOKEN is configured.' }`
```

### Local schema test (no Railway needed)

The repo ships a self-contained schema test that boots the
Express app on an ephemeral port and asserts the response
shapes match `chat-app/src/server/types/connector.ts`:

```sh
cd chat-app
npx tsx src/server/scripts/test-mcp-routes.ts
# Expected stdout: "MCP route schema tests passed."
```

### Status (2026-05-06)

- **Local schema tests:** PASS (run via `npx tsx`).
- **Live on Railway:** **BLOCKED** — Railway service has been in
  `FAILED` state since 2026-04-28. The Cloudflare Worker is the
  live MCP surface during the suspension; see
  `docs/CLOUDFLARE_MIGRATION.md` § 11.6 for the URL and curls.
- **Live on Cloudflare:** **YES** —
  `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/api/*`
  serves the four routes admin-token gated. Same payload shapes
  as documented above.
- **Sanitization:** routes return static strings only; no
  user-content yet, so the redactor is not exercised. Once the
  tmux bridge populates real lane summaries, the route layer
  must apply `redactTokenLikeSubstrings()` at the response
  boundary per `docs/CONNECTOR_SANITIZATION_RULES.md`.
- **Bridge state:** read-only stub (`getLaneSummaries()`
  returns hardcoded rows). The Stage-1 producer
  (`scripts/bridge-snapshot-lanes.sh`) is still planned per
  `LOCAL_BRIDGE_COMMAND_ALLOWLIST.md`.
- **Safe to deploy:** YES for the routes themselves (admin-token
  gated, no writes, no secrets in the payload). The dummy data
  is a docs-grade placeholder, not a security risk.
