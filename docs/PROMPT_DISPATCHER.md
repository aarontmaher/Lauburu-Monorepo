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
