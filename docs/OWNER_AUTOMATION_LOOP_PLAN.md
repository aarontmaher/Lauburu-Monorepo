# Owner-only automation loop — design plan

What "Aaron leaves the house, Claude / Codex keep working safely
through a queue, app pings him on done / blocked / needs-review"
looks like. Phase 2 of the owner-only coder-status surface
(Phase 1 = `mark-agent-done.sh` + `/admin/agent-status` route +
Admin/Dev `Coder status` card, already on `main`).

Companion to `BACKLOG_AUTOMATION_SYSTEM.md` (three-lane risk
model), `LOCAL_BRIDGE_WORKFLOW_PLAN.md` (SSH-bridge gates),
`CONNECTOR_BACKLOG_TOOLS_PLAN.md` (write-tool gates),
`CONNECTOR_SECURITY_MODEL.md` (invariants).

Updated 2026-05-06.

## Hard rules (carried forward)

1. **Owner-only.** Every queue item, every push, every status
   read is gated by the same email allowlist that already
   governs Admin/Dev (see `app/admin-dev.tsx` `ADMIN_EMAILS`).
   Local 7-tap dev unlock alone is NOT enough to participate in
   this loop — it grants read-only Admin/Dev diagnostics, but
   never queue control.
2. **No arbitrary shell execution.** The queue carries
   pre-defined PROMPT-IDs and parameter sets — never raw
   command strings. Same allowlist pattern as the GitHub
   Actions workflow dispatcher already uses.
3. **Termius / tmux only as the execution surface.** The app
   never SSHes anywhere. The runner (Claude Code / Codex)
   already runs in Aaron's tmux session. This loop ADDS a
   queue file the runner reads + a status file the runner
   writes; it does not change WHERE the runner runs.
4. **Stop conditions before max loop count.** `tsc` failures,
   workflow-dispatch failures, doc-edit collisions on a pinned
   section, or a planned action that falls into Lane 3 (per
   `BACKLOG_AUTOMATION_SYSTEM.md`) all halt the loop. Loop
   count is the last-resort cap, not the primary brake.
5. **Push notifications never carry secret content.** A push
   surfaces only the agent + status + short title; the body
   stays in the admin-token-gated agent-status route, fetched
   on tap. Same pattern as standard "1 new message" pushes.

## Phase 2 — owner-only prompt queue

Adds a small structured file at `data/agent-queue/<agent>.json`
that the runner reads on startup and pops one prompt at a time:

```jsonc
{
  "agent": "claude",
  "ownerEmail": "aaron.t.maher@gmail.com",
  "queue": [
    {
      "id": "BACKEND-AUDIT-ROLLUP-AND-WORKER-SUPABASE-WIRE-01",
      "promptId": "BACKEND-AUDIT-ROLLUP-AND-WORKER-SUPABASE-WIRE-01",
      "title": "Backend audit roll-up routes",
      "lane": "lane2",
      "maxRetries": 1,
      "stopOn": ["tsc_error", "workflow_dispatch_failed"],
      "addedAt": "2026-05-06T08:30:00Z"
    }
  ],
  "maxLoopCount": 5,
  "updatedAt": "2026-05-06T08:30:00Z"
}
```

Constraints:

- `id` + `promptId` are pulled from `BACKLOG_AUTOMATION_SYSTEM.md`
  Lane 1 (safe autopilot) or Lane 2 (build autopilot with
  confirmation). Lane 3 prompts (production releases / paid AI
  / Supabase pushes / etc.) are REJECTED at write time —
  validation lives in a new `scripts/queue-add.sh` helper that
  refuses to add a Lane-3-shaped prompt without an
  `--owner-approved` flag.
- `maxLoopCount` defaults to 5; runner stops after 5 successful
  prompt completions OR the queue empties OR a stop-condition
  fires.
- `stopOn` is a per-prompt override of the standard stop
  conditions from `BACKLOG_AUTOMATION_SYSTEM.md` § Stop
  conditions.
- `ownerEmail` is set from a fixed allowlist match — the file
  itself can be written by anyone with shell access on the
  Mac, but the runner ignores it if `ownerEmail` doesn't match
  one of the allowlisted emails. Belt-and-braces.

## Phase 3 — push notifications on DONE / BLOCKED / NEEDS REVIEW

Adds `expo-notifications` + a per-device push token registry on
the backend. When `mark-agent-done.sh` writes a new agent-status
file, it ALSO POSTs to `POST /api/athlete-memory/admin/push-tokens/notify`
(admin-token-gated) with:

```json
{
  "agent": "claude",
  "status": "done",
  "title": "Claude finished: Backend audit roll-up routes",
  "body": "tsc clean. Next: deploy preview Worker."
}
```

Backend looks up registered owner-email push tokens (registered
via a new `POST /admin/push-tokens/register` route on app
launch when the user is on the email allowlist) and forwards to
the Expo push API. Token registry is per-device; tokens that
return 410 Gone on send are auto-removed.

Push surface is intentionally minimal:

- Title: `{agent} {status}: {task}` (≤120 chars).
- Body: `{summary first sentence}` (≤200 chars, redactor
  applied as in `redactTokenLikeSubstrings()`).
- Tap action: open `/admin-dev` (already a Stack route) →
  scroll to `Coder status` section.

Out of Phase 3:

- Read receipts on push (Apple/Google APNs/FCM both unreliable
  about delivery confirmation; not building this today).
- Per-status sound differentiation (rest of app stays silent;
  this is a single notification per coder-finish event).

## Phase 4 — runner integration

The runner (Claude Code / Codex) optionally reads
`data/agent-queue/<agent>.json` at boot. If a queue exists and
the top prompt's `lane` is `lane1` or `lane2`, the runner
proceeds with the next prompt automatically. After each prompt:

1. Runner writes the result via `mark-agent-done.sh`.
2. Backend's `mark-agent-done.sh` (or a sibling
   `mark-agent-done-and-notify.sh`) POSTs the push.
3. Aaron's phone vibrates. He taps. Admin/Dev opens with the
   Coder status card already showing the latest result.
4. If the prompt failed any stop condition, the runner halts
   and waits for human input — does NOT pop the next queued
   prompt.

Runner participation is OPT-IN per session. The loop is paused
by default; Aaron explicitly types "loop go" to start it.

## Stop conditions (carried forward + added)

Per `BACKLOG_AUTOMATION_SYSTEM.md` plus:

1. `tsc --noEmit` failure after the runner's edits.
2. Any GitHub Actions workflow returning non-2xx on dispatch.
3. Doc edit collides with a frontmatter `pin: true` section.
4. Planned action falls into Lane 3 without explicit owner
   approval.
5. Test (when present) fails in CI.
6. Detected write that would leak a secret per
   `CONNECTOR_SECURITY_MODEL.md`.
7. **NEW**: queue file's `ownerEmail` doesn't match the
   allowlist.
8. **NEW**: push-token route returns 401/403 (auth drift) —
   halt before the next prompt.
9. **NEW**: `maxLoopCount` reached.

## Out of scope for this doc

- Web UI for the queue (Aaron edits the JSON via Termius / nano
  for now).
- Per-prompt time budgets (single-prompt timeout is a runner
  concern, not a queue concern).
- Cross-runner orchestration (Claude and Codex don't coordinate
  — each has its own queue file).
- Streaming push notifications during a long-running prompt
  (only fires on terminal status: done / blocked / needs_review).

## Files this plan adds (Phase 2 + 3, not yet implemented)

- `data/agent-queue/<agent>.json` (gitignored, like agent-status).
- `scripts/queue-add.sh` (owner-only validation).
- `scripts/queue-pop.sh` (runner-side; emits next-prompt JSON).
- `chat-app/src/server/routes/athleteMemory.ts`:
  - `POST /admin/push-tokens/register`
  - `POST /admin/push-tokens/notify`
  - `GET /admin/agent-queue` (read-only, owner-token gated).
- `apps/mobile`:
  - `expo-notifications` dependency + per-launch token register
    on owner-email allowlist match.
  - `apps/mobile/src/services/push-token-client.ts`.
  - Admin/Dev surface for the queue (read/skip; no add — that's
    Termius-side).

## What's NOT being implemented this batch

This doc is design-only. Ship Phase 2 + Phase 3 in a future
explicit-go batch — they need a coherent same-session
implementation pass with `expo-notifications` install + native
rebuild test, not a partial bolt-on tonight.
