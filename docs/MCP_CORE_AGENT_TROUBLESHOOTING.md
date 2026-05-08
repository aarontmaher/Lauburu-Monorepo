# MCP Core — Agent vs normal-chat troubleshooting

Status: troubleshooting reference. Apply when normal ChatGPT can
call Grappling Map MCP Core but Anthropic Agent / Claude Code Agent
/ Claude Managed Agents say it is "not callable."

This doc only covers the diagnostic path. Setup lives in
`docs/CHATGPT_CONNECTOR_SETUP.md`. Surface split lives in
`docs/RELEASE_AUTOMATION_SPEC.md` § 7 and the deployed worker
`cloudflare-worker/src/mcp-v2.ts`.

## Canonical URL + auth

| Field | Value |
|---|---|
| Server URL | `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2` |
| Auth | No authentication |
| Transport | Streamable HTTP (JSON-RPC 2.0 over POST; GET returns descriptor) |
| Protocol version | `2025-03-26` |
| Tool count on /mcp/v2 | 9 (well under the ~30-tool ChatGPT picker cap) |
| Future canonical URL | `https://mcp.lauburugrapplingmap.com/mcp/v2` (gated on Stage 5 of `docs/CLOUDFLARE_MIGRATION.md` — currently 404) |

The bare hostname will not work. The path `/mcp/v2` is required.

## Diagnostic ladder — run these in order

### Rung 1 — JSON-RPC ping (transport check)

```bash
URL="https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2"
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}' "$URL"
```

Expected:

```json
{"jsonrpc":"2.0","id":1,"result":{}}
```

If this fails, the issue is below MCP — DNS, TLS, the worker is
down, or the client is hitting the wrong host. Stop and fix that
first.

### Rung 2 — `project.ping` tool (server check, no upstream)

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"project.ping","arguments":{}}}' "$URL"
```

`project.ping` does NOT touch Supabase or proxy to the website MCP.
If this works but `project.get_current_state` fails, the upstream
mirror (Supabase / website) is the issue, not the MCP transport.

### Rung 3 — `project.get_current_state` (full path including upstream)

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call",
       "params":{"name":"project.get_current_state","arguments":{}}}' "$URL"
```

Expected payload includes `freshness.staleReason` (`fresh` /
`no_writeback` / `env_missing`). If `staleReason !== "fresh"`, the
data is stale but the MCP transport is healthy.

### Rung 4 — agent's tool list

Inside the agent, try to list tools. If the agent reports zero tools
or a stale tool list:

1. Recreate the connector record. Do not edit; delete and create new.
2. Start a NEW agent session / new chat. Tool lists are usually
   fetched once per session.
3. Re-run rung 2 inside the agent session.

## Why "works in chat but not Agent" — common causes

| Cause | Symptom | Fix |
|---|---|---|
| Agent uses a stale tool list cached from the original /mcp/v2 (50 tools) | Agent says "MCP not callable" or "tool not found"; ChatGPT picker shows 9 tools | Recreate connector, fresh agent session |
| Agent's MCP client requires explicit `Mcp-Session-Id` issuance | Agent fails on `initialize`; ChatGPT works | None on server today; the spec marks session ID optional. Document and watch — see § "Server side notes" |
| Agent has a stricter content-type negotiation | Agent only accepts `application/json` and the server returned `text/event-stream` | The worker negotiates by Accept header. Ensure the agent sends `Accept: application/json` — every Anthropic agent today does |
| Agent only allows tool names matching `^[a-zA-Z0-9_-]+$` (no dots) | Agent reports "invalid tool name" | This is a documented historical OpenAI custom-tool limitation; MCP namespaced names with dots ARE supported on current ChatGPT custom MCP and Anthropic Managed Agents per spec. If agent enforces no-dot names, surface tools without dot is N/A — this server only ships dot-namespaced. Fall back to JSON-RPC `ping` (rung 1) and the manual workflow below |
| Agent caps schema size or description length | Schemas validate but tools/list silently truncates | Server descriptions are ≤512 chars; schemas are minimal. Not an issue on this server today |
| Agent only allows Bearer auth, not "no auth" | Agent connector form rejects "no auth" mode | Use ChatGPT-style connector ("No authentication"). This server has no Bearer-required mode for the core surface |
| Agent enforces a specific protocol version other than `2025-03-26` | Agent rejects initialize | Server returns the standard MCP version. Newer agents should accept |

## Server side notes (informational)

- `cloudflare-worker/src/mcp-v2.ts` does not currently issue an
  `Mcp-Session-Id` header. Per the Streamable HTTP spec the server
  *may* (not must) issue one. If a future agent client requires it,
  the fix is a small worker patch — out of scope for this doc.
- `Access-Control-Expose-Headers` already includes `mcp-session-id`,
  so when the server starts issuing one the client will see it.
- `Access-Control-Allow-Headers` already includes `authorization`,
  `content-type`, `mcp-session-id`, `x-athlete-memory-token`. No
  preflight failure has been observed against ChatGPT or any
  Anthropic agent so far.
- `cache-control: no-store` on every JSON response — clients should
  not be caching tool lists.

## Recreate / enable / fresh-chat steps

1. Open the MCP connector settings UI (ChatGPT custom MCP, or the
   Agent's MCP connector list).
2. Delete any existing Grappling Map MCP record. Do not edit it in
   place.
3. Create a new record with:
   - Name: anything (cosmetic).
   - URL: `https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2`
   - Auth: No authentication.
4. Save.
5. Start a NEW chat / new agent session. The tool list refetches.
6. From inside the new session, ask the agent to call
   `project.ping` first. If that works, then ask it to call
   `project.get_current_state`. The first answers in <100ms; the
   second hits Supabase and may take 100–500ms.

## Fallback workflow if Agent cannot use the MCP

If the agent harness flatly refuses to attach to the MCP after
running through rungs 1–4 and the recreate steps, work continues
out-of-band:

1. Aaron / a coder runs the curl from rung 3 manually and pastes
   the JSON output into the agent chat.
2. The agent treats the pasted output as the source of truth for
   MCP state for that turn.
3. Aaron records a ledger action describing the agent harness +
   the failure mode so the bridge writer can capture it. Action
   ID convention: `mcp-agent-cannot-attach-<harness>-<date>`.
4. The agent must NOT claim a feature is `Built/tester-ready` or
   `shipped` based on pasted MCP state alone — the existing
   installed-device QA gate (`docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md`)
   still applies.

This fallback is intentionally clunky so it is preferred only
short-term. The /mcp/core (6-tool) surface at
`https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/core`
is also available for harnesses that want an even smaller advertised
tool list — same diagnostic ladder applies, just substitute the URL.

## When to escalate

Escalate (file a server-side patch) when ALL of the following hold:

- The agent harness is one Aaron actually uses (Claude Code Agent /
  Claude Managed Agents / a known-listed ChatGPT mode).
- The fallback is being used > 3 times in a week.
- The diagnostic ladder shows the failure occurs at rung 1 or 2
  (transport / no-upstream tool), NOT rung 3 (which would be a
  Supabase issue, not MCP).

The patch is likely one of: issue Mcp-Session-Id; relax CORS;
shrink the instructions string; ship a no-dot-named alias of
`project.ping`. None of these are urgent until the harness in
question is identified.
