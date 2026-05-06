# ChatGPT MCP connector — exact setup + troubleshooting

The cheapest, no-API-loop way to read project status from
ChatGPT. One connector, one URL, one auth choice. The richer
private surface stays on the laptop.

Companion to:
- `docs/MCP_PHONE_CONTROL_CENTRE.md` (live MCP read paths)
- `docs/CONTROL_CENTRE_MVP_SPEC.md` (in-app Admin/Dev surface)

Updated 2026-05-07.

## 1. Setup — what to paste into ChatGPT

Open **ChatGPT → Settings → Connectors → Add custom connector**.
Use exactly these values:

| Field | Value |
|---|---|
| **Name** | `Lauburu MCP (public preview)` |
| **MCP Server URL** | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/public` |
| **Authentication** | **No Auth** |

Save. ChatGPT runs `initialize` → `tools/list` immediately and
should show four tools:

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

## 7. Quick verification

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
