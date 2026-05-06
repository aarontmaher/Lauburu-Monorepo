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

## 14. MCP inventory audit — 2026-05-07

Read-only audit sources:

- Live MCP JSON-RPC calls to
  `https://mcp.lauburugrapplingmap.com/mcp`:
  `initialize`, `tools/list`, `resources/list`, `prompts/list`.
- Local repo route definitions in `cloudflare-worker/src/mcp.ts`
  and `cloudflare-worker/src/mcp-public.ts`.
- Local WHOOP MCP implementation at
  `~/whoop-integration/whoop_mcp.py`.
- Local MCP client configuration in Codex / Claude / VS Code,
  redacted in this doc. Do not publish credential values.

### 14.1 Inventory table

| MCP | Item | Kind | Data source | Live / repo-dev state | Known consumers | Classification | Unified mapping |
|---|---|---|---|---|---|---|---|
| Mobile public MCP | `get_public_mcp_health` | tool | Worker + Supabase config probe | live Worker, public-safe | ChatGPT connector, diagnostics | merge into unified | `project.get_overview` + `mobile.get_mcp_health` |
| Mobile public MCP | `get_lane_overview` | tool | Supabase `connector_coder_lanes` counts | live Worker, public-safe | ChatGPT connector | merge into unified | `mobile.get_lane_overview` |
| Mobile public MCP | `get_build_overview` | tool | Supabase `connector_build_status` enum projection | live Worker, public-safe | ChatGPT connector | merge into unified | `mobile.get_build_overview` |
| Mobile public MCP | `get_repo_overview` | tool | Supabase `connector_work_status.payload.repoStatus` | live Worker, public-safe | ChatGPT connector | merge into unified | `mobile.get_repo_overview` |
| Mobile public MCP | resources | resource list | none | live returns empty | none | keep empty / no migration | none |
| Mobile public MCP | prompts | prompt list | none | live returns empty | none | keep empty / no migration | none |
| Mobile private MCP | `get_work_status` | tool | Supabase `connector_work_status` | live Worker, admin-token gated | laptop curl / future authenticated clients | merge into unified | `mobile.get_work_status` |
| Mobile private MCP | `get_coder_lanes` | tool | Supabase `connector_coder_lanes` | live Worker, admin-token gated | laptop curl / AdminDev-equivalent data | merge into unified | `mobile.get_coder_lanes` |
| Mobile private MCP | `get_build_status` | tool | Supabase `connector_build_status` | live Worker, admin-token gated | laptop curl / AdminDev-equivalent data | merge into unified | `mobile.get_build_status` |
| Mobile private MCP | `get_handoff` | tool | Supabase `connector_handoff` | live Worker, admin-token gated | laptop curl / AdminDev-equivalent data | merge into unified | `mobile.get_handoff` |
| Mobile private MCP | `get_terminal_summary` | tool | Supabase `connector_terminal_summary` | live Worker, admin-token gated | laptop curl / AdminDev-equivalent data | merge into unified | `mobile.get_terminal_summary` |
| Mobile private MCP | resources | resource list | none | live returns empty | none | keep empty / no migration | none |
| Mobile private MCP | prompts | prompt list | none | live returns empty | none | keep empty / no migration | none |
| Website MCP | `list_pending_suggestions` | tool | website suggestion queue | live production website MCP | ChatGPT, Codex app approvals, website automation | keep unique, proxy | `website.list_pending_suggestions` |
| Website MCP | `get_suggestion` | tool | website suggestions / next / accepted files | live production website MCP | ChatGPT, website automation | keep unique, proxy | `website.get_suggestion` |
| Website MCP | `submit_suggestion` | tool, write | website suggestion inbox | live production website MCP | ChatGPT / website suggestion flow | keep unique, proxy with write warning | `website.submit_suggestion` |
| Website MCP | `approve_suggestion_for_preview` | tool, write | website markdown queue | live production website MCP | website automation | keep unique, proxy with write warning | `website.approve_suggestion_for_preview` |
| Website MCP | `list_automation_batches` | tool | website automation batch files | live production website MCP | ChatGPT / automation | keep unique, proxy | `website.list_automation_batches` |
| Website MCP | `get_automation_state` | tool | website `AUDIT_STATE.json` | live production website MCP | ChatGPT / automation | keep unique, proxy | `website.get_automation_state` |
| Website MCP | `get_preview_status` | tool | website preview/implementation status | live production website MCP | website automation | keep unique, proxy | `website.get_preview_status` |
| Website MCP | `start_preview_run` | tool, write | website automation state | live production website MCP | website automation | keep unique, proxy with write warning | `website.start_preview_run` |
| Website MCP | `advance_phase` | tool, write | website orchestrate script | live production website MCP | website automation | keep unique, proxy with write warning | `website.advance_phase` |
| Website MCP | `approve_batch` | tool, write | website orchestrate script / audit state | live production website MCP | website automation | keep unique, proxy with write warning | `website.approve_batch` |
| Website MCP | `get_handoff` | tool | website handoff artifact | live production website MCP | ChatGPT / website handoff | duplicate name, unique data | `website.get_handoff` |
| Website MCP | `create_handoff_artifact` | tool, write | website handoff artifact store | live production website MCP | website automation | keep unique, proxy with write warning | `website.create_handoff_artifact` |
| Website MCP | `get_work_status` | tool | website agent work-status store | live production website MCP | ChatGPT, Codex app approvals | duplicate name, unique data | `website.get_work_status` |
| Website MCP | `update_work_status` | tool, write | website agent work-status store | live production website MCP | Codex app approval configured | duplicate name, unique data | `website.update_work_status` |
| Website MCP | `create_prompt_job` | tool, write | website prompt-job queue | live production website MCP | website automation / possible mobile hook via shared client | keep unique, proxy | `website.create_prompt_job` |
| Website MCP | `list_prompt_jobs` | tool | website prompt-job queue | live production website MCP | website automation; mobile hook references shared prompt-job client | keep unique, proxy | `website.list_prompt_jobs` |
| Website MCP | `get_prompt_job` | tool | website prompt-job queue | live production website MCP | website automation | keep unique, proxy | `website.get_prompt_job` |
| Website MCP | `claim_prompt_job` | tool, write | website prompt-job queue | live production website MCP | website automation | keep unique, proxy with write warning | `website.claim_prompt_job` |
| Website MCP | `complete_prompt_job` | tool, write | website prompt-job queue | live production website MCP | website automation | keep unique, proxy with write warning | `website.complete_prompt_job` |
| Website MCP | `fail_prompt_job` | tool, write | website prompt-job queue | live production website MCP | website automation | keep unique, proxy with write warning | `website.fail_prompt_job` |
| Website MCP | `cancel_prompt_job` | tool, write | website prompt-job queue | live production website MCP | website automation | keep unique, proxy with write warning | `website.cancel_prompt_job` |
| Website MCP | `get_daily_performance_object` | tool | website WHOOP performance store | live production website MCP | ChatGPT / website health surfaces | keep unique for website, consider WHOOP overlap later | `website.get_daily_performance_object` |
| Website MCP | `get_user_health_summary` | tool | website normalized multi-provider store | live production website MCP | ChatGPT / website user-health lookup | keep unique, auth review needed | `website.get_user_health_summary` |
| Website MCP | `get_user_shared_memory` | tool | website per-user shared memory store | live production website MCP | ChatGPT / website memory lookup | keep unique, auth review needed | `website.get_user_shared_memory` |
| Website MCP | `list_provider_registry` | tool | website provider registry | live production website MCP | ChatGPT / website docs | merge conceptually | `integrations.list_provider_registry` or `website.list_provider_registry` |
| Website MCP | resources | resource list | none | live returns empty | none | keep empty / no migration | none |
| Website MCP | prompts | prompt list | none | live returns empty | none | keep empty / no migration | none |
| WHOOP MCP | `get_today_recovery` | tool | local SQLite WHOOP daily summaries | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_today_recovery` |
| WHOOP MCP | `get_recovery_history` | tool | local SQLite recovery rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_recovery_history` |
| WHOOP MCP | `get_hrv_trend` | tool | local SQLite HRV rows / derived rolling metrics | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_hrv_trend` |
| WHOOP MCP | `get_sleep_last_night` | tool | local SQLite sleep rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_sleep_last_night` |
| WHOOP MCP | `get_sleep_history` | tool | local SQLite sleep rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_sleep_history` |
| WHOOP MCP | `get_cycle_history` | tool | local SQLite cycle rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_cycle_history` |
| WHOOP MCP | `get_strain_history` | tool | local SQLite strain projection | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_strain_history` |
| WHOOP MCP | `get_workout_history` | tool | local SQLite workout rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_workout_history` |
| WHOOP MCP | `get_workout_zone_history` | tool | local SQLite workout zone rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_workout_zone_history` |
| WHOOP MCP | `get_training_load_summary` | tool | local SQLite WHOOP workout/cycle aggregates | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_training_load_summary` |
| WHOOP MCP | `get_recovery_vs_strain` | tool | local SQLite joined daily summaries | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_recovery_vs_strain` |
| WHOOP MCP | `get_recovery_vs_sleep` | tool | local SQLite joined daily summaries | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_recovery_vs_sleep` |
| WHOOP MCP | `get_daily_summary` | tool | local SQLite recovery/sleep/strain/workout/journal rows | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_daily_summary` |
| WHOOP MCP | `get_stored_daily_metrics` | tool | local SQLite daily metrics / health flags | local authenticated/dev | Claude/Codex local MCP | unique authenticated WHOOP | `integrations.whoop.get_stored_daily_metrics` |
| WHOOP MCP | `get_health_flags` | tool | local SQLite health flags | local authenticated/dev | Claude/Codex local MCP | unique but derived | `integrations.whoop.get_health_flags` |
| WHOOP MCP | `get_correlation_snapshots` | tool | local SQLite correlation snapshots | local authenticated/dev | Claude/Codex local MCP | unique but derived/historical | `integrations.whoop.get_correlation_snapshots` |
| WHOOP MCP | `get_grappling_sessions` | tool | local SQLite manual/grappling context linked to WHOOP dates | local authenticated/dev | Claude/Codex local MCP | unique but may overlap app training logs later | `integrations.whoop.get_grappling_sessions` |
| WHOOP MCP | `get_manual_daily_context` | tool | local SQLite manual context | local authenticated/dev | Claude/Codex local MCP | unique but may overlap app check-ins later | `integrations.whoop.get_manual_daily_context` |
| WHOOP MCP | `get_intelligence_ready_view` | tool | local SQLite joined WHOOP intelligence view | local authenticated/dev | Claude/Codex local MCP | unique; high privacy risk | `integrations.whoop.get_intelligence_ready_view` |
| WHOOP MCP | `get_data_completeness_report` | tool | local SQLite + API/CSV/manual coverage state | local authenticated/dev | Claude/Codex local MCP | unique operator diagnostic | `integrations.whoop.get_data_completeness_report` |
| WHOOP MCP | `get_sync_status` | tool | local SQLite sync status | local authenticated/dev | Claude/Codex local MCP | unique operator diagnostic | `integrations.whoop.get_sync_status` |
| WHOOP MCP | `get_auth_status` | tool | local token/auth lifecycle diagnostics | local authenticated/dev | Claude/Codex local MCP | unique but sensitive | `integrations.whoop.get_auth_status` admin-only |
| WHOOP MCP | `get_webhook_status` | tool | local SQLite webhook status | local authenticated/dev | Claude/Codex local MCP | unique operator diagnostic | `integrations.whoop.get_webhook_status` |
| WHOOP MCP | `get_user_profile` | tool | local SQLite WHOOP profile | local authenticated/dev | Claude/Codex local MCP | unique but private/delete from public | `integrations.whoop.get_user_profile` admin-only |
| WHOOP MCP | `get_body_measurements` | tool | local SQLite body measurements | local authenticated/dev | Claude/Codex local MCP | unique but private/delete from public | `integrations.whoop.get_body_measurements` admin-only |
| WHOOP MCP | `get_sport_labels` | tool | static local sport-id mapping | local/dev | Claude/Codex local MCP | merge as static registry | `integrations.whoop.get_sport_labels` public-safe possible |
| WHOOP MCP | `/health` | custom HTTP route | local SQLite + token/config presence booleans | local/dev or hosted WHOOP MCP | health checks | keep unique, admin/private if remote | `integrations.whoop.get_bridge_health` |
| WHOOP MCP | `/data/today` | custom HTTP route | local SQLite latest daily snapshot | local/dev or website hydration | website frontend hydration | unique authenticated WHOOP data | `integrations.whoop.get_today_snapshot` admin-only |
| WHOOP MCP | `/diag/token-check` | custom HTTP route | token file + live WHOOP API probe | local/dev | operator only | unsafe for public; keep admin/local only | `integrations.whoop.diag.token_check` admin-only |
| WHOOP MCP | `/diag/trigger-sync` | custom HTTP route, write | live WHOOP API sync + SQLite writes | local/dev | operator only | unsafe to proxy publicly | `integrations.whoop.sync.trigger` disabled unless admin |
| WHOOP MCP | `/diag/force-reseed` | custom HTTP route, write | env token seed + token file write | local/dev | operator only | unsafe/stale/delete candidate for unified public | do not expose in unified |
| WHOOP MCP | `/whoop/authorize` / `/whoop/callback` | custom HTTP routes | WHOOP OAuth flow + token file | local/dev or hosted WHOOP MCP | operator OAuth | keep separate from unified until OAuth design | not in v1 unified |
| WHOOP MCP | webhook route | custom HTTP route, write | WHOOP webhook validation + SQLite writes | hosted/local WHOOP bridge | WHOOP webhooks | keep separate ingress | not an MCP tool |
| WHOOP MCP | resources | resource list | none found in code/tool registry | local/dev | none | no migration | none |
| WHOOP MCP | prompts | prompt list | none found in code/tool registry | local/dev | none | no migration | none |

### 14.2 Unique value assessment

- Website MCP is not only project-status metadata. It is the live
  website automation and suggestion-control surface. It has write
  tools, prompt-job tools, website handoffs, website agent status,
  provider registry, and user-health/memory lookups.
- WHOOP MCP provides unique authenticated WHOOP functionality.
  It is not merely project-status metadata: most tools read
  local SQLite WHOOP-derived recovery, sleep, HRV, strain,
  workout, webhook, auth, and completeness data. Some routes can
  trigger sync or reseed tokens, so they are not safe for a
  public unified MCP.
- Mobile MCP is the current live control-centre status surface
  for this repo. Its public endpoint is intentionally small and
  sanitized. The Admin/Dev mobile app consumes `/api/*` REST,
  not JSON-RPC MCP.

### 14.3 Merge / delete recommendation by group

| Group | Recommendation | Why |
|---|---|---|
| Mobile public MCP tools | Merge into unified `mobile.*`; keep legacy wrappers first | They are already sanitized and are the safest ChatGPT-readable status path. |
| Mobile private MCP tools | Merge into unified `mobile.*` admin-only; keep `/api/*` forever | Mobile Admin/Dev depends on REST. MCP is an alternate client surface. |
| Website suggestion / automation tools | Proxy under `website.*`; do not delete | Separate website data store and active/historical backlog. |
| Website write tools | Proxy only with explicit write classification and confirmation policy | They mutate website queues/state. No silent execution from public clients. |
| Website user health / memory tools | Keep under `website.*`; require auth review before public exposure | They may return per-user data. Treat No-Auth status as risk until audited. |
| Website provider registry | Consider merging into `integrations.list_provider_registry` after compatibility wrapper | It is catalogue-like and can be public-safe if no private data. |
| WHOOP read-only health data tools | Keep separate now; later expose as admin-only `integrations.whoop.*` if needed | Unique authenticated health data; high privacy risk. |
| WHOOP diagnostics | Keep local/admin-only; do not expose through public unified MCP | Auth/token/webhook details are operationally sensitive. |
| WHOOP write routes (`trigger-sync`, `force-reseed`, OAuth callback, webhook) | Do not fold into MCP v1; never expose No-Auth | They mutate tokens/data or receive vendor webhooks. |
| Empty resources/prompts | Keep empty | No existing client depends on resources/prompts. |

### 14.4 Risks of deletion

- Deleting website MCP tools would lose access to the website
  suggestion queue, automation batches, prompt jobs, and historic
  handoffs. That would also break any ChatGPT/Codex workflow
  currently bound to the GrapplingMap Control Centre connector.
- Deleting mobile public MCP would remove ChatGPT's No-Auth view
  of this repo's live lane/build/repo status.
- Deleting mobile private MCP is lower risk than deleting `/api/*`,
  but still breaks laptop curl / future authenticated MCP clients.
- Deleting WHOOP MCP would remove local authenticated WHOOP
  analysis, sync/auth/webhook diagnostics, and the only verified
  source for several WHOOP-specific views. It may also break local
  Claude/Codex tools.
- Deleting WHOOP token/OAuth routes without a replacement risks
  losing the ability to refresh or reseed authenticated WHOOP
  access.

### 14.5 Unified namespace mapping

Recommended final namespaces:

| Namespace | Owns | Examples |
|---|---|---|
| `project.*` | Cross-project overview, top priorities, live/repo-only rollups | `project.get_overview`, `project.list_priorities` |
| `mobile.*` | This repo's control-centre, build, repo, lanes, terminal summaries | `mobile.get_lane_overview`, `mobile.get_control_centre` |
| `website.*` | Website project suggestions, automation, website handoffs, website agent state | `website.list_pending_suggestions`, `website.get_work_status` |
| `handoff.*` | Cross-project latest handoff summaries with source disambiguation | `handoff.get_latest`, `handoff.get_by_source` |
| `integrations.*` | Provider registry and connection state | `integrations.list_sources`, `integrations.list_provider_registry` |
| `integrations.whoop.*` | Authenticated WHOOP-only data and diagnostics | `integrations.whoop.get_daily_summary`, `integrations.whoop.get_sync_status` |
| `integrations.polar.*` | Future Polar direct state | `integrations.polar.get_status` |
| `integrations.health.*` | Apple Health / Health Connect source state | `integrations.health.get_overview` |

### 14.6 Safe cutover plan

1. Add `/mcp/v2` compatibility wrappers first. Do not remove
   `/mcp/public`, `/mcp`, or `mcp.lauburugrapplingmap.com/mcp`.
2. Test old endpoints:
   - Mobile `/mcp/public`: `initialize`, `tools/list`, each
     public tool call.
   - Mobile `/mcp`: unauthenticated 403, authenticated
     `tools/list`, each private read tool.
   - Website `/mcp`: `initialize`, `tools/list`,
     `resources/list`, `prompts/list`.
   - WHOOP local MCP: tools list through local client only; do
     not call data tools in a public audit unless explicitly
     needed.
3. Test new unified endpoint:
   - `tools/list` includes namespaced wrappers.
   - Public-safe tools contain no free text, file paths, tokens,
     IDs, secrets, raw logs, or per-user health values.
   - Admin-only tools reject unauthenticated calls.
   - Website proxy preserves old website tool response shapes
     under `website.*`.
4. Mark old endpoints deprecated in docs only after `/mcp/v2`
   works for ChatGPT, Claude, Codex, mobile Admin/Dev, and any
   automation scripts.
5. Delete or return `410 Gone` only after confirmed unused for
   at least 30 days. Do not delete website MCP or WHOOP MCP from
   this repo.

### 14.7 Files/configs that would need changes

| Path / config | Change needed |
|---|---|
| `cloudflare-worker/src/mcp-v2.ts` | New unified router and namespace registry. |
| `cloudflare-worker/src/worker.ts` | Add `/mcp/v2` route; leave legacy routes intact. |
| `cloudflare-worker/src/mcp-public.ts` | No immediate change; later compatibility wrapper/deprecation notice only. |
| `cloudflare-worker/src/mcp.ts` | No immediate change; later compatibility wrapper/deprecation notice only. |
| `chat-app/src/server/scripts/test-mcp-v2-live.ts` | New live integration test for public/admin behavior and website proxy. |
| `cloudflare-worker/test/*` | Extend dangerous-pattern redaction tests to `/mcp/v2`. |
| `docs/CHATGPT_CONNECTOR_SETUP.md` | Add unified connector entry after Phase 1 ships. |
| `docs/MCP_CANONICAL_STATE.md` | Keep split-state doc until Phase 3; then add deprecation note. |
| `apps/mobile/src/services/connector-status-client.ts` | No change required for MCP v2; mobile uses `/api/*` REST. Optional later: read `/api/control_centre` only. |
| `~/.codex/config.toml` | Optional: update approval entries if tool names move to `website.*`. |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Keep WHOOP MCP local; never publish credential values. |
| `~/LauburuGrapplingMap/.vscode/mcp.json` | Optional: add unified URL after Phase 2, keep website URL during comparison. |

### 14.8 Final recommendation

Do **not** delete any MCP now.

Merge by adding a unified compatibility layer, not by moving data
stores:

- `mobile.*` wraps this repo's current Worker/Supabase status.
- `website.*` proxies the live website MCP unchanged.
- `integrations.whoop.*` remains **out of v1 public scope**.
  WHOOP MCP has unique authenticated WHOOP value and must stay
  local/admin-only until a privacy/auth design is approved.

The deletion target is only future legacy wrappers after proven
cutover, not the underlying website or WHOOP MCPs.
