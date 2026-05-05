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
