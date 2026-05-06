# Local bridge command allowlist

The exhaustive list of commands the owner-only local bridge will
ever execute. Every script under `scripts/` validates its
positional + flag inputs against the relevant section of this
file; anything not listed gets rejected without execution. No
arbitrary shell, no free-text input that reaches `eval` / `exec`.

Companion to:
- `LOCAL_BRIDGE_WORKFLOW_PLAN.md` (six-stage build-out, eight
  hard rules)
- `BACKLOG_AUTOMATION_SYSTEM.md` (three-lane risk model)
- `OWNER_AUTOMATION_LOOP_PLAN.md` (Phase 2 prompt-queue spec)
- `CONNECTOR_BACKLOG_TOOLS_PLAN.md` (write-tool gates)
- `CONNECTOR_SECURITY_MODEL.md` (invariants 1–10)

Updated 2026-05-06.

## Why this exists

Aaron will eventually run a small daemon on his Mac that listens
for owner-only commands (over Tailscale, never WAN) so the
mobile app can ask "rebuild Android now" or "mark Codex done"
without pasting commands into Termius by hand. That bridge MUST
NOT accept arbitrary command strings — every action is a fixed
ID with type-checked parameters, and this doc is the single
source of truth for what's allowed.

If a command appears in this doc with `state: planned`, the
runtime stub refuses it. Only `state: live` actions are
accepted. New entries require a doc commit; the runtime won't
synthesise commands from elsewhere.

## Naming convention

Each row carries:
- `id` — the canonical command identifier (UPPER_SNAKE).
- `script` — the `.sh` file under `scripts/` that owns it.
- `state` — `live` / `planned` / `deferred`.
- `lane` — Lane 1 / Lane 2 / Lane 3 per
  `BACKLOG_AUTOMATION_SYSTEM.md`.
- `inputs` — exact parameter names + types + allowed values.
- `effect` — what the script writes / dispatches / observes.
- `audit` — whether the action records itself in
  `data/agent-status/<agent>.json` or
  `data/audit-events/...`.

## Live commands

### `MARK_AGENT_DONE`

- **script**: `scripts/mark-agent-done.sh`
- **state**: live (commit `5ac91e3`)
- **lane**: Lane 1 (safe autopilot — owner-only writes a JSON
  status row).
- **inputs**:
  - `agent` enum: `claude` | `codex` | `claude-code-guide` |
    `other`
  - `status` enum: `done` | `blocked` | `needs_review` |
    `in_progress`
  - `task` string ≤ 240 chars
  - `summary` string ≤ 1200 chars
  - `verification` string ≤ 240 chars (default `n/a`)
  - `nextAction` string ≤ 240 chars (default `n/a`)
- **effect**: writes `data/agent-status/<agent>.json` with the
  validated payload + `updatedAt` ISO timestamp.
- **audit**: the file IS the audit row; the
  `/api/athlete-memory/admin/agent-status` route reads it
  through `redactTokenLikeSubstrings()`.
- **rejection criteria**: anything outside the agent + status
  enum exits with `::error::` and writes nothing.

### `START_DEV`

- **script**: `scripts/start-dev.sh`
- **state**: live (commit `c430c5e`)
- **lane**: Lane 1.
- **inputs**: none. Reads `LAUBURU_ROOT` env (default
  `~/LauburuGrapplingMap-mobile`).
- **effect**: idempotent tmux session named `lauburu` with three
  windows (mobile / chat-app / logs). If session exists,
  attaches.
- **audit**: none — diagnostic only.

### `RESTART_DEV`

- **script**: `scripts/restart-dev.sh`
- **state**: live (commit `c430c5e`)
- **lane**: Lane 1.
- **inputs**: none.
- **effect**: kills the `lauburu` tmux session if running, then
  re-runs `START_DEV`.
- **audit**: none.

### `TAIL_LOGS`

- **script**: `scripts/tail-logs.sh`
- **state**: live (commit `c430c5e`)
- **lane**: Lane 1.
- **inputs**:
  - `window` enum: `mobile` | `chat-app` | `logs` (default
    `mobile`).
- **effect**: read-only attach (`tmux attach -r`) to the
  specified window.
- **audit**: none.

### `BRIDGE_SNAPSHOT_LANES`

- **script**: `scripts/bridge-snapshot-lanes.sh`
- **state**: live (Stage 1 of the local tmux bridge).
- **lane**: Lane 1 (read-only — captures tmux pane content,
  classifies status, writes a JSON snapshot to disk).
- **inputs**: none. Lane → tmux session map is hardcoded:
  - `lauburu` → `claude`
  - `codex-lauburu` → `codex`
- **effect**: writes
  `data/agent-status/lanes/coder_lanes.json` (CoderLanes
  payload) and per-lane snapshots
  `data/agent-status/lanes/<laneId>.json` (CoderLaneRow). All
  string fields pass through the two-pass redactor in
  `docs/CONNECTOR_SANITIZATION_RULES.md`. Path entries pass
  through the file-path masking rules; secret-shaped basenames
  are dropped, host-absolute paths are replaced with
  `<host_path>`. Long fields are truncated at word boundaries
  (`lastSummary` ≤ 1200 chars).
- **audit**: the JSON files ARE the audit row; future bridge
  writers (planned `POST /admin/lane-status` route per
  `chat-app/src/server/types/connector.ts`
  `LaneStatusWritePayload`) will pick these up. No event log
  yet.
- **safety**:
  - Subprocess calls are fixed-argv only (`tmux`, `git`).
    No `shell=True`, no `eval`, nothing from pane content
    reaches a shell.
  - Pane buffer is read but never executed.
  - Lane id validated against the `LaneId` enum at write time;
    unknown lanes are dropped.
  - Status defaults to `idle` on any read failure (NEVER
    fabricates `working` / `done`).
  - Detection of `done` requires both a pane-claim signal AND
    a clean `git status` per
    `docs/CONNECTOR_SANITIZATION_RULES.md` § Lane-status
    detection.
- **rejection criteria**: tmux not installed → exit 1 with
  `::error::tmux not installed`. python3 missing → exit 1 with
  `::error::python3 not installed`. Any unknown lane id in the
  hardcoded map → silently skipped (won't be written).

## Planned commands (NOT executed by any runtime today)

Each entry below is documented for Phase 2 / Phase 3 of the
owner-automation loop. The runtime stubs refuse these until the
explicit go batch lands.

### `QUEUE_ADD`

- **script**: `scripts/queue-add.sh` (planned)
- **state**: planned (per `OWNER_AUTOMATION_LOOP_PLAN.md` Phase 2)
- **lane**: Lane 2 (build autopilot — refuses Lane 3 prompts
  unless `--owner-approved` flag passed).
- **inputs**:
  - `agent` enum (same as `MARK_AGENT_DONE`)
  - `prompt_id` — UPPER_SNAKE prompt ID, must match a documented
    PROMPT-ID in repo
  - `lane` enum: `lane1` | `lane2` | `lane3`
  - `max_retries` integer 0–3 (default 1)
  - `--owner-approved` flag — required when `lane=lane3`
- **effect**: appends to `data/agent-queue/<agent>.json`.
- **audit**: writes a `queue_add` audit event (planned).
- **rejection criteria**: Lane 3 without `--owner-approved`,
  unknown prompt_id, agent outside enum.

### `QUEUE_POP`

- **script**: `scripts/queue-pop.sh` (planned)
- **state**: planned.
- **lane**: Lane 1 (read-only — pops the head of the queue).
- **inputs**: `agent` enum.
- **effect**: emits the next-prompt JSON to stdout, removes from
  the queue file, increments retry counter on failure.
- **audit**: planned audit event for each pop.

### `RUN_TYPECHECK`

- **script**: `scripts/run-typecheck.sh` (planned)
- **state**: planned.
- **lane**: Lane 1.
- **inputs**:
  - `package` enum: `mobile` | `chat-app` | `cloudflare-worker`
- **effect**: runs `npx tsc --noEmit` in the named package and
  records exit status.
- **audit**: writes a `tsc_run` audit event (planned).

### `DISPATCH_BUILD`

- **script**: NOT a script — bridge calls `gh workflow run` via
  the existing GitHub CLI auth.
- **state**: **NEVER auto-dispatched by the bridge.** Per
  `LOCAL_BRIDGE_WORKFLOW_PLAN.md` Stage 4 anti-rule: build
  dispatch is a human tap, no exceptions. Listed here only so
  the rejection is documented.
- **rejection criteria**: any bridge attempt to call
  `gh workflow run android-aab-build.yml` /
  `ios-testflight-build.yml` exits with `::error:: build
  dispatch must be a human tap (Admin/Dev Primary actions)`.

### `MARK_AUDIT_TRIAGED`

- **script**: `scripts/mark-audit-triaged.sh` (planned)
- **state**: planned.
- **lane**: Lane 1.
- **inputs**:
  - `event_id` — audit event ID from
    `data/audit-events/...`.
  - `triage_status` enum: `triaged` | `archived`.
- **effect**: updates the local audit-event store status field.
- **audit**: writes a `mark_audit_triaged` audit event.

## Deferred / explicitly forbidden

These are NOT in the allowlist and never will be without a
written security review:

- Any command that takes a free-text shell string.
- Any command that mutates `grappling.opml` or grappling content
  structure.
- Any command that touches Supabase via `psql` / direct SQL.
- Any command that posts to a paid AI API.
- Any command that rotates OAuth tokens or env secrets.
- Any command that writes to `apps/mobile/eas.json`,
  `apps/mobile/app.json` (`versionCode` / `buildNumber`), or
  `.github/workflows/*` — release configuration is owner-only.
- Any command that submits to App Store / Play Store production
  tracks.
- Any command that disables or bypasses `CONNECTOR_SECURITY_MODEL.md`
  invariants 1–10.

A bridge implementation MUST refuse any command outside this
file's `state: live` set with a non-zero exit code and zero
side effects.

## Validation checklist for adding a new command

Before committing a new entry to this doc:

1. Lane 1 / Lane 2 / Lane 3 classification matches
   `BACKLOG_AUTOMATION_SYSTEM.md`. Lane 3 requires explicit
   owner-approval flag at runtime.
2. All free-text inputs have an explicit length cap.
3. All enum inputs name every accepted value.
4. The `effect` field describes EXACTLY what files / routes the
   command writes.
5. The `audit` field names the event type if any.
6. The rejection criteria are spelled out.
7. The script under `scripts/` (or runtime stub) actually
   enforces the validation listed here — not just trusts the
   doc.

## Anti-rule

Documenting a command in this file does NOT activate it. New
commands move from `state: planned` to `state: live` only via
an explicit owner-go batch that ships the script + the
validation in code. The doc and the runtime evolve together;
neither leads the other.
