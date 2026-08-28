# Prompt dispatcher

Local-only helper for feeding the next approved prompt into an
idle tmux lane. It is intentionally conservative and defaults to
dry-run.

The dispatcher does not call MCP tools directly. It reads the
local bridge/action-ledger files produced by `mcp-auto`:

```text
data/agent-status/lanes/coder_lanes.json
data/action-ledger/pending_actions.json
data/prompt-dispatcher/queue.json
```

If `coder_lanes.json` is missing or stale, dispatch is blocked
with:

```text
run npm run terminal:auto -- --attach mcp-auto first
```

## Run

```sh
npm run prompt:dispatch -- --once
```

Real dispatch requires an explicit flag:

```sh
npm run prompt:dispatch -- --once --dispatch --bridge-snapshot
```

Loop mode:

```sh
npm run prompt:dispatch -- --watch --interval 10
```

Generate/update the local queue from the action ledger before
selecting. This is the default:

```sh
npm run prompt:dispatch -- --once --generate-queue
```

Use a prebuilt queue without regenerating:

```sh
npm run prompt:dispatch -- --once --no-generate-queue
```

Real loop dispatch:

```sh
npm run prompt:dispatch -- --watch --interval 10 --dispatch --bridge-snapshot
```

## Combined MCP automation

Run all MCP automation loops together:

```sh
npm run mcp:auto
```

This creates/attaches a tmux session named `mcp-auto` with one
tiled window:

- `bridge-watch`
- `mcp-poll`
- `prompt-dry-run`
- `bridge-verify`

The combined command defaults to prompt dry-run. Real prompt
dispatch must be explicitly enabled:

```sh
npm run mcp:auto -- --dispatch
```

Attach later:

```sh
tmux attach -t mcp-auto
```

## One-command terminal startup

Use this for Termius startup or a local Terminal tab:

```sh
cd /Users/aaronmaher/LauburuGrapplingMap-mobile && npm run terminal:auto
```

It ensures these sessions exist:

- `mcp-auto` — all MCP automation loops
- `codex-lauburu` — Codex / Claude / Agent workspace
- `lauburu` — standalone Claude Code

By default it attaches to `codex-lauburu`. Switch windows:

```text
Ctrl-b 0  Codex
Ctrl-b 1  Claude Code
Ctrl-b 2  Agent
Ctrl-b 6  Shell
```

Attach somewhere else:

```sh
npm run terminal:auto -- --attach mcp-auto
npm run terminal:auto -- --attach lauburu
```

Use these panes inside `mcp-auto`:

```text
top-left      bridge-watch
top-right     mcp-poll
bottom-left   prompt-dry-run / prompt-dispatch
bottom-right  bridge-verify
```

Disable the periodic verifier if you only want the live loops:

```sh
npm run mcp:auto -- --no-verify
```

Default tmux targets:

| Lane | Target |
|---|---|
| `codex` | `codex-lauburu:0.0` |
| `claude` | `lauburu:0.0` |

Override when needed:

```sh
npm run prompt:dispatch -- --once --codex-target codex-lauburu:3.0
```

## Queue

Default queue path:

```text
data/prompt-dispatcher/queue.json
```

Shape:

```json
{
  "prompts": [
    {
      "id": "repo-only-next-safe-bundle",
      "targetLane": "codex",
      "priority": "P1",
      "status": "queued",
      "approved": true,
      "publicSafe": true,
      "createdAt": "2026-05-10T00:00:00Z",
      "promptText": "Lane: Codex — repo-only safe bundle.\nNo EAS/TestFlight/Play upload/release actions."
    }
  ]
}
```

The generator reads:

```text
data/action-ledger/pending_actions.json
```

Manual/unsafe actions, such as uploading the v21 AAB to Play
Internal, are written as non-dispatchable queue rows. They can
show as the top blocker/next action, but the dispatcher will not
paste them into a lane.

Dispatched rows are marked locally with `status: "dispatched"`,
`dispatchedAt`, and `consumedAt`; repeated runs will not send
the same prompt again.

The dispatcher refuses prompts unless:

- `approved: true`
- `publicSafe: true`
- `status` is `queued`, `ready`, or `approved`
- target lane is `codex` or `claude`
- target lane may also be `agent` when an Agent tmux pane exists
- target lane is idle in `data/agent-status/lanes/coder_lanes.json`
- `coder_lanes.json` is fresh from the local bridge snapshot
- prompt text does not contain positive build/upload/release
  instructions

Lines that explicitly prohibit unsafe actions, such as
`No EAS/TestFlight/Play upload/release actions.`, are allowed.

## Logs

Every pass writes a local JSONL audit event:

```text
data/prompt-dispatcher/dispatch-log.jsonl
```

`data/prompt-dispatcher/` is gitignored because it is operator
state and may contain prompt text.

## Anti-rules

- No automatic builds.
- No Play/TestFlight/App Store uploads.
- No production releases.
- v21 Play Internal upload, Samsung install, versionCode 21
  confirmation, and 10-screenshot Health Connect QA remain manual
  installed-device workflow steps. Automation may surface them,
  never perform or mark them complete.
- No secrets, tokens, raw logs, or private worker text in queue
  rows.
- Run dry-run first before enabling `--dispatch`.
