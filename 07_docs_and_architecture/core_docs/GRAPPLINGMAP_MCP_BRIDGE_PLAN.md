# GrapplingMap MCP-style bridge plan

How the Lauburu Railway backend becomes a structured source of
truth that ChatGPT, Claude, and Codex can read MCP-style. First
iteration is read-only project / app state; raw athlete health
data is gated separately and remains out of the connector
indefinitely without explicit consent gating.

Companion to `RAILWAY_CONNECTOR_TOOLS.md` (curl examples),
`CONNECTOR_BACKLOG_TOOLS_PLAN.md` (write tools spec),
`CONNECTOR_SECURITY_MODEL.md` (invariants), and
`IN_APP_AUDIT_SYSTEM.md` (audit roll-ups).

Updated 2026-05-06.

## Vision

ChatGPT / Claude / Codex talk to a small set of MCP-style tools
hosted on the Railway backend that already powers the mobile
app. The connector replaces the laptop ChatGPT + Apple Notes
loop by giving the AI runner direct read access to the
structured project state — current priority, release status,
backlog, feedback queue, audit summary, handoff blocks. Writes
are second-wave and gated.

## Live today

- `GET /api/athlete-memory/admin/status` — booleans/links/repo
  state. LIVE since commit `c29dee2`.
- `GET /api/athlete-memory/admin/work-status` — connector-shaped
  owner-state. LIVE since commit `31d9bb0`. Returns
  currentPriority / currentBlocker / nextAction +
  androidReleaseStatus + iosReleaseStatus + healthSourceStatus +
  adminDevStatus + feedbackSummary + backlogSummary + manualSteps
  + canDeleteFromNotes + doNotDeleteYet + reserved future-route
  names. Awaits the next Railway deploy of `chat-app` to surface
  on the live host.
- `GET /api/feedback/recent` — admin-gated tester feedback.
  LIVE.
- `GET /api/feedback/attachments/:filename` — admin-gated
  attachment image. LIVE.

## Read tools (planned, owner-token gated)

| Tool name | HTTP route | State |
|---|---|---|
| `get_work_status` | `GET /api/athlete-memory/admin/work-status` | LIVE |
| `get_release_status` | subset of work-status | LIVE |
| `get_health_source_status` | subset of work-status | LIVE (per-source roll-up; per-user via `:athleteId/source-health`) |
| `get_health_audit_summary` | `GET /api/athlete-memory/admin/health-audit-summary` | TODO (route reserved in audit doc) |
| `get_feedback_queue` | `GET /api/feedback/recent` | LIVE |
| `get_backlog_priority` | `GET /api/athlete-memory/admin/backlog` | TODO |
| `get_handoff` | `GET /api/athlete-memory/admin/handoff` | TODO |

All read tools require the `x-athlete-memory-token` header. None
return raw athlete health data, secrets, or PII beyond what's
already in the feedback records.

## Write tools (second wave, gated by owner-tap)

Per `CONNECTOR_BACKLOG_TOOLS_PLAN.md`. Summary:

- `create_backlog_item` — owner shared token only; new items
  default to `status: 'new'`, `needsReview: true`,
  `source: 'connector'`.
- `update_backlog_item` — owner shared token; cannot move items
  to `archived`.
- `mark_feedback_triaged` — owner shared token.
- `update_current_priority_draft` — writes a `priorityDraft`
  field, NEVER the live priority. Owner promotes via a one-tap
  Accept in Admin/Dev.
- `save_handoff` — owner shared token.
- `create_prompt_draft` — owner shared token.
- `mark_audit_event_triaged` — owner shared token.

Connector NEVER calls `/v1/internal/*`, build dispatch,
direct Supabase, raw normalized_daily_metrics writes, or any
route that would mutate per-user health data.

## Approval gates

For every write that changes user-facing state, an explicit
human-tap second factor in Admin/Dev is required. See
`CONNECTOR_BACKLOG_TOOLS_PLAN.md` § Write tools and
`BACKLOG_AUTOMATION_SYSTEM.md` Lane 3. In short:

- Active #1 priority changes → connector writes `priorityDraft`,
  owner taps Accept.
- Archiving completed items → owner-only.
- Dispatching builds → owner-tap in Admin/Dev. Connector cannot
  hit `/admin/workflows/:id/dispatch`.
- Changing health/readiness user-facing copy → owner-only.
- Stable athlete-memory promotion → owner-only.
- Paid API usage → owner-only (gated by `AI_PROVIDER_STRATEGY.md`).

## Wire-up

1. **Connector configuration** — for ChatGPT Connectors UI,
   Claude.ai MCP, or a Codex agent, the configuration entry is:
   - URL: `https://lauburu-ai-backend-production.up.railway.app`
   - Auth: header `x-athlete-memory-token: $ATHLETE_MEMORY_TOKEN`
     (where `$ATHLETE_MEMORY_TOKEN` is the same value as the mobile
     app's `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN`).
   - Tool list: per `RAILWAY_CONNECTOR_TOOLS.md` § ChatGPT
     connector / MCP read-only tool mapping.
2. **Polling cadence** — `get_work_status` is cheap enough to
   poll on every conversation turn; the others are explicit on
   request.
3. **No connector secret rotation** — the same shared token
   gates the in-app Admin/Dev surface. If the token leaks,
   rotate via Railway env update; the mobile app picks up the
   new value on the next build.

## Health data path (intentionally out of scope)

Aaron's and the girlfriend's per-day health metrics live in
Supabase `normalized_daily_metrics` rows behind the per-athlete
JWT cross-check. The connector is NOT given read access to those
rows. Reasons:

1. Cross-user privacy. The connector authenticates as "owner"
   via the shared admin token; that's not the right credential
   to read another user's health data.
2. Consent gating. Sharing health data with a third-party AI
   service requires explicit per-user opt-in, per-feature
   consent — which doesn't exist yet (and won't until the paid
   AI lane, monetisation, and consent flows from
   `AI_PROVIDER_STRATEGY.md` all land).
3. Cohort aggregation. Once we want cohort-level health data
   visibility, the right shape is a privacy-preserving roll-up
   (k-anonymity threshold per cell, no per-user identifiers) —
   not a raw read.

## Stages of MCP build-out

| Stage | What lands | Trigger |
|---|---|---|
| **Stage 1 — read project state** | LIVE today (work-status + status + feedback reads) | Already done |
| **Stage 2 — read backlog/handoff/audit roll-ups** | TODO routes from this doc | Next safe lane |
| **Stage 3 — owner write tools (drafts)** | create/update_backlog, save_handoff, prompt_draft, priority_draft | After stage 2 is live for ≥1 week |
| **Stage 4 — connector-driven build dispatch** | NEVER. Build dispatch is a human tap, no exceptions. |
| **Stage 5 — per-user health reads** | Only if/when consent + monetisation gates are in place. |

## Out of scope for this doc

- The exact MCP JSON schema for each tool — generated when the
  connector configuration is set up; until then,
  `RAILWAY_CONNECTOR_TOOLS.md` carries the curl-level shape.
- Streaming responses — request/response only.
- Server-Sent Events for live status — polling is enough.
- A separate connector token (e.g. per-AI vendor). One shared
  owner token until / unless that pattern proves insufficient.
