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
**questions, ChatGPT must use:**

```
https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public
```

Tool calls (No Auth):

- `get_public_mcp_health` — diagnostic.
- `get_lane_overview` — lane status counts.
- `get_build_overview` — Android v + iOS Build status.
- `get_repo_overview` — branch + short HEAD.

For richer detail (lane summaries, manual step text, full
build/handoff/terminal_summary) Aaron uses curl from the laptop
or the in-app Admin/Dev surface — both go through the
admin-token-gated `/api/*` routes, NOT through any ChatGPT
connector. ChatGPT does not currently support API-key auth in
the connector form.

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
