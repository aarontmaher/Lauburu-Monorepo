# ChatGPT connector — state contract

The shared, read-first state contract that lets ChatGPT
(Connectors), Claude (MCP), Codex, and the in-app Admin/Dev
control centre all read the same picture of "what is this
project doing right now" without any of them executing
arbitrary shell commands.

This doc is the **schema + boundary**. It does not introduce
new runtime — it names the shape every existing or planned
read-route must produce, and the rules every writer must
respect.

Companion to:
- `GRAPPLINGMAP_MCP_BRIDGE_PLAN.md` (the read-route catalogue)
- `CONNECTOR_BACKLOG_TOOLS_PLAN.md` (write-tool spec)
- `CONNECTOR_SECURITY_MODEL.md` (invariants 1–10)
- `LOCAL_BRIDGE_COMMAND_ALLOWLIST.md` (live + planned scripts)
- `LOCAL_BRIDGE_WORKFLOW_PLAN.md` (six-stage build-out)
- `ADMIN_DEV_CONTROL_CENTER_PLAN.md` (the in-app surface)
- `OWNER_AUTOMATION_LOOP_PLAN.md` (the prompt queue)
- `TERMINAL_WORKFLOW_STRATEGY.md` (terminal-side strategy)

Updated 2026-05-06.

## Goal in one paragraph

ChatGPT (running in a browser tab on Aaron's laptop or phone)
should be able to ask "what is each coder doing, what's the
next prompt, is the build green, what's blocking shipping" and
get a structured JSON answer drawn from the same source of
truth the in-app Admin/Dev page reads. Aaron should never have
to paste tmux output into ChatGPT by hand. ChatGPT should
never be able to make Aaron's laptop run an arbitrary command.

## Design principle

Read-only structured status first. Actions later, from a
fixed allowlist, with owner-tap confirmation.

## Out of scope (now and forever without explicit owner-go)

- Arbitrary shell execution by ChatGPT or any connector.
- Returning raw tokens, OAuth secrets, env values, or
  credentials in any response.
- Returning raw athlete health values (HRV ms, sleep hours,
  step counts) — only metadata about source state.
- Bypassing `LOCAL_BRIDGE_COMMAND_ALLOWLIST.md` for any
  bridge-driven action.
- Triggering Play / TestFlight / App Store production
  uploads.

## State objects

Every read-route returns one or more of these five objects.
Object names are stable; field additions are additive only;
removals require a doc-committed migration.

### 1. `work_status`

Single object. The "what's happening right now" summary.

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-06T05:50:00Z",
  "currentPriority": "Verify v17/Build 18 surfaces on Aaron + girlfriend devices.",
  "currentBlocker": "Codex is mid-IA-move; do not dispatch next build until commit lands.",
  "liveStatus": {
    "androidVersionCode": 17,
    "iosBuildNumber": "18",
    "androidPlayTrack": "internal_testing",
    "iosTestflightGroup": "Team (Expo)",
    "lastRailwayDeployAt": "2026-05-04T...Z",
    "cloudflareWorkerDeployed": false
  },
  "repoStatus": {
    "head": "ce02a35",
    "branch": "main",
    "dirtyFileCount": 2,
    "untrackedFileCount": 2,
    "lastCommitAt": "2026-05-06T16:15:23+10:00",
    "lastCommitMessage": "UX: simplify tester-facing app screens"
  },
  "nextAction": "Wait for Codex IA cleanup commit, then audit + queue Build 19/v18 dispatch as owner-tap."
}
```

Notes:
- `currentBlocker` is a string in plain English; `null` when nothing blocks.
- `liveStatus.last*` fields are advisory — derived from logs and
  may be stale. Authoritative status comes from
  `build_status`.
- No file paths, no commit author emails, no remote URLs in
  this object.

### 2. `coder_lanes`

Array of one row per coder lane. Today: `claude` and `codex`.

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-06T05:50:00Z",
  "lanes": [
    {
      "laneId": "claude",
      "status": "idle",
      "lastSeenAt": "2026-05-06T05:48:00Z",
      "currentPromptId": null,
      "lastPromptId": "CLAUDE-REVIEW-CE02-UX-CLEANUP-AND-WAIT-FOR-IA-01",
      "lastSummary": "Reviewed ce02a35; verdict PASS; waiting for Codex IA commit.",
      "lastCommit": null,
      "lastTypecheckResult": null,
      "dirtyFiles": [],
      "nextPrompt": "CLAUDE-REVIEW-IA-MOVE-NUTRITION-AND-SCHEDULE-01"
    },
    {
      "laneId": "codex",
      "status": "working",
      "lastSeenAt": "2026-05-06T05:46:00Z",
      "currentPromptId": "CODEX-IA-MOVE-NUTRITION-TO-HEALTH-AND-SCHEDULE-TO-TRAIN-01",
      "lastPromptId": "(prior)",
      "lastSummary": null,
      "lastCommit": "ce02a35",
      "lastTypecheckResult": "pass",
      "dirtyFiles": [
        "apps/mobile/src/components/NutritionTargetsEditor.tsx",
        "apps/mobile/src/components/WeeklyScheduleEditor.tsx"
      ],
      "nextPrompt": null
    }
  ]
}
```

Allowed `status` values: `idle | working | blocked | needs_user | needs_review | done`.

Field rules:
- `lastSummary` is the bridge-extracted short report from the
  coder's most recent terminal turn — capped at ~1200 chars,
  passed through the same `redactTokenLikeSubstrings()` two-pass
  redactor as `MARK_AGENT_DONE`.
- `dirtyFiles` is the result of `git status --short` filtered
  to entries owned by that lane, derived from heuristic
  ownership (path-prefix rules in
  `BACKLOG_AUTOMATION_SYSTEM.md` Lane 1/2/3 mapping).
- `nextPrompt` is the prompt-ID the lane should run next, set
  by the owner via Admin/Dev or copy-bridge — never auto-set.
- `lastCommit` is short SHA; redactor preserves labelled
  values per `b1b88ce`.

### 3. `build_status`

Single object. The release-channel truth.

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-06T05:50:00Z",
  "android": {
    "versionCode": 17,
    "appVersion": "0.1.0",
    "githubRunId": "25417977756",
    "githubStatus": "success",
    "easBuildId": "92778b10-7023-4ce6-b665-398069fa9d28",
    "easBuildUrl": "https://expo.dev/accounts/aaronmaher/projects/.../builds/92778b10-...",
    "playSubmissionId": "94cee638-97b3-4fcd-a2ba-5834b2d3be20",
    "playStatus": "submitted_completed",
    "playTrack": "internal"
  },
  "ios": {
    "buildNumber": "18",
    "appVersion": "0.1.0",
    "githubRunId": "25417981099",
    "githubStatus": "success",
    "easBuildId": "b05edd9a-0a16-42a2-9bf6-c04f95b2feea",
    "easBuildUrl": "https://expo.dev/accounts/aaronmaher/projects/.../builds/b05edd9a-...",
    "testflightSubmissionId": "badb173d-cf75-49ae-8be4-3d2e79088d4d",
    "testflightStatus": "uploaded_processing",
    "testflightGroup": "Team (Expo)"
  }
}
```

Allowed status enums:
- `githubStatus`: `queued | in_progress | success | failure | cancelled`.
- `playStatus`: `submitted_draft | submitted_completed | rolled_out | failed`.
- `testflightStatus`: `uploaded_processing | available | invalid_binary | failed`.

### 4. `handoff`

Single object. The active "what each coder should do next +
what no one should touch right now" document.

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-06T05:50:00Z",
  "latestClaudePrompt": "CLAUDE-REVIEW-CE02-UX-CLEANUP-AND-WAIT-FOR-IA-01",
  "latestCodexPrompt": "CODEX-IA-MOVE-NUTRITION-TO-HEALTH-AND-SCHEDULE-TO-TRAIN-01",
  "manualSteps": [
    "Aaron: open TestFlight on iPhone, confirm Build 18 is installable.",
    "Aaron: open Play Internal Testing on Android, confirm versionCode 17 surfaces."
  ],
  "doNotTouch": [
    "apps/mobile/app/(tabs)/health.tsx",
    "apps/mobile/app/(tabs)/train.tsx",
    "apps/mobile/app/(tabs)/settings.tsx",
    "apps/mobile/src/components/HealthActionsPanel.tsx",
    "apps/mobile/src/components/NutritionTargetsEditor.tsx",
    "apps/mobile/src/components/WeeklyScheduleEditor.tsx"
  ],
  "safeToBuild": false,
  "safeToBuildReason": "Codex IA move is mid-flight. Build after the IA commit + Claude postcommit audit."
}
```

`safeToBuild` is the one boolean that actually gates the
in-app Dispatch button; it must be set to `true` by an owner
action and reset to `false` whenever a non-`done` lane appears
in `coder_lanes`.

### 5. `terminal_summary`

Array. Most recent ~10 entries; capped, sanitized.

```jsonc
{
  "schemaVersion": 1,
  "generatedAt": "2026-05-06T05:50:00Z",
  "entries": [
    {
      "laneId": "claude",
      "at": "2026-05-06T05:45:00Z",
      "summary": "Reviewed ce02a35: PASS. No app UI edits. Waiting for IA commit.",
      "verification": "ce02a35 surfaces in git log -1; tester FAB gating intact.",
      "nextAction": "Wait for CODEX-IA-MOVE-... commit, then run CLAUDE-REVIEW-IA-MOVE-...",
      "exitCode": 0
    }
  ]
}
```

Rules:
- `summary` is the bridge-extracted text only — never the full
  pane. Pane text passes through
  `redactTokenLikeSubstrings()` and is then truncated to 1200
  chars.
- No file paths beyond what the coder explicitly named in their
  reported summary.
- No raw `git diff` output, no raw `tsc` errors with absolute
  paths, no `printenv` output.

## Local tmux bridge — staged build-out

The bridge is the producer of `coder_lanes` and
`terminal_summary`. It runs on Aaron's Mac as an opt-in
LaunchAgent + tmux read-only attach.

### Stage 1 — read-only local writer (planned)

- New script: `scripts/bridge-snapshot-lanes.sh` (planned;
  not yet in `LOCAL_BRIDGE_COMMAND_ALLOWLIST.md`).
- Inputs: none. Reads pane buffers from the existing
  `lauburu` tmux session via `tmux capture-pane -p`.
- Effect: writes `data/agent-status/<lane>.json` with
  `schemaVersion: 1` payload matching the `coder_lanes`
  row shape above.
- Sanitization: pipe through the same redactor that
  `MARK_AGENT_DONE` uses (sentinel-tag labelled commit
  values, run JWT/sk-/ghp_/AKIA/hex/base64 regexes,
  restore from sentinels — exactly the
  `b1b88ce`/`6c68726` pattern, no second implementation).
- Audit: each snapshot writes one `bridge_snapshot` audit
  event to `data/audit-events/...` with the lane ID and
  `summary.length`.
- Cadence: triggered by an owner-only LaunchAgent every
  60s, **only** while the `lauburu` session exists. No
  systemd-style always-on; if the session is killed, the
  agent exits silently.
- Failure mode: any tmux read error writes
  `status: 'idle'` and stops; never escalates to a
  "blocked" claim it cannot prove.

### Stage 2 — app/AdminDev display (extends existing)

- Admin/Dev page already reads `data/agent-status/<lane>.json`
  via `fetchAgentStatus()` (commit `5ac91e3`).
- Add a `LaneStatusSection` component that renders the array
  in the `coder_lanes` shape: lane chip + status pill +
  last-summary preview + Copy-prompt button for `nextPrompt`.
- The Copy-prompt button copies the prompt-ID and the
  full prompt body to the clipboard; it does **not** dispatch
  the prompt anywhere. The owner pastes it into the relevant
  coder's terminal.
- No command execution from the app at this stage. No "Run
  next prompt" button.

### Stage 3 — predefined actions (gated, owner-go required)

- The set of actions matches `LOCAL_BRIDGE_COMMAND_ALLOWLIST.md`
  `state: live` rows only. No new actions land in this
  stage without a doc commit.
- Each action surfaces in Admin/Dev as a button labelled
  with the canonical command ID; tapping requires:
  1. Admin email check on the device.
  2. Local Tailscale-only HTTP call to the bridge daemon.
  3. Bridge daemon revalidates the action ID against the
     allowlist file; rejects unknowns with a non-zero exit.
  4. Result writes a normal audit event and updates the
     relevant `coder_lanes` row.
- Build dispatch is **never** in this set — see allowlist
  `DISPATCH_BUILD` rejection.

## Routes / API surface

These are the proposed canonical names. Some exist on
Railway today; the Cloudflare Worker scaffold reserves the
namespace per `cloudflare-worker/src/worker.ts`.

| Route | Verb | Auth | State |
|---|---|---|---|
| `/api/athlete-memory/admin/work-status` | GET | admin token | LIVE on Railway (commit `31d9bb0`). Returns `work_status`. |
| `/api/athlete-memory/admin/agent-status` | GET | admin token | LIVE on Railway (commit `5ac91e3`). Returns `coder_lanes` rows. |
| `/api/athlete-memory/admin/build-status` | GET | admin token | **PLANNED.** Returns `build_status`. |
| `/api/athlete-memory/admin/handoff` | GET | admin token | **PLANNED.** Returns `handoff`. |
| `/api/athlete-memory/admin/handoff` | POST | admin token + owner-go | **PLANNED.** Owner-only handoff edit. |
| `/api/athlete-memory/admin/terminal-summary` | GET | admin token | **PLANNED.** Returns `terminal_summary`. |
| `/api/athlete-memory/admin/terminal-summary` | POST | admin token | **PLANNED.** Bridge-only writer. |
| `/api/athlete-memory/admin/lane-status` | POST | admin token | **PLANNED.** Bridge-only writer for one `coder_lanes` row. |
| Cloudflare Worker `/work-status` | GET | admin token | **REPO-ONLY** scaffold. Mirrors Railway when Supabase env wired. |

Auth model:
- All routes require the shared `ATHLETE_MEMORY_API_TOKEN`
  header (per `CONNECTOR_SECURITY_MODEL.md` invariant 1).
- Public / per-tester / anonymous access: **none**. Tester
  builds never see Admin/Dev, never call these routes.
- ChatGPT Connector access: scoped to read-only `GET` routes
  via the shared admin token. The token is registered with
  the Connector; it never leaves Aaron's machine.
- Claude MCP / Codex agent access: same scope as ChatGPT.
- Write routes (`POST /admin/handoff`, `POST /admin/terminal-summary`,
  `POST /admin/lane-status`) require the bridge daemon's
  signed payload — not the connector token alone.

## Security rules (consolidated)

1. **No arbitrary shell** anywhere in the stack. ChatGPT, the
   app, the bridge daemon, and the connector all reject any
   command-string parameter that does not match a fixed action
   ID in `LOCAL_BRIDGE_COMMAND_ALLOWLIST.md`.
2. **No raw secrets in any response.** Token-like substrings
   pass through `redactTokenLikeSubstrings()` two-pass
   sentinel-and-regex redactor before any write.
3. **No raw athlete health values.** Connector responses carry
   metadata only — source state, sync mode, sync timestamp,
   missingDomains list. Never the values themselves.
4. **No bridge-driven build dispatch.** Build dispatch is a
   human tap in Admin/Dev. The allowlist rejects any bridge
   attempt to call `gh workflow run`.
5. **No remote control.** The bridge daemon binds to localhost
   + Tailscale only. WAN-exposed endpoints are forbidden.
6. **No mock/stub coder summaries.** If the bridge cannot read
   the tmux pane, the lane status is `idle` — never a
   fabricated "working" or "done".
7. **Schema additions only.** Field removals from any of the
   five state objects require a doc commit and a
   `schemaVersion` bump.
8. **Owner-only writes.** All write routes require the admin
   token AND a per-write owner-go signal (Admin/Dev tap or
   bridge daemon signed payload).
9. **Audit every write.** Any state-mutating route writes a
   structured audit event. No silent state changes.
10. **Tester builds are blind.** Production app shipped to
    testers does not include the connector token, does not
    render the Admin/Dev page, does not surface lane status.

## Build order — what to land first

1. **Documented today (this doc).** No runtime change.
2. **`build_status` on Railway** — new GET route reading the
   GitHub Actions API + EAS metadata that `admin/work-status`
   already partially emits. Pure derivation; no new persistence.
3. **`handoff` GET on Railway** — file-backed (similar to
   `agent-status`). New `data/handoff.json` store. Owner edits
   via Admin/Dev (write route lands later).
4. **`terminal-summary` GET on Railway** — array of last
   ~10 entries from `data/terminal-summary/*.json`. Bridge
   becomes the writer in stage 1.
5. **Stage 1 bridge writer** — `scripts/bridge-snapshot-lanes.sh`
   added to allowlist as `state: planned` first, then
   `state: live` once the script + LaunchAgent + audit event
   are in.
6. **`lane-status` POST + `terminal-summary` POST** — bridge
   writer endpoints. Both signed by the bridge daemon.
7. **`handoff` POST** — owner-only edit endpoint.
8. **Admin/Dev `LaneStatusSection`** — UI binding for the
   read routes.
9. **Cloudflare Worker mirror** — once Supabase + worker
   secrets are wired (per `CLOUDFLARE_MIGRATION.md`), the
   Worker exposes the same five GETs reading from Supabase.
   Railway still authoritative until cutover.

## Build order — what NOT to land yet

- Connector-driven action dispatch beyond the allowlist.
- Any `POST /api/athlete-memory/admin/run-script` route.
- Any "ChatGPT can mark agent done" route — `MARK_AGENT_DONE`
  stays a local-only owner action.
- Any remote-tunnel exposure of the bridge daemon.
- Auto-promotion of provisional Grappler Readiness or
  vendor-passthrough metrics into the connector responses.
- Push-notification triggers from the connector — explicitly
  deferred until `OWNER_AUTOMATION_LOOP_PLAN.md` Phase 3
  unblocks.

## Open questions for owner-go

1. Does the bridge daemon want to live in `scripts/` as a
   long-running shell loop, or as a small Node process under
   `chat-app/src/bridge/`? (The latter gets typecheck +
   redactor reuse; the former is simpler.)
2. Should `terminal_summary` keep a 10-entry ring per lane,
   or one global ring? (Per-lane is cleaner for the in-app
   list view.)
3. Does ChatGPT see `handoff.doNotTouch` directly, or only
   `safeToBuild` + `safeToBuildReason`? (The doNotTouch list
   contains file paths, which is fine — no secrets, just
   structure.)

These do not block any of build-order steps 1–4.
