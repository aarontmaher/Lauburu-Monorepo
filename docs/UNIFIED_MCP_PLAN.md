# Unified Lauburu / GrapplingMap MCP — design plan

A single canonical MCP endpoint that consolidates mobile-dev
state, website / control-centre state, integrations state, and
handoffs behind a namespaced tool surface — without breaking any
existing connector during the rollout.

This doc is **design only**. No code lands in the same commit as
this plan. The migration checklist (§ 6) drives later batches.

Companion to:
- `docs/MCP_PHONE_CONTROL_CENTRE.md` — current `/api/*` runbook.
- `docs/CHATGPT_CONNECTOR_SETUP.md` — current connector setup.
- `docs/MCP_CANONICAL_STATE.md` — the two-MCPs-coexist clarity
  doc this plan supersedes IF AND ONLY IF the migration
  reaches Phase 4.
- `docs/CONTROL_CENTRE_MVP_SPEC.md` — the snapshot the
  `mobile.*` namespace already serves.

Updated 2026-05-07.

## 1. Goal

One MCP server URL where ChatGPT, Claude Code, Codex, and any
future client can read every project-state question through a
single tool surface, with namespaces that make the scope of each
answer obvious. No data store gets coupled. No existing endpoint
gets deleted in the same release the new one ships.

## 2. Backwards-compatibility contract (HARD GUARANTEES)

Every endpoint below KEEPS WORKING through the migration. Nothing
in this plan deletes or breaks them.

| Endpoint | Status during migration | When (if ever) deprecated |
|---|---|---|
| `lauburu-mcp-preview…/mcp/public` (4 tools, No Auth) | KEEP | Earliest at Phase 4, only after the v2 endpoint has run for ≥30 days with no regressions |
| `lauburu-mcp-preview…/mcp` (5 tools, admin-token) | KEEP | Earliest at Phase 4 |
| `lauburu-mcp-preview…/api/*` (REST, admin-token) | KEEP indefinitely — these back the mobile app's `connector-status-client.ts`, not just MCP | Never (different consumer) |
| `mcp.lauburugrapplingmap.com/mcp` (~25 tools, No Auth) | KEEP — different repo entirely | Out of scope; that codebase decides |
| WHOOP MCP (if present at a separate URL — currently shows as disconnected in Claude Code's deferred tool list) | KEEP if present | Out of scope; that codebase decides |

**Anti-rule:** the v2 endpoint is **additive**. A commit that
removes any of the above before Phase 4 is rejected.

## 3. Canonical endpoint shape

Add a new path on this codebase's existing Worker:

```
POST https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2
Content negotiation: text/event-stream OR application/json
                    (matches existing /mcp/public negotiator)
Auth: layered — public-safe namespaces No Auth; private
      namespaces require admin token via Authorization: Bearer
      OR x-athlete-memory-token.
```

The same Cloudflare Worker hosts it; same secrets; same
admin-token gate. No new Cloudflare resource. The internal
implementation lives in a new `cloudflare-worker/src/mcp-v2.ts`
that:

- For `mobile.*` and `project.*` and `integrations.*`: queries
  Supabase `connector_*` tables and `source_connection_state`
  via the existing `getSupabaseAdapter`.
- For `website.*`: forwards JSON-RPC requests to
  `mcp.lauburugrapplingmap.com/mcp` and re-wraps the response.
  No website-project credentials live in this Worker — the
  website MCP is No Auth, so the proxy just relays the body
  with a session id.
- For `handoff.*`: composes from both stores; tags each entry
  with `source: 'mobile' | 'website'`.

## 4. Tool namespaces (the surface mobile / ChatGPT / Codex see)

### `project.*` — cross-project / roadmap

Public-safe by default. Aggregates only.

| Tool | Returns | Backed by |
|---|---|---|
| `project.get_overview` | `{ generatedAt, currentTopPriority: { source, title }, openManualStepsCount, openBacklogCount }` | `connector_*` (this repo) + `mcp.lauburugrapplingmap.com/mcp` `list_pending_suggestions` (website) |
| `project.list_priorities` | `[{ source, rank, title, status }]` from `docs/APP_DEVELOPMENTS.md`-style top-N (no free text > 120 char) | composed in Worker (no DB) |
| `project.get_canonical_state_doc` | URL + last-modified of `docs/MCP_CANONICAL_STATE.md` | static |

Live vs repo-only flag: `state: 'live' \| 'repo-only'` per item.
"Live" means deployed; "repo-only" means committed but not
shipped to testers / production.

### `mobile.*` — this repo's mobile-app dev state

Public-safe sanitised aggregates AT MOST. Detail lives behind
admin-token via the existing `/api/*` REST.

| Tool | Returns | Backed by | Auth |
|---|---|---|---|
| `mobile.get_lane_overview` | `{ totalLanes, byStatus, lastSnapshotAt }` | `connector_coder_lanes` | No Auth |
| `mobile.get_build_overview` | `{ android: {versionCode, status enum}, ios: {buildNumber, status enum} }` | `connector_build_status` | No Auth |
| `mobile.get_repo_overview` | `{ branch, shortHead }` | `connector_work_status.payload.repoStatus` | No Auth |
| `mobile.get_control_centre` | full `ControlCentreSnapshot` per `docs/CONTROL_CENTRE_MVP_SPEC.md` | `/api/control_centre` | admin token |
| `mobile.get_coder_lanes` | full `CoderLanes` (lane summaries with text) | `/api/coder_lanes` | admin token |
| `mobile.get_terminal_summary` | full `TerminalSummary` (≤50 entries) | `/api/terminal_summary` | admin token |
| `mobile.get_handoff` | full `Handoff` (manual steps with text) | `/api/handoff` | admin token |
| `mobile.get_work_status` | full `WorkStatus` payload | `/api/work_status` | admin token |
| `mobile.get_build_status` | full `BuildStatus` payload | `/api/build_status` | admin token |

### `website.*` — website project (proxied)

Forwarded JSON-RPC calls to `mcp.lauburugrapplingmap.com/mcp`.
The Worker re-wraps responses, no website credentials needed
(that MCP is No Auth).

| Tool | Maps to | Notes |
|---|---|---|
| `website.list_pending_suggestions` | `list_pending_suggestions` | identical args + return |
| `website.get_suggestion` | `get_suggestion` | identical |
| `website.submit_suggestion` | `submit_suggestion` | write — the website's queue, not this codebase's |
| `website.approve_suggestion_for_preview` | `approve_suggestion_for_preview` | write |
| `website.list_automation_batches` | `list_automation_batches` | identical |
| `website.get_automation_state` | `get_automation_state` | identical |
| `website.get_preview_status` | `get_preview_status` | identical |
| `website.start_preview_run` | `start_preview_run` | write |
| `website.advance_phase` | `advance_phase` | write |
| `website.approve_batch` | `approve_batch` | write |
| `website.get_handoff` | `get_handoff` | website project's handoff (not this codebase's) |
| `website.create_handoff_artifact` | `create_handoff_artifact` | write — for the website project |
| `website.get_work_status` | `get_work_status` | website's coder agents (NOT this codebase's lanes) |
| `website.update_work_status` | `update_work_status` | write to website store |
| `website.create_prompt_job`, `website.list_prompt_jobs`, `website.get_prompt_job`, `website.claim_prompt_job`, `website.complete_prompt_job`, `website.fail_prompt_job`, `website.cancel_prompt_job` | same names | website prompt-job queue |
| `website.get_user_health_summary` | `get_user_health_summary` | website's per-user health summary |
| `website.get_user_shared_memory` | `get_user_shared_memory` | website's per-user memory |
| `website.list_provider_registry` | `list_provider_registry` | website's provider catalogue |
| `website.get_daily_performance_object` | `get_daily_performance_object` | website's WHOOP performance store |

The proxy preserves `Mcp-Session-Id` between requests so
session-aware website tools (e.g. `tools/list` after
initialize) work transparently.

### `integrations.*` — third-party source state

| Tool | Returns | Backed by | Auth |
|---|---|---|---|
| `integrations.list_sources` | `[{ source, connected, lastSyncAt, missingFields }]` (sanitised) | Supabase `source_connection_state` | admin token |
| `integrations.get_overview` | `{ totalSources, byStatus: { connected, stale, never_connected }, lastSyncAt }` | aggregated from `source_connection_state` | No Auth (counts only) |
| `integrations.whoop.get_status` | `{ connected, lastWhoopSyncAt, missing: ['recovery'/'sleep'/'strain'] }` | `source_connection_state` row for whoop_oauth | admin token |
| `integrations.polar.get_status` | same shape | `source_connection_state` row for polar_oauth | admin token |
| `integrations.health.get_overview` | `{ ios: { appleHealth: 'connected'/'never_seen' }, android: { healthConnect: 'connected'/'never_seen' } }` (no per-user data) | aggregated `source_connection_state` | admin token |

Per-user health values NEVER appear here. Aggregate counts only.
The existing `/api/health/*` admin routes carry the per-user
detail.

### `handoff.*` — cross-project handoff artifacts

| Tool | Returns | Backed by |
|---|---|---|
| `handoff.get_latest` | `[{ source: 'mobile'\|'website', generatedAt, summary, manualStepsCount }]` ordered by `generatedAt desc`, ≤2 entries | `connector_handoff` (mobile) + proxied `website.get_handoff` |
| `handoff.list` | last 10 across both sources | composed |
| `handoff.get_by_source` | `{ source, payload }` for either side | direct |

`source` field is the disambiguator that prevents the "stale
April handoff" confusion: a `handoff.get_latest` response with
two entries makes it obvious which is which.

## 5. Auth model

Two layers, identical to the current Worker:

- **No Auth (public-safe):** `project.*` (aggregates only),
  `mobile.get_*_overview` (counts only),
  `integrations.get_overview`, `website.*` (proxy passthrough —
  the website MCP itself is No Auth so the namespace inherits).
  Strict allow-list per tool: every output field built from
  named scalars, never a free-text passthrough.
- **Admin token (private):** every `mobile.get_*` that returns
  free text, every `integrations.<source>.get_status`,
  `handoff.list` / `handoff.get_*`. Uses the existing
  `ATHLETE_MEMORY_API_TOKEN` Worker secret.

ChatGPT's connector form supports No Auth. Public-safe tools
work in any chat. Private tools fail-soft: tool result is
`{ isError: true, content: [{ type: 'text', text: 'admin token
required for this tool' }] }` so the chat can fall back to the
public-safe equivalent (`mobile.get_lane_overview` instead of
`mobile.get_coder_lanes` etc).

## 6. Migration checklist

Each phase is gated; no phase opens until the previous one has
held for the named period.

### Phase 0 — design (this batch, docs only)

- [x] `docs/UNIFIED_MCP_PLAN.md` (this file).
- [x] No code or config touched.
- [x] No existing endpoint deleted or modified.

### Phase 1 — additive Worker route (separate batch)

Lane: this codebase. Lane 2 (build autopilot with confirmation).

- [ ] `cloudflare-worker/src/mcp-v2.ts` — new handler.
- [ ] Worker route registration: `POST /mcp/v2`.
- [ ] Tool registry table mapping each `project.*` /
      `mobile.*` / `integrations.*` / `handoff.*` to its
      builder function.
- [ ] `website.*` proxy: forwards JSON-RPC body to
      `mcp.lauburugrapplingmap.com/mcp`, preserves
      `Mcp-Session-Id` between requests, re-wraps response with
      Worker's negotiated content-type (SSE or JSON).
- [ ] `auth: 'public' | 'admin'` flag per tool entry; the
      route checks the flag before dispatching.
- [ ] Live integration test
      (`chat-app/src/server/scripts/test-mcp-v2-live.ts`):
      tools/list returns the full namespaced surface; each
      `*.get_*_overview` 200s without auth; each
      `mobile.get_<full>` 403s without auth; `website.*`
      passthrough returns the same payload as a direct call.
- [ ] Existing `/mcp` and `/mcp/public` remain unchanged and
      pass their existing tests.
- [ ] `npm run mcp:test:public-redaction` still passes
      against `/mcp/public`.
- [ ] Public-safe redaction test extended for `/mcp/v2`
      verifying the same dangerous-pattern grep on every
      No-Auth tool output.

### Phase 2 — dual-track ChatGPT connector availability

Lane: docs only.

- [ ] `docs/CHATGPT_CONNECTOR_SETUP.md` adds a **new**
      "Lauburu MCP (unified)" connector entry pointing at
      `/mcp/v2` with No Auth.
- [ ] Existing entries ("Lauburu MCP (mobile dev)" at
      `/mcp/public`, "GrapplingMap MCP (website)" at
      `mcp.lauburugrapplingmap.com/mcp`) stay documented,
      flagged as "still works; can run alongside the unified
      connector".
- [ ] Phone test checklist updated: from a fresh chat, the
      unified connector should resolve `project.get_overview`
      and `website.list_pending_suggestions` in the same
      session.

### Phase 3 — soft cutover (≥7 days after Phase 2)

Lane: docs only.

- [ ] `CHATGPT_CONNECTOR_SETUP.md` flips the recommended
      connector to "Lauburu MCP (unified)"; the other two
      stay listed under "alternative connectors still
      supported".
- [ ] `MCP_CANONICAL_STATE.md` adds a "Phase 3 deprecation
      notice" section pointing at
      `UNIFIED_MCP_PLAN.md`.

### Phase 4 — hard cutover (≥30 days after Phase 3, optional)

Lane: this codebase.

- [ ] Phase-4 readiness gate: zero open issues against the
      unified endpoint AND every active client (mobile app,
      Aaron's ChatGPT, Codex, Claude Code) has been confirmed
      using `/mcp/v2`.
- [ ] `lauburu-mcp-preview…/mcp/public` and
      `lauburu-mcp-preview…/mcp` retire — the route handlers
      stay but return a `410 Gone` JSON-RPC error pointing at
      `/mcp/v2`.
- [ ] `chat-app/src/server/scripts/test-mcp-worker-live.ts`
      retired in favour of the v2 test.
- [ ] `mcp.lauburugrapplingmap.com/mcp` is **untouched** —
      that's a different codebase. We continue to proxy it via
      `website.*`.
- [ ] WHOOP MCP, if it exists at a separate URL, is also
      **untouched** — out of scope.

### Phase 5 — optional, never required

Lane: not in scope without an explicit owner-approved batch.

- [ ] Custom domain on the v2 endpoint
      (`mcp.lauburu.dev/v2` or similar). Until then,
      `…workers.dev/mcp/v2` is the canonical URL.
- [ ] Auth upgrade from API-key to OAuth, when ChatGPT's
      connector form supports it natively.

## 7. Tool mapping — current → unified

| Current tool | Source | Unified tool |
|---|---|---|
| (this repo) `get_public_mcp_health` (`/mcp/public`) | mobile MCP | `project.get_overview` (covers it) and `mobile.get_health` (new) |
| (this repo) `get_lane_overview` (`/mcp/public`) | mobile MCP | `mobile.get_lane_overview` (No Auth) |
| (this repo) `get_build_overview` (`/mcp/public`) | mobile MCP | `mobile.get_build_overview` (No Auth) |
| (this repo) `get_repo_overview` (`/mcp/public`) | mobile MCP | `mobile.get_repo_overview` (No Auth) |
| (this repo) `get_work_status` (`/mcp` admin) | mobile MCP | `mobile.get_work_status` (admin) |
| (this repo) `get_coder_lanes` (`/mcp` admin) | mobile MCP | `mobile.get_coder_lanes` (admin) |
| (this repo) `get_build_status` (`/mcp` admin) | mobile MCP | `mobile.get_build_status` (admin) |
| (this repo) `get_handoff` (`/mcp` admin) | mobile MCP | `mobile.get_handoff` (admin) |
| (this repo) `get_terminal_summary` (`/mcp` admin) | mobile MCP | `mobile.get_terminal_summary` (admin) |
| (website) `get_work_status` | website MCP | `website.get_work_status` (proxy) |
| (website) `get_handoff` | website MCP | `website.get_handoff` (proxy) |
| (website) `list_pending_suggestions` | website MCP | `website.list_pending_suggestions` (proxy) |
| (website) `get_suggestion` | website MCP | `website.get_suggestion` (proxy) |
| (website) `submit_suggestion` | website MCP | `website.submit_suggestion` (proxy, write) |
| (website) `approve_suggestion_for_preview` | website MCP | `website.approve_suggestion_for_preview` (proxy, write) |
| (website) `list_automation_batches` | website MCP | `website.list_automation_batches` (proxy) |
| (website) `get_automation_state` | website MCP | `website.get_automation_state` (proxy) |
| (website) `get_preview_status` | website MCP | `website.get_preview_status` (proxy) |
| (website) `start_preview_run` / `advance_phase` / `approve_batch` | website MCP | `website.*` (proxy, write) |
| (website) `create_handoff_artifact` | website MCP | `website.create_handoff_artifact` (proxy, write) |
| (website) `update_work_status` | website MCP | `website.update_work_status` (proxy, write) |
| (website) `create_prompt_job` / `list_prompt_jobs` / `get_prompt_job` / `claim_prompt_job` / `complete_prompt_job` / `fail_prompt_job` / `cancel_prompt_job` | website MCP | `website.<same>` (proxy) |
| (website) `get_daily_performance_object` | website MCP | `website.get_daily_performance_object` (proxy) |
| (website) `get_user_health_summary` | website MCP | `website.get_user_health_summary` (proxy) |
| (website) `get_user_shared_memory` | website MCP | `website.get_user_shared_memory` (proxy) |
| (website) `list_provider_registry` | website MCP | `website.list_provider_registry` (proxy) |
| (WHOOP MCP, if present) `get_today_recovery` etc | WHOOP MCP | NOT proxied in v1; documented as `integrations.whoop.*` placeholder. WHOOP MCP stays separate until the source's URL is documented. |

## 8. Data source matrix

The "where does this answer come from?" lookup. Used by the
Worker's tool router and surfaced in every response as
`{ source: 'mobile'|'website'|'composed', dataStore }`.

| Tool | Source | Data store |
|---|---|---|
| `project.*` | composed | this repo's `connector_*` + website MCP `list_pending_suggestions` |
| `mobile.*_overview` | mobile | `connector_*` Supabase tables (this repo) |
| `mobile.get_<full>` | mobile | `/api/*` REST (this repo) |
| `website.*` | website | proxied to `mcp.lauburugrapplingmap.com/mcp` |
| `integrations.*` | mobile | Supabase `source_connection_state` (this repo's project) |
| `handoff.get_latest` / `handoff.list` | composed | this repo's `connector_handoff` + website `get_handoff` |
| `handoff.get_by_source` | mobile or website depending on arg | named store |

Every public-safe tool response carries `dataSource: { source,
freshness }` so the consumer can tell where the answer came
from. The "stale" disambiguation that
`docs/MCP_CANONICAL_STATE.md` solves manually becomes a
machine-readable field.

## 9. Live vs repo-only separation

Every tool response carries an explicit `state` enum on each
data point:

- `live` — the entity is running in production / a deployed
  component (Worker version, last released mobile build, etc).
- `repo-only` — committed to `main` but not yet shipped.
- `tester-build` — will ship to testers when the next paired
  build dispatch goes.
- `blocked` — cannot move without an external action.

Mirrors the four-value enum already used by
`docs/APP_DEVELOPMENTS.md` and `/api/control_centre`. Reusing
it across `project.*` and `handoff.*` keeps the consumer logic
trivial.

Tools that are themselves "repo-only" (i.e. defined in this
plan but not yet implemented in `mcp-v2.ts`) carry
`tools/list` entries flagged
`description: '[planned, Phase X]'` so consumers can choose to
hide them from rendering until Phase 1 ships.

## 10. Anti-rules

- **No deletion of any current MCP endpoint in the same commit
  that adds `/mcp/v2`.** The migration is additive.
- **No coupling of website-project writes to this codebase's
  release cycle.** The `website.*` namespace is a transparent
  proxy. If `mcp.lauburugrapplingmap.com` is down, those tools
  return a `proxy_unavailable` error — they do NOT fall back
  to a stale local copy.
- **No raw athlete health values in any namespace.**
  `integrations.*` exposes connection state only; per-user
  values live behind the existing user-token-gated mobile
  routes.
- **No tokens / EAS UUIDs / GitHub run IDs / file paths in any
  No-Auth namespace.** The same dangerous-pattern grep that
  guards `/mcp/public` extends to every No-Auth tool in
  `/mcp/v2`.
- **No state-sync from one MCP to the other.** The website's
  pending suggestions queue belongs to that project; this
  codebase's `connector_backlog_items` belongs to this project.
  They render alongside each other in `project.get_overview`,
  not merged.
- **No silent expansion of namespaces.** Adding a new tool
  requires a doc commit updating this file and the per-tool
  table in § 4 BEFORE the implementation lands.

## 11. ChatGPT-facing setup (after Phase 2)

After Phase 2, the recommended ChatGPT connector list is:

| Display name | URL | Auth | Use it for |
|---|---|---|---|
| `Lauburu MCP (unified)` | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2` | No Auth | Default — every namespace; includes both projects |
| `Lauburu MCP (mobile dev, legacy)` | `…/mcp/public` | No Auth | Optional — keeps working; identical scope to `mobile.*` in unified |
| `GrapplingMap MCP (website, legacy)` | `mcp.lauburugrapplingmap.com/mcp` | No Auth | Optional — keeps working; identical scope to `website.*` in unified |

Aaron picks one. Two if he wants both. Three if he wants
side-by-side comparison during the dual-track period.

## 12. What this plan does NOT do

- Does NOT touch `mcp.lauburugrapplingmap.com` codebase. That
  project's tools are proxied unchanged.
- Does NOT auth-upgrade ChatGPT to support API-key /
  OAuth-protected tools. Until ChatGPT's connector form
  supports it, admin-token tools stay unreachable from
  ChatGPT — same as today.
- Does NOT change the mobile app's `connector-status-client.ts`
  contract. That client uses `/api/*` REST, which stays
  exactly as is.
- Does NOT remove `docs/MCP_CANONICAL_STATE.md`. That doc
  stays accurate until Phase 3 (when the unified URL becomes
  the recommended single entry point).

## 13. What lands in the next batch (Phase 1 implementation)

In a separate commit, when this plan is approved:

1. `cloudflare-worker/src/mcp-v2.ts` — new file, new handler.
2. Tool builders that reuse the existing `getSupabaseAdapter`
   helpers and the existing `/api/*` route helpers.
3. JSON-RPC proxy for `website.*` calls.
4. `cloudflare-worker/src/worker.ts` — adds the `/mcp/v2`
   path; existing `/mcp`, `/mcp/public`, `/api/*` paths
   untouched.
5. `chat-app/src/server/scripts/test-mcp-v2-live.ts` — live
   integration test.
6. `npm run mcp:test:v2-live` shortcut in root `package.json`.
7. Update `docs/CHATGPT_CONNECTOR_SETUP.md` with the new
   connector entry (Phase 2 doc work bundled with the Phase 1
   code if Aaron wants a single review surface).

Estimated size: one Worker file (~300 lines), one test
(~150 lines), ≤30-line worker.ts edit, doc updates. Single
review pass.
