# Local bridge workflow — staged plan

How the in-app Admin/Dev workflow gets from "remote control for
GitHub Actions + clipboard prompt bridge" (today) to "local Mac /
tmux bridge that the phone can poke from across the room" (later)
without ever shipping a raw terminal or arbitrary shell. Every
stage is itself a useful product; later stages are gated and
deferred until the prior stage is stable.

Companion to `TERMINAL_WORKFLOW_STRATEGY.md` (security boundary)
and `NO_API_OWNER_WORKFLOW.md` (deterministic-only, no paid LLM).

Updated 2026-05-05.

## Why staged

Each stage closes one specific friction point in Aaron's current
laptop loop. Skipping ahead means importing risk (security, store
review, runaway LLM cost) before the prior stage is paying its way.
"Build the boring thing first" is the rule.

## Stage 1 — Admin/Dev control centre (LIVE on `main`)

Status: shipped to repo, awaiting next paired build for tester
visibility.

Closes: "where are we up to?" — one-screen view of priority,
blocker, next action, Android status, iOS status. Compact chips,
no walls of text, owner-gated.

Done when: Admin/Dev surfaces the Now / Android / iOS / OTA cards
above all other content. Confirmed in this batch.

## Stage 2 — Safe GitHub Actions workflow buttons (LIVE)

Status: shipped via the signed backend dispatch endpoint
(`/api/athlete-memory/admin/workflows/:id/dispatch`).

Closes: "I have to walk to the laptop to start a build". Each
button posts to a fixed allowlist of workflows; arbitrary
parameters are rejected; confirm Alert names the cost (EAS
credits, Play DRAFT release).

Done when: Aaron can dispatch typecheck / release audit / backend
smoke from the phone without opening a terminal. Build dispatch
buttons remain gated by the EAS build cost control rule below.
Confirmed.

EAS build cost control: coders may mark a change
`Implementation-complete, awaiting Agent functional confirmation`
when code is committed, typecheck/tests pass, no obvious blockers
remain, and expected behaviour is clearly described. They must not
request, trigger, or recommend a new EAS/tester build yet. A build
is allowed only after Agent performs a functional audit, Agent
confirms the change is worthwhile to test on-device, the change is
bundled with other meaningful mobile changes where possible,
typecheck/tests pass, and Aaron explicitly approves the EAS build.
Default is no EAS build, no tester build, no "quick build to check",
no build for docs/backend/MCP-only changes, and no build for tiny
copy/UI tweaks unless bundled.
Generated prompts must include: "Do not run EAS builds unless Agent has confirmed a worthwhile on-device change and Aaron approves."

Status wording: `Implementation-complete, awaiting Agent functional
confirmation` → `Agent-confirmed, ready for Aaron build approval` →
`Aaron-approved for EAS build` → `Built/tester-ready`. Do not call
mobile work `fully complete` until Aaron has tested or approved it.

## Stage 3 — Template prompt bridge (LIVE)

Status: shipped — `apps/mobile/src/services/prompt-templates.ts`
+ `apps/mobile/src/store/owner-workflow-store.ts`.

Closes: "I want to ask Claude Code to do X but I'm on the phone."
Five deterministic templates (Claude Code / Claude Chrome /
ChatGPT status / Codex / terminal check) generated from a
structured `OwnerWorkflowContext`. No paid LLM. Long-press to
copy → paste into the runner of choice.

Done when: each template renders from the context and copies
clean. Confirmed.

## Stage 4 — Backlog bridge (LIVE)

Status: shipped — `apps/mobile/src/store/owner-backlog-store.ts`
(local-only) + Quick capture form in Admin/Dev. Repo-side
canonical backlog at `docs/APP_DEVELOPMENTS.md`.

Closes: "I keep brain-dumping into Apple Notes and forgetting".
Owner taps Quick capture → fills title / details / type /
platform / priority / status → saved locally. Standing top-5
mirrors APP_DEVELOPMENTS.md.

Future extension (Stage 4.5, deferred): backend route
`/admin/backlog` that accepts the same shape so captures sync
across Aaron's devices. The local store's contract already
matches what the route will accept — no migration when wired.

Done when: capture stores items locally, lists them, allows ship
/ delete. Confirmed.

## Stage 5 — Local Mac / tmux bridge (Stage 1 LIVE; Stages 2–5 PLANNED)

Status: **Stage 1 producer LIVE** —
`scripts/bridge-snapshot-lanes.sh` reads pane content for the
`lauburu` and `codex-lauburu` tmux sessions and writes
sanitised CoderLanes JSON to
`data/agent-status/lanes/`. No daemon, no network, no
side-effecting actions yet — just read-only snapshots.
See `docs/LOCAL_BRIDGE_COMMAND_ALLOWLIST.md` →
`BRIDGE_SNAPSHOT_LANES`.

Run it manually:

```sh
./scripts/bridge-snapshot-lanes.sh
# wrote /Users/.../data/agent-status/lanes/coder_lanes.json
#   lane=claude  status=working dirty=N currentPrompt=… lastPrompt=…
#   lane=codex   status=working dirty=N currentPrompt=… lastPrompt=…
```

Stages 2–5 below remain planned — the daemon, push to the
backend, the Tailscale URL, and the predefined action set are
all gated by the eight hard rules below.

Closes: "I want the phone to drop a single approved instruction
into the laptop's tmux session that already has Claude Code
running, instead of switching apps to copy-paste."

Shape (when built):

- **Bridge daemon on the Mac** — small Node service in
  `tools/local-bridge/` (separate from `chat-app/` to keep
  blast radius local). Runs in the same tmux Aaron uses for
  Claude Code. Listens on **localhost only** (127.0.0.1) by
  default; reachable from the phone over **Tailscale** only,
  never the public internet.
- **Phone calls a Tailscale-only URL** with a short-lived
  token. The Tailscale ACL restricts the URL to Aaron's two
  devices.
- **Endpoints accept only predefined actions** from a fixed
  allowlist:
  - `tmux send-keys` of one of N known prompts (the Prompt
    bridge templates from Stage 3).
  - `git status` / `git log -5` / `npx tsc --noEmit` —
    read-only diagnostics.
  - Nothing else. No raw `command` field.
- **No secrets in the request body.** The phone sends the
  action name + the chosen template body (which is itself
  secret-free by construction, see `AI_PROVIDER_STRATEGY.md`
  logging policy).
- **Confirmation before any side-effecting action.** The
  bridge replies with a "would do X" preview; the phone shows
  it; Aaron taps Confirm; the bridge then executes.
- **Audit log on the Mac.** Every accepted action appended to
  `~/.lauburu-bridge/audit.log` with timestamp + action name.

Hard rules for Stage 5 (must all hold or it doesn't ship):

1. Tailscale (or local Wi-Fi via mDNS, never WAN) — never a
   public URL.
2. Owner-only auth via biometrics on the phone AND a token the
   bridge mints at startup printed once into Aaron's tmux.
3. Predefined actions only. No arbitrary shell. No `eval`.
4. No secrets passed through the bridge request. The bridge
   reads its own env when it needs them.
5. Confirmation step for every side-effecting action.
6. Audit log persisted on the Mac.
7. Bridge daemon defaults to OFF; explicit `lauburu-bridge
   start` / `stop` commands.
8. Documented kill-switch from a separate device (laptop login
   that revokes the bridge token).

Until all eight hold, the bridge stays a doc.

## Stage 6 — Paid AI integration (DEFERRED)

Status: design only — `AI_PROVIDER_STRATEGY.md` +
`AI_MONETISATION_AND_USAGE_STRATEGY.md`. No code.

Closes: "summarise this status block for me", "draft the next
prompt automatically", "triage feedback by ladder rule X".

Gated on:

1. All triggers in `AI_PROVIDER_STRATEGY.md` met.
2. All triggers in `AI_MONETISATION_AND_USAGE_STRATEGY.md` met.
3. Stage 5 is either shipped OR explicitly deferred. The local
   bridge gives Aaron a free fallback for most "summarise X"
   needs (he can drop the prompt into the laptop's existing
   ChatGPT subscription via the Prompt bridge); paid API only
   makes sense once that path proves insufficient.

When paid AI lands, it does NOT replace any earlier stage. Free
tier keeps the Stage 1–4 workflow exactly as-is.

## Anti-rules — do not skip

- **Do not ship Stage 5 before Stage 4 is in real use.** Local
  bridges look exciting and end up wallpapering over a
  half-finished foundation. If Quick capture and the Prompt
  bridge aren't actually being used in Aaron's daily loop, a
  bridge daemon won't fix that — it'll just add risk.
- **Do not let Stage 5 grow a "raw command" escape hatch.** As
  soon as the daemon accepts arbitrary shell, every protection
  in `TERMINAL_WORKFLOW_STRATEGY.md` collapses. The action
  allowlist is load-bearing.
- **Do not enable Stage 6 to make Stage 4 "smarter".** Stage 4
  is deterministic on purpose. If Stage 4 outputs feel dumb,
  the fix is a better template, not an LLM.
- **Do not skip the audit log on Stage 5.** A bridge without an
  audit log is indistinguishable from malware on the Mac if
  the phone is ever stolen.

## Confirmation: what's true today

- Admin/Dev control centre: ✓ live on `main`, awaits paired build.
- Safe GitHub Actions buttons: ✓ live (signed dispatch endpoint).
- Template prompt bridge: ✓ live on `main`. Includes Copy Claude
  Code prompt / Copy Claude Chrome prompt / Copy ChatGPT status
  prompt / Copy Codex prompt / Copy current status block / Copy
  terminal check prompt. Plus Open Termius shortcut + copyable
  tmux-attach instructions.
- Backlog bridge: ✓ live local-only on `main`. Backend sync
  deferred to a separate batch.
- Local Mac / tmux bridge: not started. Planned per this doc.
- Paid AI integration: not started. Gated.

## Next concrete step (no Stage-5 work yet)

1. Aaron's Play Console listing pass + `releaseStatus` flip
   (`docs/PLAY_SUBMIT_SETUP.md` §6).
2. Next paired build (Android v14 + iOS Build 15) so Stage 1–4
   are visible on tester devices.
3. **Use Stage 4 (Quick capture) for two weeks** before
   considering Stage 5. If capture sticks, plan the bridge.
   If it doesn't, the bridge wouldn't have been used either.
