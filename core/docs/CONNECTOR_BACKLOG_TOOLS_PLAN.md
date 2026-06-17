# Connector backlog tools — read/write spec

How a future ChatGPT / Claude / Codex connector talks to the
Lauburu Railway backend safely. Companion to
`IN_APP_DEV_BACKLOG_PLAN.md` (the in-app shape) and
`LOCAL_BRIDGE_WORKFLOW_PLAN.md` (the broader staged path).

This document is a contract, not implementation. The actual
routes are scaffolded incrementally; tonight's batch lands the
first read-only one (`get_work_status` mapped to
`/api/athlete-memory/admin/status`) and reserves names for the
rest.

Updated 2026-05-06.

## Principles

1. **Owner/admin only.** Every connector route requires the
   shared `ATHLETE_MEMORY_API_TOKEN` header (already enforced for
   admin routes via `requireAdminToken`). The connector mints a
   short-lived JWT scoped to "owner" + a single Aaron-specific
   user id; no other user identity is recognised.
2. **Read-only first.** The first wave of tools is GET-only. The
   write tools land after the read tools have been live and
   audited.
3. **No secrets returned.** Every response is filtered through
   the existing pattern (admin status returns booleans + repo
   links only). Tokens, env values, OAuth client secrets, service
   account keys — never serialised to the wire.
4. **No raw athlete health data exposed via connector.** The
   connector never returns raw HealthKit / Health Connect
   samples, raw WHOOP cycle records, or raw food logs. It can
   surface aggregated state (e.g. "WHOOP recovery score
   available: yes/no") but not the values.
5. **Writes create an audit log.** Every write is appended to a
   server-side log (Railway logs are fine for the first
   iteration; durable Supabase audit table is a follow-up).
6. **Dangerous writes need a human-tap second factor.** Priority
   changes, archiving, build dispatches, paid AI invocation, and
   stable-memory writes all require an explicit owner tap in
   Admin/Dev — the connector can ONLY write a "draft" that the
   owner promotes.

## Read tools (first wave, owner-token gated)

| Tool name | HTTP route | Purpose | Lives today? |
|---|---|---|---|
| `get_work_status` | `GET /api/athlete-memory/admin/status` | currentPriority + currentBlocker + nextAction + Android/iOS release status + Railway flags | EXTENDED in this batch (see `/admin/work-status` below) |
| `get_release_status` | `GET /api/athlete-memory/admin/status` | Subset: tester-live versionCode + buildNumber + auto-promote state | LIVE (commit `c29dee2`) |
| `get_health_source_status` | `GET /api/athlete-memory/:athleteId/source-health` (per-user) | Per-source freshness + missingDomains + last sync | LIVE (gated by JWT ownership) |
| `get_handoff` | `GET /api/athlete-memory/admin/handoff` | Most-recent saved CHATGPT_STATUS block | TODO |
| `get_backlog` | `GET /api/athlete-memory/admin/backlog` | Owner-backlog items + tester feedback view (per `IN_APP_DEV_BACKLOG_PLAN.md` Option A) | TODO |
| `get_feedback_queue` | `GET /api/feedback/recent` | Tester feedback rows | LIVE (admin-gated, commit `4e567b7`) |
| `get_automation_state` | `GET /api/athlete-memory/admin/status` | Subset: workflow dispatch availability + allowlist | LIVE |

## Write tools (second wave, gated by owner-tap)

| Tool name | HTTP route | Effect | Required gate |
|---|---|---|---|
| `create_backlog_item` | `POST /api/athlete-memory/admin/backlog` | Insert item with `status: 'new'`, `needsReview: true`, `source: 'connector'` | Owner shared token; no human-tap needed (item lives in queue until reviewed) |
| `update_backlog_item` | `PATCH /api/athlete-memory/admin/backlog/:id` | Update fields except `status === 'archived'` and except `priority < 4` | Owner shared token; warn if priority bumped above rank 4 |
| `mark_feedback_triaged` | `POST /api/feedback/:id/triage` | Set `triaged: true` + reason | Owner shared token |
| `update_current_priority_draft` | `POST /api/athlete-memory/admin/priority-draft` | Stages a new currentPriority value awaiting owner accept | Owner shared token; the in-app Now chip shows "[draft] {value} — Accept / Reject" until tapped |
| `save_handoff` | `POST /api/athlete-memory/admin/handoff` | Save a new CHATGPT_STATUS block | Owner shared token |
| `create_prompt_draft` | `POST /api/athlete-memory/admin/prompt-drafts` | Adds a draft to the in-app Prompt bridge library | Owner shared token |

Connector NEVER calls (period):

- Anything under `/v1/internal/*` (server-to-server only).
- `POST /admin/workflows/:id/dispatch` (build dispatch must be a
  human tap).
- Direct Supabase REST.
- Direct PATCH / DELETE on tester feedback records.
- Anything that writes into `normalized_daily_metrics` or
  `raw_source_events`.

## Today's scaffolding

This batch only lands the doc + reserves the route name
`/api/athlete-memory/admin/work-status` as a future synonym /
extension of `/admin/status`. No new code beyond the docs.

When the connector is wired:

1. The connector authenticates with the shared
   `ATHLETE_MEMORY_API_TOKEN`.
2. The mobile app's Admin/Dev "Now" chips poll the same
   `get_work_status` route the connector reads.
3. Drafts the connector writes appear in Admin/Dev under "Prompt
   drafts" + "Priority drafts" — the owner accepts them with a
   single tap.
4. The audit log surfaces in Admin/Dev → Diagnostics.

## Out of scope for this doc

- Per-tool argument schemas (will land in MCP-style JSON schema
  when the connector is implemented).
- Token rotation strategy (deferred; `ATHLETE_MEMORY_API_TOKEN` is
  rotated through Railway env updates today).
- Cross-user / aggregate trend reads (gated on consent +
  k-anonymity threshold; see `AI_PROVIDER_STRATEGY.md`).
- Streaming responses (deferred; first iteration is request /
  response only).
