# Prompt dispatcher

Local-only helper for feeding the next approved prompt into an
idle tmux lane. It is intentionally conservative and defaults to
dry-run.

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

Real loop dispatch:

```sh
npm run prompt:dispatch -- --watch --interval 10 --dispatch --bridge-snapshot
```

## Combined MCP automation

Run all MCP automation loops together:

```sh
npm run mcp:auto
```

This creates/attaches a tmux session named `mcp-auto` with:

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

Use these windows inside `mcp-auto`:

```text
Ctrl-b 0  bridge-watch
Ctrl-b 1  mcp-poll
Ctrl-b 2  prompt-dry-run / prompt-dispatch
Ctrl-b 3  bridge-verify
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

The dispatcher refuses prompts unless:

- `approved: true`
- `publicSafe: true`
- `status` is `queued`, `ready`, or `approved`
- target lane is `codex` or `claude`
- target lane is idle in `data/agent-status/lanes/coder_lanes.json`
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
- No secrets, tokens, raw logs, or private worker text in queue
  rows.
- Run dry-run first before enabling `--dispatch`.
