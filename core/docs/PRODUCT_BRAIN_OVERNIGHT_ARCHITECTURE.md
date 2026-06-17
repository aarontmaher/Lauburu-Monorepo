# Product brain — overnight architecture synthesis

The single doc that ties together the priority order, the
"nothing gets lost" rule, the live MCP model, push approvals,
audit automation, AI economics, and Forever Improve. Each
section is a one-screen-at-most synthesis with cross-references
to the existing specs that own the detail.

This is **doc-only**. No app code, no Worker code, no EAS
build, no production release.

## 0. Status check (2026-05-09)

- `project.get_current_state`: source=supabase, freshness=fresh
  (ageMs ≈173k, ~2.9m). Both lanes (claude/codex) reporting at
  HEAD `085b300` (`audit-agent-bundle aggregator`).
- `project.get_operating_rules`: returns 18 rules. Local repo
  carries 23 rules; rules 19–23 are repo-only until the Worker
  is redeployed (`cd cloudflare-worker && npx wrangler deploy
  --env preview`).
- `handoff.get_latest`: mobile bridge handoff fresh; 11 actions
  pending / 3 active / 1 blocked.
- `project.get_work_status`: priority unchanged — `Health
  connectivity Phase 1 mobile truth labels`. nextAction
  reaffirms "no EAS build until Agent confirms and Aaron
  approves." `blocker: None`.

## 1. Canonical priority order

This is the priority order Aaron's automation MUST honour
until he explicitly changes it. The bridge writer mirrors it
into MCP via `project.get_work_status.currentPriority`; this
doc is the source of truth for the FULL ordered list.

| Rank | Priority | Why now |
|---|---|---|
| 1 | **Health Connect / Apple Health installed-device truth** | Tester proof closes the v20 release gate; without it, Surface A parity (per `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2 (a)) cannot hold and Developer Mode cannot be turned off. |
| 2 | **Push approval notifications** | Phone-only operation requires Aaron approving from the lock screen instead of opening Admin/Dev manually. Setup blockers are the gate; see `docs/APPROVAL_GATES_AND_PUSH.md` § Push setup blockers. |
| 3 | **Admin/Dev approval centre** | Already substantially shipped (commits 87ebabc / 228160c / 11b8c75 / fe7f93d / eb81060 / 14bbf62 / 085b300). Remaining: server-side gate writeback (`project.update_approval_gate` etc on `/mcp/v2/admin`) so the chain progresses without manual ledger paste. |
| 4 | **Screenshot + auto click-through audit automation** | All four capture tiers shipped (simulator / iPhone Mirroring / scrcpy / Maestro) plus the synthesis aggregator (`audit:agent-bundle`). Remaining: install Maestro / scrcpy on Aaron's laptop when cadence justifies it. |
| 5 | **Grappling Readiness core** | Core readiness compute lives in `packages/shared/src/backend/services/readiness/`. Higher-priority work above gates this. Treat new readiness work as PARTIAL until item (1) clears the install gate. |
| 6 | **AI cost control / external AI offload** | Spend gates + research-job offload shipped (commits 228160c / 11b8c75). Remaining: cached-artifact reuse server-side; tester-stage offload is repo-ready in `apps/mobile/src/store/research-jobs-store.ts`. |
| 7 | **Forever Improve / product intelligence** | The long-tail backlog and the categorical UX/UI improvements live in `docs/APP_DEVELOPMENTS.md` § Forever Improve. Touch only after items 1–6 are PARTIAL or better. |

**Anti-rules**:

- A new prompt MUST NOT skip ahead from rank 7 → rank 1
  without an explicit Aaron statement.
- Rank 1 BLOCKS rank 2 only when the v20 retest fails. If
  v20 passes, rank 2 unblocks immediately and rank 1 demotes
  to rank 5–7 status.
- A coder seeing a high-impact opportunity from a low rank
  surfaces it as a Forever Improve / action-ledger entry — not
  by reordering the list silently.

## 2. "Nothing gets lost" — expanded

Every artefact below has a deterministic schema, an owner, and
a locking test. The full table lives in
`docs/ARTIFACT_SCHEMAS.md` § 1–7; this section restates the
RULE so the next person reading this doc cannot accidentally
let a finding stay terminal-only.

If a finding does not match one of the canonical artefact
shapes below, it is NOT done. Either it ladders into one of
these, or it stays on the action ledger as `pending` until
someone files it correctly.

| Finding type | Lands in | Capture path today |
|---|---|---|
| Terminal markers (MCP_RESULT / MCP_BLOCKER / MCP_COMMIT / MCP_TESTS / MCP_NEXT / AGENT_QA_RESULT_JSON) | Per-lane row → `connector_coder_lanes.payload.lastMarkers` (Supabase via bridge:snapshot / bridge:watch) | Coder/agent emits a single line; `parse_mcp_markers` extracts on every tick (`docs/MCP_BRIDGE_AUTOREFRESH.md` § 4) |
| Agent installed-device QA findings | `connector_handoff.payload.agentQaResult` + screenshot bundle | `npm run bridge:agent-qa <result.json>` |
| Audit-screenshot bundle | `artifacts/app-audit/<sub>/<isoTimestamp>/manifest.json` (gitignored, local-first) | `npm run audit:screenshots` / `audit:iphone-mirroring` / `audit:android-scrcpy` / `audit:maestro` / `audit:agent-bundle` |
| Feature ideas / UX / UI / cost / coaching ideas | `docs/APP_DEVELOPMENTS.md` § Forever Improve | Aaron / coder appends a short line under the matching category |
| Blockers (P0) | `data/action-ledger/pending_actions.json` row with status `blocked` + a triggerCondition | Coder appends; bridge upserts to `connector_handoff` |
| Approval gates | `data/approval-gates/gates.json` (repo state) + `apps/mobile/src/store/approval-gates-store.ts` (device cache) | Mobile-side hydrate; ledger note paste; future: `project.update_approval_gate` on `/mcp/v2/admin` |
| AI spend gates | `apps/mobile/src/store/spend-gates-store.ts` (device cache) + emitted ledger notes | Mobile-side; future server route covers this |
| Research outputs | `apps/mobile/src/store/research-jobs-store.ts` (device cache) keyed by `reuseHash` | Aaron pastes Deep Research result; same reuseHash auto-supersedes older artefacts |
| Operating-rule additions | `docs/OPERATING_RULES.md` + `cloudflare-worker/src/operating-rules.ts` (locked by `test-operating-rules.ts`) | Coder edits both; test enforces 1..N coverage |
| Forever Improve drift / quality bar | `docs/APP_DEVELOPMENTS.md` § Permanent improvement categories | Coder appends; nothing automated retires entries |

A coder MUST run `python3 scripts/test-bridge-snapshot-classifier.py`
+ `npm run bridge:verify` + `cd cloudflare-worker && npx tsx test/test-operating-rules.ts`
before claiming any finding is "captured" — those three tests
guarantee the bridge schema, the operating-rule index, and
the action-ledger redaction surfaces match repo state.

## 3. Live MCP model — finalised

| Concept | Value | Owner |
|---|---|---|
| Marker writeback drift | 10–30 seconds (poll 10s + min-write 10s + Supabase round-trip ~1–2s) | `scripts/bridge-watch.sh` |
| Heartbeat-only drift | 60 seconds | same |
| Freshness window (Worker) | 600 seconds (10 minutes) | `cloudflare-worker/src/mcp-v2.ts` `FRESHNESS_WINDOW_MS_V2` |
| `lastSeenAt` field | bumped every snapshot | `bridge_snapshot_classifier.heartbeat_envelope` |
| `lastStateChangeAt` field | bumped only on status transition; carries forward | `compute_state_change_at` |
| `lastMarkers.markerHash` field | FNV-1a 32-bit hex; changes whenever any marker text changes | `marker_hash` |
| `source` field | `tmux_bridge` for canonical writer | `heartbeat_envelope` |
| AdminDev drift warning | fires when ANY lane's `lastSeenAt` > 60s OR `freshness.staleReason !== 'fresh'` | `apps/mobile/app/admin-dev.tsx` `summariseLaneHeartbeat` |
| AdminDev marker chip | "Live marker writeback" rendered always (admin-only); flags markerCount + markerHash + most-recent value per lane | same `summariseMarkerWriteback` |

### All-workers-idle push trigger

When EVERY lane in `project.get_current_state.agents[]` has
`status` ∈ `{ idle, needs_review, blocked, needs_user,
complete_waiting_approval }`, the in-app banner fires today
(`useAdminDevNotificationStore.allWorkerDirectionAlertsEnabled`).
Once the push setup blockers in
`docs/APPROVAL_GATES_AND_PUSH.md` clear, the same condition
fires a system push notification using the
`lauburu_approval_gate_v1` notification category — payload
carries the `currentPriority` text only (≤ 80 chars), no
descriptions, no payloads. Server-side fan-out goes through
the future `project.notify_approval_gate` admin tool.

### Anti-rules

- The Worker's `staleReason` enum is the source of truth for
  freshness, NOT the per-lane heartbeat. A bridge that's
  pushing rows every 10s will read as `fresh`; a laptop that
  hasn't touched the bridge in 11 minutes will read as
  `no_writeback` regardless of any local file mtime.
- Marker text MUST NEVER carry secrets / raw user health
  values / file paths outside the repo. The two-pass redactor
  catches token shapes; emitters are still on the hook.
- The marker_hash is informational. Worker-side logic does
  not branch on it; only `bridge-watch.sh` reads it.

## 4. Push approval architecture — finalised

(Source of truth: `docs/APPROVAL_GATES_AND_PUSH.md`. This is
the synthesis.)

| Action | Mapping | App-open fallback |
|---|---|---|
| **Approve** | `useApprovalGatesStore.approve(gateId, 'approved via push notification action')` | If lock-screen action fails to deliver, gate stays `pending` and Aaron approves from the in-app approval centre. |
| **Defer 24h** | `useApprovalGatesStore.defer(gateId, +24h, 'deferred via push notification action')` | Same. |
| **Deny** | `useApprovalGatesStore.cancel(gateId, 'denied via push notification action')` — opens app to approval centre on iOS for confirm glance | App-open is INTENTIONAL for the destructive action. |

### Chained approvals

A gate can declare `dependsOnGateId: <upstream-gate-id>`. The
dependant is **locked** (cannot be approved / deferred) until
the upstream is `approved` or `completed`. Cancelled / expired
upstreams do NOT unlock the dependant — fail-closed; Aaron
must re-create.

Canonical example shipped today: `gate-mcp-core-worker-deploy`
depends on `gate-android-v20-play-upload` (the worker deploy
waits on the v20 Play upload completing first).

### Resume automation

When Aaron approves a gate from a push action, the store
emits a sanitized `ledgerNote` string that surfaces via the
**Copy last ledger note** button. Aaron / Codex pastes it into
`data/action-ledger/pending_actions.json`'s `evidenceSummaryOrLink`
for the matching action. Once the future
`project.update_approval_gate` admin tool ships on
`/mcp/v2/admin`, the writeback happens automatically.

### AI spend gates + build/release gates

AI spend gates extend the same ApprovalGate machinery with
extra fields (`triggerType`, `estimatedCostClass`,
`precheckSummary`, `precheckRuleId`). Build/release gates ride
on the existing `release.get_gate` Worker tool +
`AGENT_QA_RESULT_JSON` writeback path.

### Anti-rules

- safeDefault MUST stay biased toward inaction
  (`skip | wait | rollback | notify_only`).
- Push payload MUST stay short — title ≤ 80 chars, body
  generic. No descriptions, no actionPayload, no resolution
  notes.
- Notification action labels MUST stay short — `Approve`,
  `Defer 24h`, `Deny`. iOS truncates aggressively on lock
  screen.

## 5. Audit automation architecture — finalised

(Source of truth: `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` for
the tiers; `docs/AUDIT_SCREENSHOTS.md` /
`docs/IPHONE_MIRRORING_QA_WORKFLOW.md` /
`docs/AUDIT_SCRCPY_ANDROID.md` /
`apps/mobile/audit-flows/README.md` per tier; this is the
synthesis.)

| Tier | Tool | Output | Status |
|---|---|---|---|
| v1 manual | screen recording | not committed | Aaron's existing flow |
| v1.5 simulator/emulator | `npm run audit:screenshots` | `artifacts/app-audit/<isoTimestamp>/` | shipped (commit fc8d7c3) |
| v1.5 iPhone Mirroring | `npm run audit:iphone-mirroring` | `artifacts/app-audit/iphone-mirroring/<isoTimestamp>/` | shipped (commit 412dab2) |
| v1.5 Android scrcpy | `npm run audit:android-scrcpy` | `artifacts/app-audit/android-scrcpy/<isoTimestamp>/` | shipped (commit ce62e90) |
| v3 Maestro | `npm run audit:maestro` | `artifacts/app-audit/maestro/<isoTimestamp>/` | shipped (commit ce62e90); Maestro itself unin­stalled |
| v? synthesis | `npm run audit:agent-bundle` | `artifacts/agent-bundles/<isoTimestamp>/` | shipped (commit 085b300) |

### Capture cadence rule

Screenshots first; short recordings only when motion or
permission flow matters. Recordings are NOT committed; the
manifest may carry a `notes` line referencing the recording's
local path. Anti-rule: never auto-share recordings; they
often catch real Apple ID / Supabase email / push tokens.

### Agent-ready bundle contract

`audit:agent-bundle` picks the most recent capture across
every tier, copies under
`artifacts/agent-bundles/<isoTimestamp>/`, fetches a snapshot
of `project.get_current_state` + `project.get_work_status`,
and writes `manifest.json`. This is the single artefact Aaron
hands to Agent. Schema locked in
`cloudflare-worker/test/test-audit-screenshots-manifest.ts`.

## 6. AI economics plan — finalised

GrapplingMap stays cheap to operate during tester stage and
opens up paid AI flows behind explicit gates once public
launch happens.

### Tester stage (today through public release)

| Path | Cost surface | Status |
|---|---|---|
| Deterministic prechecks | $0 | shipped (`packages/shared/src/approval-gates/spend-prechecks.ts`) — every AI call surfaces a deterministic answer FIRST |
| Spend gates | $0 in repo | shipped — Aaron approves the spend before any paid call |
| External AI offload (ChatGPT / Deep Research) | Aaron's existing chat / Plus / Pro subscription | shipped (`packages/shared/src/research-jobs/index.ts`) — paste-into-ChatGPT prompt-export; `reuseHash` dedup auto-supersedes older artefacts |
| Cached artefacts | $0 to reuse | shipped — `findReusableByHash` short-circuits new spend when a fresh artefact exists |
| In-app paid LLM call | none | DEFERRED until Aaron approves; today the app makes zero paid LLM calls |

### Public stage (tier model)

| Tier | Included AI credits | Overflow |
|---|---|---|
| Free | none — deterministic-only paths visible | n/a |
| Member (paid) | bounded monthly credit pool (deterministic precheck still runs first) | pay-as-you-go via Stripe; rate-limited per user |
| Coach (higher tier) | larger credit pool + private coaching workflow | pay-as-you-go + custom-prompt cache |

Public-stage anti-rules:

- No tier may bypass the spend-gate precheck. Deterministic
  answer surfaces first, every time.
- Cached artefacts MUST be per-user-scoped on public surfaces;
  no cross-user reuse without explicit consent.
- Pay-as-you-go overflow MUST cap monthly per-user spend with
  a hard limit Aaron picks. Default proposal: $10/user/month
  hard cap; $25/user/month soft cap with notification.

### Anti-rules across both stages

- Auto-AI calls without an approved spend gate are FORBIDDEN.
- The spend-gate precheck output MUST appear BEFORE the AI
  rationale in any prompt export. Prevents users approving
  spend without seeing the deterministic answer.
- A research artefact older than its `freshnessWindowDays`
  reads as `stale`; it does NOT auto-block reuse, but the UI
  warns Aaron when the artefact is past its window.

## 7. Forever Improve — expanded

(Source of truth: `docs/APP_DEVELOPMENTS.md` § Forever Improve
+ § Permanent improvement categories. This section is the
short index — nothing here replaces those.)

| Direction | Status today | Cross-ref |
|---|---|---|
| **UX / UI** | continuous polish; never "done" | `docs/APP_DEVELOPMENTS.md` |
| **Mobile-only Admin/Dev** | substantially shipped — Now / Approval gates / Spend gates / Research offload / Live marker writeback / Lane heartbeat / Release gate / Developer Mode pill all live | `apps/mobile/app/admin-dev.tsx` |
| **Grappling Readiness depth** | repo-ready compute layer; tester-stage proof gates this | `packages/shared/src/backend/services/readiness/` |
| **Cost reduction** | spend gates + research offload + cached artefacts | § 6 above |
| **Gamification** | not started; appears in Forever Improve | `docs/APP_DEVELOPMENTS.md` |
| **Feedback incentives** | not started | same |
| **AI video analysis** | not started; long-tail | same |
| **Private coaching** | not started; Coach tier unlocks | § 6 above + `docs/APP_DEVELOPMENTS.md` |
| **Evidence-driven technique evolution** | not started; depends on cumulative grappling-session data | same |

## 8. Live vs repo-only vs planned

### Live (deployed Worker / installed app)

- `/mcp/v2` core surface with 8 tools (preview env)
- `/mcp/v2/admin` 17 tools (preview env)
- `/mcp/v2/website` 25 tools (preview env)
- `/mcp/v2/health` probe (preview env)
- `/mcp/core` 6-tool legacy surface (preview env)
- `/mcp/public` 4-tool legacy preview (preview env)
- Bridge writeback (Supabase) — connector_* tables stay HTTP
  200/200/200/201 on every snapshot
- Action ledger lives in repo + reaches MCP via the bridge

### Repo-only (NOT yet deployed to Worker)

- `project.ping` diagnostic tool (commit 1081d65)
- `agents[].lastStateChangeAt` field (commit 8ba25ae)
- `agents[].source` field (same)
- `agents[].lastMarkers` field (commit 14bbf62)
- Operating rules 19–23 (the deployed Worker reads 18; local
  repo + tests have 23)
- All audit:* npm scripts (run locally)

When Aaron approves the next Worker deploy, the command is:

```sh
cd cloudflare-worker && npx wrangler deploy --env preview
```

No EAS build needed for the Worker.

### Repo-only / mobile-side only (no server-side writeback yet)

- Approval gates / spend gates / research jobs (mobile stores
  emit ledger notes for manual paste; server-side
  `project.update_approval_gate` etc still TODO on
  `/mcp/v2/admin`)
- Push notification scaffold (lazy expo-notifications;
  six-step setup blocker chain in
  `docs/APPROVAL_GATES_AND_PUSH.md`)
- Maestro flows + scrcpy helper (Maestro / scrcpy themselves
  un­installed locally)

### Planned (NOT in repo)

- `project.update_approval_gate` / `project.update_ai_spend_gate`
  / `project.research_job_create` / `project.research_artifact_import`
  on `/mcp/v2/admin`
- `project.notify_approval_gate` on `/mcp/v2/admin`
- expo-notifications native dep (next EAS build, gated on
  Aaron approval)
- Apple Push Notification capability for
  `com.lauburu.grapplingmap`
- Public-stage tier model (Stripe wiring, per-user credit
  ledger)
- AI video analysis (Forever Improve)

## 9. Cross-references

Per section above, the canonical source of truth:

- § 1 priority order — this doc
- § 2 nothing-gets-lost — `docs/ARTIFACT_SCHEMAS.md`
- § 3 live MCP model — `docs/MCP_BRIDGE_AUTOREFRESH.md`,
  `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md`
- § 4 push approvals — `docs/APPROVAL_GATES_AND_PUSH.md`,
  `docs/HUMAN_APPROVAL_GATE_SPEC.md`
- § 5 audit automation —
  `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` plus the four
  per-tier docs
- § 6 AI economics — `docs/AI_SPEND_GATES_SPEC.md`,
  `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md`
- § 7 Forever Improve — `docs/APP_DEVELOPMENTS.md`
- § 8 live vs repo-only — this doc + the deploy command
- Operating rules (1..23 today) —
  `docs/OPERATING_RULES.md` +
  `cloudflare-worker/src/operating-rules.ts`
- Action ledger — `data/action-ledger/pending_actions.json`
