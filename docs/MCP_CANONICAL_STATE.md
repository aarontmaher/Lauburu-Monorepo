# MCP canonical state — which MCP answers which question

There are two live HTTP MCP servers in Aaron's orbit, plus one
local WHOOP MCP exposed to local MCP clients. They are **not
duplicates**. They target different projects with different data
stores, so a ChatGPT chat connected to one will not see the
other's state. This doc names which is canonical for which
question and stops the "I asked ChatGPT and it said agents are
idle even though Claude is working right now" confusion.

Updated 2026-05-07.

## The split

| Server | URL | Scope | Codebase | Auth in ChatGPT |
|---|---|---|---|---|
| **Lauburu mobile-app MCP** (this repo) | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public` | Mobile-app dev state — Claude / Codex lane status, `/api/control_centre` snapshot, build/repo state, manual steps, suggestions backlog | `LauburuGrapplingMap-mobile` (this repo) | **No Auth** |
| **GrapplingMap System MCP** (website project) | `https://mcp.lauburugrapplingmap.com/mcp` | Website project — pending technique suggestions, automation batches, daily WHOOP performance objects, prompt jobs, project handoffs related to the website's automation loop | `grapplingmap` website project (separate repo) | **No Auth** |
| **WHOOP MCP** (local) | local stdio via Claude/Codex MCP config | Authenticated WHOOP-derived local SQLite data: recovery, sleep, HRV, strain, workouts, webhook/auth/sync diagnostics | `~/whoop-integration/whoop_mcp.py` | **Not a ChatGPT public connector** |

Both work. Both are reachable from ChatGPT. They expose tools
with overlapping names like `get_work_status`, `get_handoff`,
`list_pending_suggestions` — but those tools read from
different data stores. Asking one for state about the other
returns stale or unrelated answers, by design.

## Why mcp.lauburugrapplingmap.com looks "stale"

It is not stale relative to its own data — it accurately
reflects the website project's state at the time of the last
website-side write. It looks stale ONLY when the question is
about *this codebase's* current Claude / Codex / control-centre
state, because that lives in a different project's tables:

- The website MCP's `get_work_status` reads
  `agent-status/*.json` from the website project's repo /
  durable store. That feed has not been updated by THIS
  codebase's bridge — our bridge writes to Supabase
  `connector_*` tables that the website MCP doesn't know about.
- The website MCP's `get_handoff` reads the website's last
  `create_handoff_artifact` call — likely the April handoff
  Aaron mentioned.
- The website MCP's `list_pending_suggestions` reads the
  website's suggestion queue — the technique / website-feature
  suggestions, NOT this codebase's
  `connector_backlog_items` (FS-001…FS-006).

None of this is broken. It's two products on the same brand
hosted by the same person.

## Decision: do NOT sync state between the two

The safe move is to keep the two stores separate and document
the split, NOT to forward state from one MCP to the other.
Reasons:

- The website project owns its own data lifecycle. Forcing
  this codebase's bridge to also write to the website project's
  store would couple two release cycles together — every
  mobile-bridge change would risk breaking the website's
  automation.
- The two projects have different "agent" definitions. The
  website MCP's `agent` is a website-side coding agent on the
  website's automation loop. This codebase's lane is a
  laptop-side coder on the mobile-app loop. Merging them
  would lose the distinction.
- Aaron's existing technique suggestions in the website MCP's
  pending queue are HISTORICAL product backlog (knowledge-base
  improvements, technique edits, technique-tree changes).
  They belong in the website project's queue, not this
  codebase's `connector_backlog_items`. Don't move them, don't
  delete them.

## Decision: canonical paths

For live "what is Claude / Codex doing right now? what's the
mobile build state? what manual steps does Aaron have open?"
**questions, ChatGPT must use the unified Worker MCP, not the
website MCP:**

```
https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2
```

Single canonical tool call (No Auth):

- **`project.get_current_state`** — composes priority / blocker
  / next action + per-lane (claude / codex) status enum +
  sanitised task summaries (≤140 char) + Android v / iOS Build
  state + freshness flag. Response includes
  `source: 'supabase'`, `freshness.isStale`,
  `freshness.staleReason`, and `agents[]` with the actual
  lane-status enum (idle / working / blocked / needs_user /
  needs_review / done) — never "all idle" by default. **Use
  this as the first call from any new chat.**

Other public-safe tools at `/mcp/v2` (No Auth):

- `project.get_overview` — cross-project aggregate including
  website pending count.
- `project.get_work_status` — same priority / blocker / next
  action shape (subset of `get_current_state`).
- `project.list_priorities` — top active backlog item(s). The
  native iPhone/TestFlight automation item is repo-backed at
  rank 0 while the health-connectivity release gate remains the
  current work status.
- `mobile.get_lane_overview` / `mobile.get_build_overview` /
  `mobile.get_repo_overview` — counts/aggregates only.
- `handoff.get_latest` — composed across both projects, each
  entry tagged `source: 'mobile' | 'website'`.
- `qa.get_latest_result` — latest public-safe Agent QA gate
  summary. Distinguishes repo-only QA from installed-device QA
  and reports whether TestFlight/Internal QA builds are allowed.
- `integrations.get_overview` — per-platform exposure spec.

Legacy public preview path (`/mcp/public`, four tools, No Auth)
is also still live with the same `get_*_overview` /
`get_public_mcp_health` calls. It retires when Phase 4 of
`docs/UNIFIED_MCP_PLAN.md` opens — until then, both paths
coexist.

For richer detail (lane summaries, manual step text, full
build/handoff/terminal_summary/Agent QA detail) Aaron uses curl from the laptop
or the in-app Admin/Dev surface — both go through the
admin-token-gated `/api/*` routes or `mobile.get_<full>` v2
tools. ChatGPT does not currently support API-key auth in the
connector form.

Agent QA results are written with `npm run bridge:agent-qa -- <json>`
into a local ignored artifact, then carried by `npm run bridge:snapshot`
inside `connector_handoff.agentQaResult`. This is control-centre
status only, not athlete private memory. Public MCP sees only
the redacted `qa.get_latest_result` summary; full notes are
admin-gated at `mobile.get_agent_qa_result`.

For "what's pending in the website's automation queue? when's
the next batch? what techniques need editing?" **questions,
ChatGPT must use:**

```
https://mcp.lauburugrapplingmap.com/mcp
```

That's the website project's canonical state. Treat its
`get_work_status` / `get_handoff` answers as **website
project context, not this codebase**.

## What NOT to do

- **Do not delete the technique suggestions** stored in the
  website MCP's queue. They are product backlog. If they are
  stale, that's a separate website-project triage task.
- **Do not configure ChatGPT to point only at one of the two**
  if Aaron uses both projects. Add both connectors with
  distinct names so the chat can resolve cleanly.
- **Do not write a "sync from control-centre to website MCP"
  job** without an explicit owner-approved batch. The blast
  radius is two products at once.
- **Do not update the website MCP's `get_handoff` from this
  codebase's writers.** The website project owns that data.

## Recommended ChatGPT connector configuration

Two distinct connectors, both **No Auth**, distinct names so
ChatGPT lists them separately:

| Display name | URL | Use it for |
|---|---|---|
| `Lauburu MCP (mobile dev)` | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public` | Live Claude / Codex / build / repo / control-centre status for THIS repo. |
| `GrapplingMap MCP (website)` | `https://mcp.lauburugrapplingmap.com/mcp` | Website automation, technique suggestions, website handoffs. |

The WHOOP MCP should **not** be added to ChatGPT as a No-Auth
public connector. It exposes personal health data and
authenticated WHOOP-derived status. Keep it local or behind a
private/authenticated namespace if it is ever folded into the
unified MCP.

If WHOOP is folded into the unified MCP later, personal metrics
must live under authenticated `integrations.whoop.*` tools.
Apple Health / Health Connect hub summaries belong under
`integrations.health.*`; future direct Polar-specific metrics
belong under `integrations.polar.*`. `/mcp/public` and any
unauthenticated unified tools must never expose personal health
metrics.

The local WHOOP MCP is not a deletion candidate until the
unified MCP has equivalent authenticated WHOOP tools, secure
credential handling, live tests, and a confirmed audit showing
no remaining unique functionality.

## Why "stale" really means "empty store + no patch path"

A second probe (2026-05-07) confirmed the precise reason the
website MCP looks "stale" for this codebase's questions, and
why no code change in this repo can fix it:

1. **Website MCP `get_work_status` data is empty, not old.**
   The full response is null/idle for every agent it tracks:
   ```jsonc
   {
     "schema_version": 1,
     "agents": {
       "claude_chat":  { "task": null, "status": "idle", "branch": null, "commit": null, "summary": null, "updated_at": null },
       "claude_code":  { "task": null, "status": "idle", "branch": null, "commit": null, "summary": null, "updated_at": null },
       "codex":        { "task": null, "status": "idle", "branch": null, "commit": null, "summary": null, "updated_at": null },
       "chatgpt":      { "task": null, "status": "idle", "branch": null, "commit": null, "summary": null, "updated_at": null },
       "cowork":       { "task": null, "status": "idle", "branch": null, "commit": null, "summary": null, "updated_at": null }
     },
     "updated_at": null
   }
   ```
   This is **the website project's accurate state** — nobody
   has been writing to its `update_work_status` queue. Not a
   stale cache, not a regression; just an empty data store on
   a project where nobody is currently coding.

2. **The website MCP rejects every proxy write attempt from this
   No-Auth connector path.**
   Three different `clientInfo.name` identities (`owner-aaron`,
   `lauburu-mobile-bridge`, `claude-code`) all returned the
   same response from `update_work_status`:
   `{ ok: false, error: 'unauthorized', role: 'none' }`. The
   write gate is not on `clientInfo`; it is on something the
   v2 proxy can't synthesise (per-user ChatGPT account context
   or a server-side allowlist that doesn't include our
   proxy). There is **no patchable auth path** from this
   repo.

3. **This repo can only fix the unified v2 surface.** The
   `/mcp/v2` Worker now exposes public-safe read tools plus a
   narrow admin-token-gated priority intake tool
   (`project.submit_priority_suggestion`). ChatGPT No Auth
   still cannot write; unauthenticated writes remain blocked.
   Modifying the website MCP's `submit_suggestion` /
   `update_work_status` auth requires commits in the website
   project. The two projects keep their data lifecycles
   separate per § "Do NOT sync state between the two".

If a chat needs both views side-by-side, ChatGPT can be
configured with both connectors (Lauburu MCP unified +
GrapplingMap MCP website). Each tool answer carries the
`source` discriminator (`source: 'mobile'` vs
`source: 'website'`) on our `/mcp/v2` proxy responses, so the
chat doesn't have to guess which project a status came from.

## Read-only audit snapshot — 2026-05-07

Verified live / local facts:

- `https://mcp.lauburugrapplingmap.com/mcp` responds as
  `serverInfo.name = "GrapplingMap System"`,
  `version = "1.27.0"`.
- The website MCP exposes **25 tools**, **0 resources**, and
  **0 prompts** through `tools/list`, `resources/list`, and
  `prompts/list`.
- Local WHOOP MCP configuration exists in Claude Desktop as a
  stdio server named `whoop`, backed by `~/whoop-integration`.
  The config includes WHOOP client credentials; values must stay
  out of docs, prompts, and app UI.
- Codex's deferred MCP registry exposes WHOOP MCP tools, which
  means Codex can call local WHOOP tools when explicitly needed.
- Current mobile app code uses `/api/*` REST through
  `EXPO_PUBLIC_MCP_BASE_URL`, not the MCP JSON-RPC endpoint, for
  Admin/Dev phone cards.

Cleanup: any existing connector pointing at the wrong host
should be deleted per
`docs/CHATGPT_CONNECTOR_SETUP.md` § 4. Tool resolution within
a chat goes by connector name + tool name, so identical tool
names on different connectors are disambiguated by which
connector ChatGPT picked.

## Diagnostic for "is the connector wired correctly?"

Open a fresh chat (older chats snapshot the tool list at
chat-start time). Ask:

> Use Lauburu MCP (mobile dev) to call get_public_mcp_health.
> Then call get_lane_overview.

Expected: the diagnostic returns
`serverInfo.name = "lauburu-mcp-public-preview"` and the lane
overview returns counts grouped by status. If ChatGPT replies
that the tool isn't available, the connector isn't bound to
the chat — fix per `docs/CHATGPT_CONNECTOR_SETUP.md` § 2.

If the diagnostic returns
`serverInfo.name = "GrapplingMap System"` instead, the chat
called the website MCP — that's the wrong server for THIS
codebase's status. Use the other connector or rename them so
ChatGPT picks correctly.

## Tool inventory — public, admin, write-status (P1 spec-ready)

The unified Worker MCP at
`https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2`
exposes a clean public/admin split. Updated 2026-05-07.

### Public tools (No Auth)

These are safe for any ChatGPT connector. They never expose
prompt IDs, file paths, raw lane summaries longer than 140 char,
or any personal health metric. The freshness envelope (added in
commit `8a393b7`) is canonical: every tool that surfaces a
timestamped row reports `{ updatedAt, ageMs, isStale,
staleReason, windowMs }` with the same 10-min window. **Until
that commit's worker redeploy ships,
`mobile.get_*` / `handoff.get_latest` continue to return the
pre-envelope shape; `project.get_current_state` already had
the envelope and is the recommended public tool.**

| Tool | Returns | First-call recommendation |
|---|---|---|
| `project.get_current_state` | composed priority/blocker/next/agents[]/freshness | **Yes** — primary public entry-point. |
| `project.get_overview` | cross-project aggregates (mobile top priority + website pending count) | secondary cross-project view |
| `project.get_work_status` | sanitised priority/blocker/next; subset of get_current_state | redundant with get_current_state |
| `project.list_priorities` | top backlog item only | when you only want the headline backlog item |
| `project.get_operating_rules` | the 18 operating rules with id/title/body | rule lookup |

Deferred prompt/action state belongs in MCP, bridge artifacts, or a
local backlog with `id`, `owner`, `targetWorker`,
`triggerCondition`, `promptOrActionText`, `priority`, `createdAt`,
`status`, and `voidReason` when void. Public read surfaces may show
compact counts or next-action summaries only; full prompt/action
text must stay in admin-gated or local artifacts when it could
contain operational detail.

Action-ledger records extend that same model to every prompt, goal,
human step, coder step, Agent step, and AI step. The canonical
record shape is:

- `id`
- `owner`
- `targetWorkerOrPerson`
- `lane`
- `actionText`
- `triggerCondition`
- `status: pending | active | completed | blocked | void | superseded`
- `priority`
- `createdAt`
- `updatedAt`
- `evidenceSummaryOrLink`
- `voidReason` / `supersededBy` when applicable

Public MCP surfaces may expose only compact redacted summaries,
counts, stale-action indicators, and the next action per lane. Full
action detail belongs in admin-gated MCP tools, bridge artifacts, or
local backlog files until a durable `connector_action_ledger` table
ships.
| `mobile.get_lane_overview` / `mobile.get_build_overview` / `mobile.get_repo_overview` | counts/aggregates only | when ChatGPT wants a count without admin token |
| `handoff.get_latest` | composed across mobile + website, each entry tagged source | handoff feed |
| `integrations.get_overview` | per-platform exposure spec (apple_health/health_connect/whoop_oauth/polar_oauth) | integration inventory |

### Admin tools (require `x-athlete-memory-token` or `Authorization: Bearer`)

The admin token is `ATHLETE_MEMORY_API_TOKEN` set via
`wrangler secret put`. Same value is mirrored to the mobile
app under `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN` for the in-app
admin/dev surface. **ChatGPT cannot present this token via the
connector form today** — admin tools are reachable only from
the laptop / mobile-app, not from a chat session.

| Tool | Returns | Use |
|---|---|---|
| `mobile.get_control_centre` | full `/api/control_centre` snapshot incl. `operatingRules`, `lanes`, `manualSteps`, `topBacklog`, `dataSource` | local admin view |
| `mobile.get_coder_lanes` | full lane payloads for claude / codex | lane diagnostic |
| `mobile.get_work_status` | full WorkStatus payload (priority + blocker + liveStatus + repoStatus + nextAction) | full read |
| `mobile.get_build_status` | Android + iOS release rows including IDs | build diagnostic |
| `mobile.get_handoff` | full Handoff payload (manualSteps text, doNotTouch, safeToBuild) | full handoff read |
| `mobile.get_terminal_summary` | up to 50 most recent terminal entries | terminal recall |

### Write-status situation (the explicit answer)

**Today: there is no MCP v2 write tool for any agent / coder
status.** No `mobile.update_work_status`, no
`update_lane_status`, no `set_handoff`, no equivalent on the
public OR admin side. The full canonical-store write surface
lives **outside the MCP**:

| Writer | Surface | Auth | Notes |
|---|---|---|---|
| Bridge / coder script | direct Supabase write to `connector_*` tables | service role key | The intended canonical writer; runs from laptop. |
| `Supabase` MCP `execute_sql` | direct SQL against `public.connector_*` rows | Supabase MCP credentials | What Claude / Codex / Aaron use today to refresh `currentPriority`, `nextAction`, lane `lastSeenAt`. Not a chat-from-ChatGPT path. |
| Mobile app admin/dev cards | `POST /api/...` (admin token) | `x-athlete-memory-token` | Phone-side admin view; not ChatGPT-reachable. |
| Website MCP `update_work_status` / `submit_suggestion` | the WEBSITE project's tables / suggestion inbox | website-side per-user auth | Rejects No-Auth proxy writes from this Worker (`role: 'none'`). Not patchable from this repo. Use unified v2 public reads or an admin-auth v2 write tool instead. |
| Unified v2 `project.submit_priority_suggestion` | this repo's priority overlay/intake response | `x-athlete-memory-token` OR `Authorization: Bearer <ATHLETE_MEMORY_API_TOKEN>` | Shipped as an admin-gated, public-write-blocked tool. The native iPhone/TestFlight automation priority is repo-backed at rank 0; generic durable suggestion storage still needs a future table/approval workflow. |

**Implication for Codex**: if Codex needs to mark its lane
`needs_review` or post a lane summary, it does so via the
Supabase MCP `execute_sql` tool against
`public.connector_coder_lanes WHERE lane_id = 'codex'`, NOT
via an MCP v2 write tool (none exists). When ChatGPT asks
"can ChatGPT update Claude's status?" the answer is **no, not
through MCP today** — the closest path is the Supabase MCP
`execute_sql` tool if that connector is configured for
ChatGPT.

**Decision: do NOT add a public MCP write tool.** A public
write tool would (a) need rate-limiting + spam protection we
don't have today, (b) need a per-actor auth model the No-Auth
public connector cannot offer, (c) duplicate the Supabase MCP
which already does this with proper auth. The current admin
gate + Supabase MCP path is correct. If ChatGPT-from-chat
write capability is ever desired, it goes behind admin token
under `mobile.update_work_status` / `mobile.update_lane`, NOT
under the No-Auth surface.

### Recommended ChatGPT connector URL

For the live "what is Claude / Codex doing? what is the build
state? what's pending?" question:

```
https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2
```

First call: `project.get_current_state`. Read
`freshness.staleReason`. If `'fresh'`, trust the snapshot. If
`'no_writeback'` or `'env_missing'`, treat as MCP stale, fall
back to terminal / control-centre per rule 11, and continue
fixing canonical sync as a priority.

The legacy `/mcp/public` tool list (four tools) stays live until
Phase 4 of `docs/UNIFIED_MCP_PLAN.md`. The `/mcp/v2` URL is
strictly preferred for new connectors.

## Anti-rules

- **No copying website-project handoff text into this codebase
  as if it were current.** Old April handoff stays in the
  website MCP's history.
- **No claiming "agents are idle" in this codebase based on the
  website MCP's response.** That field describes a different
  set of agents.
- **No bridge-side writes to the website project's stores.**
  Stay in our `connector_*` tables.
- **No removing tools from the website MCP from inside this
  repo.** Different codebase; not ours to edit.
