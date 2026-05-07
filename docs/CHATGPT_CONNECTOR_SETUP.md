# ChatGPT MCP connector — exact setup + troubleshooting

The cheapest, no-API-loop way to read project status from
ChatGPT. One connector, one URL, one auth choice. The richer
private surface stays on the laptop.

Companion to:
- `docs/MCP_PHONE_CONTROL_CENTRE.md` (live MCP read paths)
- `docs/CONTROL_CENTRE_MVP_SPEC.md` (in-app Admin/Dev surface)

Updated 2026-05-07.

## DO NOT USE — `mcp.lauburugrapplingmap.com`

`mcp.lauburugrapplingmap.com/mcp` exists and resolves (Cloudflare),
but it points at a **different** project — the website's
"GrapplingMap System" MCP (server name reports as
`GrapplingMap System v1.27.0`). It is **not** this codebase's
control-centre MCP and does not expose
`get_lane_overview` / `get_build_overview` / `get_repo_overview`
or any Lauburu app-development tools. If a ChatGPT chat is
configured against `mcp.lauburugrapplingmap.com/mcp` it will
appear connected but the project-status tools will be missing.

The canonical ChatGPT-facing URL is the workers.dev preview path
documented in § 1 below. If a chat shows a connector named
"GrapplingMap System" with weird tool names, it's wired to the
wrong host — re-create per § 1.

## 1. Setup — what to paste into ChatGPT

Open **ChatGPT → Settings → Connectors → Add custom connector**.

**Recommended — unified `/mcp/v2`** (covers everything below in one
connector, including the new `project.get_current_state` tool that
returns live Claude / Codex status from this codebase's Supabase):

| Field | Value |
|---|---|
| **Name** | `Lauburu MCP (unified)` |
| **MCP Server URL** | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2` |
| **Authentication** | **No Auth** |

Inside any chat that wires the unified connector, the first
useful question is: **call `project.get_current_state`** — it
returns priority / blocker / next action + per-lane status
(`claude` / `codex` with the canonical lane-status enum) + sanitised
task summary + freshness signal. Never the "all idle" the website
MCP shows when it doesn't know about this repo's bridge.

**Legacy preview connector — still live** (the original 4-tool
path; safe to keep alongside the unified one during the
documented dual-track period):

| Field | Value |
|---|---|
| **Name** | `Lauburu MCP (public preview, legacy)` |
| **MCP Server URL** | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public` |
| **Authentication** | **No Auth** |

Save. ChatGPT's connector negotiates the Streamable-HTTP MCP
transport via the `Accept` header. As of Worker version
`dc480b35` the `/mcp/public` endpoint:

- Returns `text/event-stream` (SSE-framed JSON-RPC) when the
  client sends `Accept: text/event-stream`. ChatGPT's connector
  uses this path.
- Returns plain `application/json` when the client sends a
  plain `Accept: application/json`. curl / `npm run mcp:test:public-redaction`
  use this path.

Both paths return identical `tools/list` and `tools/call`
results — they are different transports of the same JSON-RPC
response. Aaron does not need to choose; ChatGPT picks the right
one automatically.

After save, ChatGPT runs `initialize` → `tools/list` immediately
and should show four tools:

- `get_public_mcp_health` — diagnostic. Run this first in any
  new chat to confirm the connector is alive.
- `get_lane_overview` — coder lane counts by status enum.
- `get_build_overview` — Android `versionCode` + iOS
  `buildNumber` + status enums.
- `get_repo_overview` — branch + short HEAD SHA.

**Do not paste the private URL** (`/mcp`, no `/public`) into
ChatGPT. It requires a Bearer / API-key header that ChatGPT's
custom-connector form does not currently expose, and the rich
surface is intentionally kept off the public internet.

## 2. Why some chats see the connector but cannot call tools

Behaviour Aaron has observed: the connector appears in the
ChatGPT settings list, but inside a specific chat the tools
either don't appear or fail when called.

Three known causes:

1. **Tool list captured at chat start.** ChatGPT snapshots the
   connector's tool list when the chat is opened. Tools added
   to the connector AFTER the chat started won't be callable
   inside that chat. Fix: open a fresh chat. Older chats stay
   on their original snapshot.

2. **Duplicate connector entries with the same name.** If the
   connector list shows multiple "Grappling Map" / "Lauburu MCP"
   entries (from earlier setup attempts pointing at the wrong
   URL or the website MCP), ChatGPT picks one ambiguously per
   chat. Fix: §4 below — delete the duplicates, keep one.

3. **Connector marked enabled but not selected per-chat.** Some
   chats need the connector tile explicitly toggled on in the
   composer's connector picker. Without it, the tools resolve
   to "no provider for this tool name" inside that chat.

To diagnose: in any chat where the tools don't fire, ask
ChatGPT to call `get_public_mcp_health`. The response should
include `serverInfo.name = "lauburu-mcp-public-preview"`. If
ChatGPT can't find the tool, the connector isn't bound to that
chat — fix one of the three above.

## 3. The four tools — what each returns

All four are read-only, return JSON content as a `text` block
per the MCP spec. Every response includes `publicPreview: true`.

### `get_public_mcp_health`

Diagnostic. Run first.

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-07T…Z",
  "serverInfo": {
    "name": "lauburu-mcp-public-preview",
    "version": "0.1.0",
    "description": "Public-safe preview. Sanitized…"
  },
  "protocolVersion": "2025-03-26",
  "source": "supabase",          // or "repo-only" if Supabase down
  "toolNames": ["get_public_mcp_health", "get_lane_overview", …],
  "publicPreview": true
}
```

Use this to confirm:
- The connector is wired (tool callable).
- `source` flips to `"supabase"` (data path live) vs
  `"repo-only"` (Worker reachable but Supabase env missing /
  ping failed).

### `get_lane_overview`

```jsonc
{
  "totalLanes": 2,
  "byStatus": {
    "idle": 0, "working": 2, "blocked": 0,
    "needs_user": 0, "needs_review": 0, "done": 0
  },
  "lastSnapshotAt": "2026-05-06T…Z",
  "publicPreview": true
}
```

### `get_build_overview`

```jsonc
{
  "android": { "versionCode": 17, "githubStatus": "success",
               "playStatus": "submitted_completed",
               "playTrack": "internal" },
  "ios":     { "buildNumber": "18", "githubStatus": "success",
               "testflightStatus": "uploaded_processing" },
  "publicPreview": true
}
```

### `get_repo_overview`

```jsonc
{
  "branch": "main",
  "lastCommitShortSha": "8d06042",
  "publicPreview": true
}
```

## 4. Cleaning up duplicate connectors

If your ChatGPT settings show more than one Lauburu / GrapplingMap
MCP entry, delete the older ones and keep exactly one:

| Action | Reason |
|---|---|
| **DELETE** any connector pointing at `mcp.lauburugrapplingmap.com/mcp`. | This is the website project's "GrapplingMap System v1.27.0" MCP — different project, different tool names. Aaron's earlier Agent failure ("only Gmail/Drive/GitHub/Consensus available") was almost certainly because the chat saw an empty / unreachable tool list from this wrong host. |
| **DELETE** any connector pointing at the old website MCP URL (`grapplingmap-mcp` or any `*.lauburu*` URL that isn't `*.lauburu-aaron.workers.dev`). | Different project; different tool names. Confuses ChatGPT's tool resolution. |
| **DELETE** any connector pointing at the private path `/mcp` (no `/public`) configured with No Auth. | Will return 403 every call. Pure noise. |
| **DELETE** any connector with stale auth (Bearer token saved that no longer exists in ChatGPT's form, etc). | Half-configured connectors block the chat-side tool list. |
| **KEEP** exactly one connector at `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public` with **No Auth**. | This is the canonical public-safe entry. |

After cleanup, open a fresh chat and verify
`get_public_mcp_health` is listed and callable.

## 5. The cheapest workflow (no paid API loop)

Order of operations Aaron uses to keep development running from
the iPhone without burning a paid AI loop:

1. **Local tmux bridge writes status.** `npm run bridge:snapshot`
   from the laptop captures the `lauburu` (Claude) and
   `codex-lauburu` (Codex) panes, sanitises them, and (when env
   vars are present) upserts to Supabase. This is the only
   write path. It's free.

2. **Cloudflare Worker reads Supabase.** The `/api/*` routes
   serve full status to the laptop / mobile app via the admin
   token; `/mcp/public` serves sanitised aggregates to ChatGPT.
   Cloudflare's free tier covers current load.

3. **App Admin/Dev is the source of truth.** Once Phase 3 of
   `docs/CONTROL_CENTRE_MVP_SPEC.md` ships, the iPhone Control
   Centre is where Aaron reads priority / blocker / lanes /
   builds / manual steps / top backlog. No API calls beyond the
   one HTTP fetch to the Worker.

4. **ChatGPT custom connector for ad-hoc questions.** The four
   public-safe tools above answer "what's happening?" without
   screenshots or a paid API call.

5. **Termius is fallback only.** Direct tmux access is the
   escape hatch when the bridge can't snapshot a pane (e.g. the
   process isn't running). Aaron does not need Termius for
   normal status checks.

What this workflow explicitly avoids:

- Paid always-on agents.
- Polling loops against a paid AI API.
- Manual screenshot-pasting between Termius and ChatGPT.
- Pasting the admin token into a public web UI.

## 6. Private full-fidelity surface (laptop / Claude Code only)

The `/mcp` and `/api/*` routes return everything (lane summary
text, prompt IDs, manual steps with text, terminal_summary
entries) but require the admin token. Use them from:

- `npm run mcp:test:live` — integration smoke test.
- `curl` from the laptop with the token in `Authorization:
  Bearer …` or `x-athlete-memory-token: …`.
- Claude Code / Codex sessions on Aaron's Mac (the token sits
  in Mac Keychain).

Never paste these URLs into a public ChatGPT connector.

## 7. ChatGPT-shaped end-to-end verification

Updated 2026-05-08 against
`CLAUDE-CHATGPT-MCP-V2-ATTACHMENT-FIX-01`. Use this when the
ChatGPT custom connector lists tools but tool calls fail or
silently don't fire — these three curls reproduce exactly what
ChatGPT sends, so if all three return clean payloads, the
server is fine and the issue is on the client.

```sh
URL="https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2"

# 1. initialize handshake (ChatGPT sends this first; Accept advertises both transports)
curl -sS -X POST -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"chatgpt-test","version":"0.1"}}}' \
  "$URL"
# Expected: text/event-stream frame containing
#   serverInfo.name = "lauburu-mcp-unified"
#   serverInfo.version = "0.1.0"
#   protocolVersion = "2025-03-26"
#   capabilities.tools.listChanged = false

# 2. tools/list (ChatGPT calls this immediately after initialize)
curl -sS -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' "$URL" \
  | sed 's/^event: message$//;s/^data: //' \
  | jq '.result.tools | {count: length, namespaces: [.[].name | split(".")[0]] | unique}'
# Expected: { "count": 43, "namespaces": ["handoff","integrations","mobile","project","update_work_status","website"] }

# 3. tools/call public-safe (No Auth)
curl -sS -X POST -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"project.get_current_state"}}' \
  "$URL" \
  | sed 's/^event: message$//;s/^data: //' \
  | jq '.result.content[0].text | fromjson | {freshness: .freshness.staleReason, agents: [.agents[] | {id, status}]}'
# Expected: { "freshness": "fresh", "agents": [{ "id": "claude", "status": ... }, { "id": "codex", "status": ... }] }
```

If all three return as expected, the **server invocation path
works end-to-end**. ChatGPT-side failures are then almost
certainly one of the three causes in § 2 plus the new § 8 tool-
count cap below.

The Worker also exposes a cheap route probe for connector setup:

```sh
curl -sS https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2/health | jq
```

Expected: `ok: true`, `serverInfo.name = "lauburu-mcp-unified"`,
`transport = "streamable-http"`, and `requiredTools` containing
`project.get_current_state`, `project.get_operating_rules`,
`integrations.get_overview`, and `handoff.get_latest`.

### 7.1 Reference URLs

| URL | What it is | Use? |
|---|---|---|
| `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2` | THIS codebase's unified MCP — 43 tools (project.* / mobile.* / integrations.* / handoff.* / website.* proxied) | **YES — the canonical ChatGPT URL** |
| `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public` | THIS codebase's legacy preview — 4 tools | yes, additive; safe to keep alongside |
| `https://mcp.lauburugrapplingmap.com/mcp` | website project's MCP (`GrapplingMap System v1.27.0`) | only if you want website-project state directly; tool overlap with `website.*` proxy on /mcp/v2 |
| `https://mcp.lauburugrapplingmap.com/mcp/v2` | **does NOT exist — returns 404** | NO — common mistake; the custom domain only hosts `/mcp` (no `/v2` path) |

The `/mcp/v2` path lives ONLY on the workers.dev URL. The
`mcp.lauburugrapplingmap.com` custom domain points at the
website project's separate codebase and does not host `/mcp/v2`.

## 8. Tool-count cap on the ChatGPT custom-connector form

ChatGPT's custom-MCP connector currently surfaces **at most ~30
tools** per connector inside a chat. The unified `/mcp/v2`
exposes **43 tools** (project + mobile + integrations + handoff
+ website proxy). When the chat's selected tool list is over
the cap, ChatGPT silently drops the tail — the connector still
appears connected and the model "sees" tool names in some
contexts, but tool invocation routes to "tool not found" or
silently no-ops.

### Working around the cap

Two options, in order of preference:

1. **One connector, prompt-targeted invocations.** Keep the
   single `/mcp/v2` connector. In the chat's first message,
   instruct ChatGPT explicitly which tool to call by name —
   "Use the `project.get_current_state` tool from Lauburu MCP".
   ChatGPT then resolves the call by tool name regardless of
   how many tools are in the picker. This works for every tool
   in the 43-tool list.

2. **Two connectors, scoped surfaces.** Add the legacy
   `/mcp/public` connector (4 tools) alongside `/mcp/v2`.
   Beginner reads stay on `/mcp/public`; advanced reads
   (`project.get_current_state`, lane status, build status,
   handoff) on `/mcp/v2`. Distinct names so ChatGPT picks
   cleanly:
   - `Lauburu MCP (unified, /mcp/v2)`
   - `Lauburu MCP (preview, 4 tools)`

### Diagnosing the cap symptom

The signature of this failure mode:

- ChatGPT lists the connector in settings and the connector is
  toggled on for the chat.
- A `tools/list` curl from terminal (§ 7) returns 43 tools.
- Inside ChatGPT, asking "what tools do you see from
  Lauburu?" returns a partial list (often the first ~28-30).
- Asking ChatGPT to call a tool **by name** that's beyond the
  cap fails with "I don't have access to that tool" or silent
  no-op.
- Asking ChatGPT to call a tool **by name** that's within the
  cap works.

### Future fix path

If the cap proves persistent, the right code change is to split
`/mcp/v2` into two endpoints:

- `/mcp/v2/lauburu` — project / mobile / integrations / handoff
  (≤18 tools)
- `/mcp/v2/website` — the proxied `website.*` set (≤25 tools)

Each becomes its own ChatGPT connector with a tool count well
under the cap. This is a Worker code change behind a separate
FS-XXX candidate; not done in this commit.

## 9. Quick verification (terminal one-liners)

```sh
# Public-safe path:
curl -sS https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public | jq

# tools/list (no auth):
curl -sS -X POST -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public \
  | jq '.result.tools[].name'

# Should print exactly:
# "get_public_mcp_health"
# "get_lane_overview"
# "get_build_overview"
# "get_repo_overview"

# Diagnostic call:
curl -sS -X POST -H "content-type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_public_mcp_health"}}' \
  https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public \
  | jq '.result.content[0].text | fromjson | {source, version: .serverInfo.version}'

# Expected: { "source": "supabase", "version": "0.1.0" }
```

If the tools list comes back empty or `get_public_mcp_health`
errors, the Worker has been redeployed without the public
handler — re-run the deploy step in `docs/MCP_PHONE_CONTROL_CENTRE.md`.
