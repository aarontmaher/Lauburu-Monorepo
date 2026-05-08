# Live MCP model — freshness / drift / heartbeat / all-idle push

The synthesizing doc for the **live MCP read model**: what
"fresh" means, when "stale" fires, what marks a lane as
"drifted", what fires the all-idle push, how the Admin/Dev
tab renders these signals. Pulls together the pieces shipped
across `8ba25ae` (Bridge auto-refresh + heartbeat + drift),
`fe7f93d` (Developer Mode pill consuming drift), and the
operating rules (rule 11 / rule 12 / rule 14 / rule 18 /
rule 20).

This is **doc only**. No app code. No EAS build.

## 0. Why this doc

The pieces of the live MCP model are scattered:
- Rule 11 (MCP-first start) defines the read order +
  fresh / stale / unavailable branches.
- Rule 12 (laptop commands + writeback cadence) defines
  when freshness updates.
- Rule 14 (parallel priorities) defines what gets surfaced.
- Rule 20 (all-idle notification) defines when the
  all-3-idle push fires.
- Codex's `8ba25ae` ships the auto-refresh + heartbeat +
  drift warning fields.
- Codex's `fe7f93d` ships the Developer Mode pill that
  consumes those fields.

This doc consolidates them into a single operator-view
spec so future implementations don't drift.

## 1. Data model

The live MCP model exposes 4 signal classes:

### 1.1 Freshness

Per `project.get_current_state.freshness`:

```ts
interface Freshness {
  isFresh: boolean;
  staleReason: 'no_writeback' | 'stale_writeback' | 'mcp_unavailable' | null;
  lastWritebackAt: string;              // ISO
  lastWritebackAgeSeconds: number;
  freshnessThresholdSeconds: number;    // default 300 (5 min); per-source configurable
  source: 'bridge' | 'project_update_work_status' | 'admin_dev_writeback' | 'unknown';
}
```

Threshold tuning per source:
- `bridge:snapshot` cadence: target ≤5 min between writes
  during active workdays. Stale if `>5 min` AND a coder is
  reporting `working` status.
- `project.update_work_status` calls: per-task; whatever
  cadence the coder maintains per rule 12.
- `admin_dev_writeback`: when Aaron edits ledger / settings
  from admin-dev, the Worker upserts directly.

Stale reasons:
- `no_writeback`: the writeback path has never fired since
  the last freshness reset.
- `stale_writeback`: writeback fired but `>thresholdSeconds`
  ago.
- `mcp_unavailable`: Worker not responding / 5xx / DNS fail
  (rule 11 unavailable branch — STOP, don't fall back).

### 1.2 Lane heartbeat

Per `project.get_current_state.agents[]`:

```ts
interface AgentLaneHeartbeat {
  id: 'claude' | 'codex' | 'agent';
  status: 'idle' | 'working' | 'blocked' | 'needs_review' | 'needs_user' | 'complete_waiting_approval';
  currentTask: string | null;
  lastHeartbeatAt: string;
  heartbeatAgeSeconds: number;
  driftDetected: boolean;
  driftReason: 'no_heartbeat' | 'stuck_on_same_task' | 'no_writeback_for_commit' | null;
  currentCommitSha: string | null;
}
```

Per Codex's `8ba25ae` work, lane drift detection fires when:
- `status: 'working'` AND `heartbeatAgeSeconds > 1800` (30
  min) → `driftReason: 'no_heartbeat'`.
- `status: 'working'` AND `currentTask` unchanged for ≥45
  min → `driftReason: 'stuck_on_same_task'`.
- A new commit landed but `lastHeartbeatAt` doesn't reflect
  the post-commit writeback per rule 12 → `driftReason:
  'no_writeback_for_commit'`.

Drift surfaces a yellow lane chip in admin-dev + a one-line
note ("Codex stuck on Tests + commit for 47 min") so Aaron
can surface a check-in.

### 1.3 Build / release gate state

Per `mobile.get_build_status` + `release.get_gate`:

```ts
interface BuildGateState {
  android: { versionCode: number; playStatus: string; playTrack: string };
  ios: { buildNumber: string; testflightStatus: string };
  releaseGate: {
    newAndroidBuildAllowed: boolean;
    newTestFlightAllowed: boolean;
    reason: string;
  };
}
```

Used in admin-dev's release-gate chip + Developer Mode pill
recommendation.

### 1.4 All-idle / all-stopped detection

Per rule 20:

```ts
interface AllIdleState {
  isAllIdle: boolean;                    // all 3 lanes status: 'idle'
  isAllStopped: boolean;                 // all 3 lanes in {idle | blocked | needs_review | needs_user | complete_waiting_approval}
  hasBlocker: boolean;                   // any lane status === 'blocked'
  isAaronPaused: boolean;                // explicit pause recorded in APP_DEVELOPMENTS.md
  lastTransitionAt: string;
  pushEligible: boolean;                 // isAllIdle AND !hasBlocker AND !isAaronPaused AND freshness.isFresh
}
```

Push eligibility (rule 20):
- All 3 lanes idle.
- No blocker on any lane.
- No Aaron-paused decision.
- Freshness is `isFresh: true` (NEVER fire from stale or
  unavailable MCP — false-idle risk).

If `isAllStopped` (broader) is true but `isAllIdle` is not,
the in-app banner fires (admin-dev "All-worker direction
banner" already shipped) but the push does NOT fire — push
is reserved for the narrower all-idle case.

## 2. Worker side — auto-refresh contract

Per `8ba25ae` (Codex), the bridge has been extended with
auto-refresh + heartbeat + drift markers. The contract:

| Field | Updated when | Reset when |
|---|---|---|
| `freshness.lastWritebackAt` | Any `bridge:snapshot` / `project.update_work_status` write | Never reset; monotonic forward |
| `agents[].lastHeartbeatAt` | Same as above (per-lane scope) | Never reset; monotonic forward per lane |
| `agents[].driftDetected` | Computed at read time per § 1.2 thresholds | Auto-clears when fresh writeback lands |
| `freshness.staleReason` | Computed at read time | Auto-clears on fresh writeback |

The Worker does NOT background-poll Supabase. It reads on
each `project.get_current_state` call + computes drift at
read time. This keeps Worker cost low (Cloudflare free
tier covers it) + ensures every read is current.

## 3. Admin/Dev rendering

Per Codex's `fe7f93d` (Developer Mode pill) + the proof
checklist (`docs/ADMIN_DEV_PROOF_CHECKLIST.md` § 1):

### 3.1 MCP freshness pill

```
┌─ Now ───────────────────────────────────────┐
│ Freshness: Live · 2 min ago                 │   ← fresh
│ Freshness: Stale · 12 min ago               │   ← stale_writeback
│ Freshness: MCP unreachable                  │   ← mcp_unavailable
└─────────────────────────────────────────────┘
```

### 3.2 Lane chips

```
Claude  · Idle · 1 min                          ← normal
Codex   · Working · Tests + commit · 28 min     ← normal (within thresh)
Agent   · Working · ...drift 47 min ⚠           ← drifted
```

Drift triggers a yellow background + the `driftReason`
abbreviated (`stuck on same task`).

### 3.3 Developer Mode recommendation pill

Per `fe7f93d`:
- "Keep Developer Mode ON" — default; safe-fallback.
- "Developer Mode safe to turn OFF (device-side)" — fires
  ONLY when freshness is fresh + lane heartbeat is fresh +
  release.get_gate is readable + Surface A parity criteria
  (per `MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2).
- "unknown" — Worker reachable but a required field is
  missing.

Conservative default: keep-on. Aaron flips OFF only after
the proof checklist passes end-to-end.

### 3.4 All-idle banner

Per rule 20 + `apps/mobile/app/admin-dev.tsx` § Owner
alerts → "All-worker direction banner". Today: in-app
banner only. After CODEX-FS-XXX-ALL-IDLE-PUSH-NOTIFICATION-01
(handoff #1 of 5; foundation tier shipped in `c6fb518`):
push fires when `pushEligible: true`.

## 4. Operator escalation flow

When the live MCP model surfaces a problem:

| Signal | Operator response | Source rule |
|---|---|---|
| Freshness `stale_writeback` | Run `bridge:snapshot` from laptop OR ask the lane to refresh writeback. | rule 12 |
| Freshness `mcp_unavailable` | STOP the task; do not fall back to memory unless Aaron approves "fallback mode". | rule 11 amendment (unavailable branch) |
| Lane drift `stuck_on_same_task` | Check in with the coder; ask for a status update + writeback. | rule 12 cadence |
| Lane drift `no_writeback_for_commit` | Coder ran a commit but didn't run `bridge:snapshot`. Workflow bug — coder fixes the workflow. | rule 12 |
| All-idle push fires | Aaron feeds the next prompt per rule 19 (coordinator-fed idle lanes). | rule 19 + rule 20 |
| Approval gate push fires | Aaron approves / defers / denies per `PUSH_APPROVAL_AUTOMATION_SPEC` §§ 2-4. | rule 21 / 22 / 23 |
| Audit finding pending | Reviewed in Admin/Dev Memory panel (per `MCP_MEMORY_ARCHITECTURE_SPEC` § 3). | rule 18 |

Every operator response is recorded in the action ledger
(rule 18) so the response itself becomes evidence.

## 5. Implementation status

| Component | Status | Source |
|---|---|---|
| Worker `project.get_current_state` returning freshness | LIVE | shipped earlier this session |
| Worker auto-refresh + heartbeat fields | LIVE | Codex `8ba25ae` |
| Lane drift detection at Worker read time | LIVE | Codex `8ba25ae` |
| Admin/Dev freshness pill | LIVE | per the proof checklist § 1 |
| Admin/Dev lane chips | LIVE | per the proof checklist § 2 |
| Admin/Dev Developer Mode pill | LIVE | Codex `fe7f93d` |
| Admin/Dev all-idle in-app banner | LIVE | per `admin-dev.tsx` § Owner alerts |
| All-idle push notification | PARTIAL — foundation tier | Codex `c6fb518` (lazy expo-notifications scaffold + pure mapper) |
| Approval-gate push (rule 21) | PARTIAL — chained-approvals impl shipped | Codex `eb81060` |
| AI-spend gate push (rule 22) | SPEC ONLY | `CODEX-FS-XXX-AI-SPEND-GATES-IMPL-01` staged |
| Research-job push (rule 23) | SPEC ONLY | `CODEX-FS-XXX-DEEP-RESEARCH-OFFLOAD-IMPL-01` staged |

## 6. Anti-rules

- **No false-fresh fire.** Push notifications NEVER fire
  when freshness is `stale_writeback` or `mcp_unavailable`
  — false-idle risk.
- **No silent drift accumulation.** Drift always surfaces
  in admin-dev within one freshness threshold of the
  trigger.
- **No public exposure of full payload.** Public-safe
  surfaces show counts + statuses; full lane summaries +
  drift reasons stay admin-token-gated.
- **No background polling.** Read-time computation only
  to keep Worker cost minimal.
- **No Critical Alerts entitlement** for push (rule 21
  reaffirmed).
- **No threshold drift.** Default freshness threshold (5
  min) + drift threshold (30 min heartbeat / 45 min same-
  task) are configurable per-environment but never set
  below 60s for freshness or 5min for drift — anything
  tighter would false-positive.

## 7. Cross-references

- `docs/OPERATING_RULES.md` § 11 (MCP-first) / § 12
  (laptop commands + cadence) / § 14 (parallel priorities)
  / § 18 (action ledger) / § 19 (coordinator-fed idle) /
  § 20 (all-idle notification).
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 push
  surface this lives alongside.
- `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md` — synthesis of
  all push surfaces.
- `docs/ADMIN_DEV_PROOF_CHECKLIST.md` § 1-2 — the proof
  rows that verify this model end-to-end.
- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2 — how
  Surface A's freshness signal feeds the Developer-Mode-off
  criterion.
- `docs/MCP_MEMORY_ARCHITECTURE_SPEC.md` — operator
  escalation responses recorded as memory artifacts per
  § 4.
- Codex commits: `8ba25ae` (auto-refresh + heartbeat +
  drift) + `fe7f93d` (Developer Mode pill consuming
  drift) + `c6fb518` (push foundation) + `eb81060` (chained
  approvals).
