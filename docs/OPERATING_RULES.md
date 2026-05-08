# Operating rules — canonical

The rules every coder, agent, and consumer of this codebase
must follow. **Pinned and visible** — both as this doc and as
a tool exposed by the Worker MCP at
`project.get_operating_rules` (No Auth) AND as an
`operatingRules` field on `/api/control_centre`.

**Read rule 11 first.** "MCP-first" means: before starting any
new task, check the MCP / control-centre state. The other
ten rules govern HOW the work is done; rule 11 governs WHEN
to start it. **Rule 12** then governs WHO runs the laptop
commands — coders do, Aaron approves from phone. **Rule 13**
then governs HOW required Aaron-facing steps are presented:
clear steps first, automate before asking Aaron, and separate
coder/agent automation from true manual owner action. **Rule
14** then governs how multiple workstreams co-exist: parallel
priorities stay active in every status report — focused
readiness work must not silently starve MCP writeback, phone
control centre, idle notifications, automation, or health
input expansion. **Rule 15** then governs orchestration
between workers: no worker prompt may have its main action
be "wait for another worker to finish" — every prompt
includes a stay-busy fallback lane. **Rule 16** then closes
the delayed-instruction gap: never tell Aaron to remember a
future terminal command after another worker returns; preserve
the follow-up in the same worker prompt, MCP, bridge handoff, or
Agent QA result instead. **Rule 17** then defines the backlog
contract for deferred prompts / actions: store them with trigger
conditions and status, surface them when active, and void or remove
obsolete ones. **Rule 18** then makes that ledger universal:
every prompt, goal, human step, coder step, Agent step, or AI step
stays recorded until evidence proves completion or removal.

This doc is the source of truth. The Worker constant in
`cloudflare-worker/src/operating-rules.ts` is the **mirror** —
when the doc changes, the constant must change in the same
commit, and the live test asserts the two stay in sync (count +
hash of the rule strings).

Updated 2026-05-08.

## The twenty-three rules

These are stable. Coders MUST NOT promote, demote, reorder, or
soften any of them without an explicit doc commit referenced by
this file.

1. **Audit → bundles.** After every Agent audit, turn findings
   into parallel Claude/Codex work bundles in
   `docs/FEEDBACK_SUGGESTIONS.md` (FS-XXX candidates).
2. **Parallel non-overlapping lanes.** Keep both coders
   (Claude + Codex) working simultaneously in separate,
   non-overlapping lanes. No coder edits another coder's
   in-flight files.
3. **Don't stop at one patch.** Continue working through the
   bundle until materially complete OR genuinely blocked. One
   passing test is not a stopping point.
4. **Re-audit on implementation-complete.** When an item is
   `Implementation-complete, awaiting Agent functional
   confirmation`, re-run the Agent functional audit before
   any further promotion.
5. **Agent-confirmed gate.** If the Agent audit confirms,
   mark `Agent-confirmed, ready for Aaron approval`. Do not
   skip this label.
6. **Agent-not-confirmed = investigate.** If the Agent audit
   does NOT confirm, investigate why and continue. Do not
   silently re-mark.
7. **EAS build cost control.** No EAS build unless ALL hold:
   Agent functional audit complete, Agent confirms the change
   is worthwhile to test on-device, change is bundled,
   typecheck/tests pass, AND Aaron explicitly approves the
   build. Default is no build.
8. **Coders may say "implementation-complete", never "fully
   done".** Only Aaron-tested-on-device qualifies as fully
   done. The four-status sequence
   (`Implementation-complete, awaiting Agent functional
   confirmation` → `Agent-confirmed, ready for Aaron build
   approval` → `Aaron-approved for EAS build` →
   `Built/tester-ready`) is mandatory.
9. **Health/readiness claims stay provisional.** Until direct
   source data (Apple Health hub / Health Connect hub +
   verified manual log) supports stronger claims, every
   reading carries `confidence: provisional` floor and hedge
   language only. No "you are ready" / "skip training today"
   claims.
10. **Apple Notes is scratchpad only.** Repo docs + MCP +
    control-centre are the source of truth. Anything intended
    to drive coder / agent / Aaron action MUST be promoted
    into the repo-backed flow.
11. **MCP-first start.** Before any project action or answer,
    every coder / agent / ChatGPT MUST check the Grappling Map
    MCP Core state. Required check order:
    1. `get_work_status` (or `mobile.get_work_status` /
       `project.get_current_state` on `/mcp/v2`)
    2. `list_pending_suggestions` (website MCP) /
       `project.get_overview` (this codebase)
    3. `get_automation_state` (website MCP)
    4. `get_handoff` (or `handoff.get_latest` on `/mcp/v2`)
    5. `/api/control_centre` if reachable
    Then state: what MCP says; whether MCP appears `fresh` or
    `stale` (per the `freshness.staleReason` field on
    `project.get_current_state`); compare with terminal /
    control-centre if needed; only then choose the next task.
    If MCP is **stale** (responding but `staleReason` set), say
    "MCP stale", use the latest local bridge / terminal /
    control-centre artefacts as fallback, AND continue fixing
    MCP canonical sync as a priority.
    If MCP Core is **unavailable** (not responding, 5xx, or
    DNS failure), say so clearly, **STOP** any audit / task /
    answer that depends on live project state, and do **NOT**
    fall back to memory, Apple Notes, screenshots, or old docs
    unless Aaron explicitly approves a "fallback mode" for
    that specific question. Never start from memory in any
    other case.
12. **Coders run all laptop commands; Aaron approves from
    phone.** Aaron's role is approval, not execution. Coders
    (Claude / Codex) run every laptop command in
    `docs/CODER_LAPTOP_COMMANDS.md` — `npm run bridge:snapshot`,
    `npm run bridge:verify`, `cd cloudflare-worker && npx tsc
    --noEmit`, `cd cloudflare-worker && wrangler deploy`,
    `git add` / `git commit` / `git push`, all live and
    contract tests. Aaron NEVER runs typecheck, deploy,
    bridge:snapshot, or git commands on a laptop. After every
    meaningful unit of work, the coder MUST refresh the
    canonical store via `bridge:snapshot` or
    `project.update_work_status` so MCP doesn't drift to
    `staleReason: 'no_writeback'`. The only steps that stay
    on Aaron are listed in
    `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § 5: FS-XXX approval,
    EAS build approval, tester-device verification,
    vendor-console steps Aaron alone can do, judgement-call
    decisions, "I tested this on my phone" health-source
    confirmations, and pasting vendor secrets the one time
    they get rotated. Anything else asked of Aaron is a
    workflow bug — coder fixes the workflow.
13. **Clear steps; automate first.** When something is required,
    the worker MUST give Aaron clear step-by-step instructions
    and automate the step whenever it is safe. Claude / Codex /
    Agent should be used wherever possible before asking Aaron to
    act. Aaron should only do secrets, approvals, logins, 2FA,
    vendor dashboards, or safety-sensitive confirmations. Every
    output that names follow-up work MUST separate: `automated by
    coder/agent`, `manual Aaron step`, and `blocked until Aaron
    acts`. No EAS build may be requested, recommended, prepared, or
    triggered unless Agent confirms worthwhile on-device testing
    and Aaron explicitly approves.
14. **Parallel priorities stay active.** Focused product work
    (e.g. Grappling Readiness) MUST NOT cause neglect of other
    active workstreams. The standing parallel priorities are:
    (a) MCP writeback / no-screenshot workflow,
    (b) Admin/Dev phone control centre,
    (c) idle notifications for Claude / Codex / Agent,
    (d) full automation of laptop commands per rule 12,
    (e) health input expansion (journal, blood test, DEXA, body
    composition, spirometry, conditioning machine data, etc.).
    Coders / Agent MUST surface progress on each parallel priority
    in every status report — at minimum a one-line freshness
    note ("MCP writeback: rule 12 cadence holding"), a flag if
    a parallel priority has gone unmoved for >7 days, and a
    suggestion for the next safe sub-batch. Pausing a parallel
    priority requires an explicit Aaron decision recorded in
    `docs/APP_DEVELOPMENTS.md` priority order, never a silent
    drift.
15. **No-idle dependency.** No worker prompt may have its
    main action be "wait for another worker to finish."
    If a next step depends on another worker:
    (a) put the follow-up inside the same worker's prompt
    when possible, so that worker can continue immediately
    after its own patch;
    (b) give other workers non-overlapping adjacent work
    they can do now — tests, bridge / MCP support, schemas,
    docs, release prep, route-smoke harness, redaction
    checks, data-model support;
    (c) if Worker B must verify Worker A's output, Worker B
    prepares the verifier / harness now and then continues
    into other safe same-lane tasks until Worker A's output
    exists.
    Every worker prompt MUST include a stay-busy rule per
    rule 3 AND an explicit alternative non-blocking lane.
    No coder / agent sits idle because a dependent prompt
    was split incorrectly. If a coder reports "blocked
    waiting on X", that's a workflow bug and the prompt
    should have been split differently — fix the prompt
    template, not the worker.
16. **No delayed instruction chains.** Do not tell Aaron:
    "After Agent / Codex / Claude returns, run X." Put the
    follow-up step inside the same worker prompt whenever
    possible, and tell that worker to execute, prepare, or
    hand off the next action itself. If a step depends on
    another worker, the same prompt must include the follow-up
    action and stop condition. If another worker cannot proceed
    yet, give it non-blocking adjacent work, not a waiting
    prompt. If a manual / device action is required from Aaron,
    make that the only immediate action and store later commands
    in MCP / bridge / handoff. Use bridge handoff files,
    `AGENT_QA_RESULT_JSON`, prompt jobs, or MCP state to
    preserve next steps so Aaron does not have to remember them.
    Never make Aaron carry delayed terminal commands in memory
    while working with other agents.
17. **Backlog deferred prompts/actions; remove void ones.**
    Never make Aaron remember delayed instructions. Do not say
    "after Agent returns, run X" or "after Claude finishes, paste Y"
    as an untracked instruction. Store deferred prompts / actions in
    MCP, bridge artifacts, or a local backlog with: `id`, `owner`,
    `targetWorker`, `triggerCondition`, `promptOrActionText`,
    `priority`, `createdAt`, `status: pending | active | completed |
    void | superseded`, and `voidReason` when void. When the trigger
    condition becomes true, surface the item as the next prompt /
    action. If the item becomes obsolete, unsafe, replaced, already
    completed, or irrelevant, mark it `void` or remove it. Prefer
    putting follow-up steps inside the same worker prompt so the
    worker can continue without Aaron. If human / device action is
    unavoidable, store the later command in the backlog rather than
    relying on Aaron's memory.
18. **Action ledger until evidence clears.** Every prompt, action,
    goal, human action, coder action, Agent action, or AI action must
    be recorded in MCP / bridge until evidence proves it is completed
    or no longer necessary. **Terminal state is evidence, not
    memory** — anything discovered in a tmux pane, a build log, an
    EAS console, a Play Console screen, or any other transient
    surface MUST be written back to the action ledger /
    `connector_*` tables / canonical doc before being considered
    tracked. Terminal checks must NEVER become the only source of
    truth. The MCP / action ledger must capture every queued task,
    deferred prompt, approval gate (rules 21 / 22 / 23), audit
    finding (per `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md`), and
    follow-up. A pending action can be cleared only with
    evidence of completion, supersession, void / obsolete state,
    unsafe / rejected state, or no-longer-necessary state. Each record
    should include: `id`, `owner`, `targetWorkerOrPerson`, `lane`,
    `actionText`, `triggerCondition`, `status: pending | active |
    completed | blocked | void | superseded`, `priority`,
    `createdAt`, `updatedAt`, `evidenceSummaryOrLink`, and
    `voidReason` / `supersededBy` when applicable. Public MCP surfaces
    may show compact redacted summaries; full action detail is admin
    gated. Obsolete Agent prompts, stale worker prompts, and completed
    bridge commands must be voided or superseded, not left active.
19. **Coordinator-fed idle lanes.** When Claude, Codex, or Agent is
    idle, the coordinator (Aaron via ChatGPT or laptop) MUST provide
    the next highest-leverage prompt for that lane unless a real
    external blocker or explicit Aaron pause exists. Do not let coders
    sit idle while active project priorities (per rule 14) remain.
    The coordinator's pacing obligation is the inverse of rule 15's
    coder obligation: rule 15 makes individual prompts non-idling-by-
    design; this rule makes the prompt cadence non-gapping. Idle
    without a fed prompt for >15 minutes during active workdays is a
    workflow bug — surface it via `project.get_current_state`
    freshness signal and the action ledger backlog (rule 18).
    Acceptable pause states: tester-device QA awaiting Aaron, EAS
    billing limit, vendor-console wait, sleep, or explicit Aaron-paused
    decision recorded in `docs/APP_DEVELOPMENTS.md`. Unacceptable: "I
    forgot to give the coder the next thing." If a lane has no
    high-leverage adjacent work, the coordinator MUST queue a
    backlog-grooming or doc-refresh prompt rather than leave it idle.
20. **All-idle notification.** When Claude, Codex, and Agent are all
    in an `idle` state simultaneously (all three lanes report
    `status: 'idle'` via `project.get_current_state.agents[].status`),
    the app MUST notify Aaron via a pop-up / banner / push
    notification. Exclusions: do NOT fire when (a) any lane has a
    blocker recorded — blockers have their own dedicated alert
    surface, OR (b) an explicit Aaron pause decision is recorded in
    `docs/APP_DEVELOPMENTS.md` priority order. The notification
    payload MUST include: (1) current top priority title from
    `project.get_current_state.priority`; (2) recommended next action
    drawn from `project.list_priorities` or the action ledger
    backlog; (3) timestamp of the all-idle state; (4) freshness check
    — only fire when MCP is fresh, never from stale or unavailable
    MCP (which would risk a false-idle signal — rule 11 honoured).
    The notification serves rule 19 (coordinator-fed idle lanes) by
    telling Aaron immediately when all coders need a new prompt
    rather than requiring him to poll the admin-dev surface. In-app
    banner is implemented at `apps/mobile/app/admin-dev.tsx` § Owner
    alerts → "All-worker direction banner"; **push notification
    implementation is a Codex follow-up batch** (handoff staged in
    `docs/CONTROL_CENTRE_MVP_SPEC.md`).
21. **Human-approval push gate.** When automation pauses awaiting
    Aaron's approval (any prompt or action ledger row with
    `status: waiting_for_approval`), the app MUST send a push
    notification — even if the app is closed — provided push
    permissions are granted (per rule 20's push wiring). Notification
    payload MUST include: (1) **what needs approval** — action name
    + brief context, ≤140 chars; (2) **why it matters** — consequence
    summary (e.g. "EAS build deducts X credits" / "Cloudflare
    deploy" / "Supabase row reset"); (3) **current top priority**
    for context; (4) **safe default if Aaron defers** (e.g. "Defer
    24h" / "No build" / "Stay on current state"); (5) **action
    buttons** where the platform supports them — Approve / Defer /
    Block; fallback is tap-to-open the Admin/Dev approval centre.
    Approval gate state machine:
    `waiting_for_approval` → `approved` | `deferred` | `expired` |
    `blocked`. On `approved`: automation resumes from the action
    ledger / MCP at the exact next step. On `deferred`: gate
    re-fires after the deferred-until timestamp. On `expired`: gate
    auto-transitions to `blocked` with reason
    `expired_no_response`. On `blocked`: gate is closed and a
    Codex/Claude follow-up prompt is required to advance.
    Safety floor: NO production release, NO EAS build, NO
    destructive Worker deploy, NO Supabase migration may proceed
    past `waiting_for_approval` without an explicit `approved`
    event recorded in the ledger. Honours rule 7 (EAS build cost
    control), rule 11 (MCP-first), and rule 18 (action ledger).
    Full spec: `docs/HUMAN_APPROVAL_GATE_SPEC.md`.
22. **AI spend gate.** Cheap deterministic / backend / local
    analysis MUST run first. If a request is likely to require
    expensive AI inference (long-context reasoning, deep research,
    multi-pass synthesis, vision-heavy audit, or any path that
    materially increases monthly AI spend above Aaron's configured
    threshold), the app MUST notify Aaron via push (sharing rule
    21's gate wiring) BEFORE initiating the spend, with the gate
    UI offering: `approve_in_app` / `defer` / `export_prompt`
    (paste into external ChatGPT / Claude.ai / etc.) / `ignore`.
    Cost classes:
    - `free_deterministic` — local rules, regex parsers, MCP
      reads, `bridge:snapshot`, parser-only journal-import — runs
      without ask.
    - `cheap_ai` — short-context calls within the monthly free
      tier or below the user-configured threshold — runs without
      ask but is rate-limited per `CONNECTOR_SANITIZATION_RULES`.
    - `expensive_ai` — long-context, multi-pass, vision-heavy, or
      beyond the threshold — REQUIRES gate (uses rule 21 state
      machine).
    - `deep_research_external` — work the in-app AI cannot do
      well or that costs more than the monthly budget — surfaces
      "Export prompt" so Aaron can paste into external AI without
      paying for in-app inference.
    Notification payload: action name; why it matters;
    `estimated_cost` (credits / tokens / dollars); Approve / Defer
    / Export prompt / Ignore buttons. Settings: per-user monthly
    AI budget (default $5/month); "always ask above $X" threshold
    (default $0.50/call); pay-as-you-go credits (later).
    **Privacy floor**: NEVER send raw sensitive data (journal
    text, health metrics, PII, raw terminal output) to ANY AI
    inference path (in-app or external) without explicit per-call
    approval; default for `expensive_ai` is "summarize first,
    send minimal context". Honours rule 7 (cost control), rule 11
    (MCP-first), rule 21 (approval gates). Spec:
    `docs/AI_SPEND_GATES_SPEC.md`.
23. **Deep research offload + artifact cache.** When an
    `expensive_ai` request (rule 22) classifies as
    `deep_research_external`, the app MUST:
    1. Compute a `reuseKey` hash from `triggerType` +
       redacted `sourceDataSummary`.
    2. Check the research-artifacts cache. If a non-stale
       artifact matches, **cite it via `cited_artifact_id`
       and skip re-running** — the same research never
       repeats while a valid artifact exists.
    3. If no match, create a research job with status
       `waiting_for_approval` (rule 21 gate).
    4. On `approved`, generate a ready-to-run external-AI
       prompt (default ChatGPT Deep Research; configurable)
       Aaron copy-pastes.
    5. On Aaron's import of the external result, store as a
       cached artifact indexed by `reuseKey`, status
       `cached`, with `expiresAt`. Future requests with the
       same `reuseKey` reference the cached artifact without
       re-spending.

    **Schema fields**: `id`, `triggerType`, `prompt` (the
    external-AI-ready text), `sourceDataSummary` (redacted),
    `reuseKey`, `status` (`waiting_for_approval | approved |
    running | imported | cached | stale | blocked`),
    `approvedAt`, `resultArtifactId`, `expiresAt`,
    `citationCount`.

    **Triggers**: complex journal entry; blood test PDF /
    DEXA scan; new health trend; readiness anomaly; large
    visual app audit; long athlete-memory synthesis.

    **Cache rules**: NEVER re-run research with a non-stale
    matching `reuseKey`; cite the cached artifact in every
    future explanation that uses it; mark stale after
    configurable TTL (default 90 days for health context,
    30 days for app-state audits).

    **UX**: push (per rule 21) with action buttons Approve /
    Defer / Copy prompt / Import result.

    **Safety**: redacted minimal context only; user approval
    before any sensitive data leaves the app (rule 22 privacy
    floor); imported result MUST NOT contain medical advice
    or causation claims (rule 9 + journal-spec § 12 anti-
    rules); the import path strips any remaining advice /
    causation language at parse time.

    Honours rule 7 (cost control), rule 9 (provisional health
    claims), rule 11 (MCP-first), rule 21 (approval gates),
    rule 22 (AI-spend ladder). Spec:
    `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md`.

## Where to find each rule's full body

| Rule # | Full body lives at |
|---|---|
| 1 | `docs/FEEDBACK_SUGGESTIONS.md` § Workflow |
| 2 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § Three lanes |
| 3 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` (lane bounds), implicit "stay busy" rule in every overnight prompt |
| 4 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost control rule" |
| 5 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § Status wording |
| 6 | `docs/FEEDBACK_SUGGESTIONS.md` § Status enum (`needs_review` transitions) |
| 7 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost control rule"; `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` § Safety gates |
| 8 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § Status wording; `docs/FEEDBACK_SUGGESTIONS.md` § Build-readiness wording |
| 9 | `docs/POST_MCP_PRODUCT_LANES.md` Lane B; `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md`; `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` |
| 10 | `docs/APP_DEVELOPMENTS.md` (top); `docs/BACKLOG_AUTOMATION_SYSTEM.md` § Source of truth |
| 11 | `docs/MCP_CANONICAL_STATE.md` (canonical paths); `docs/MCP_PHONE_CONTROL_CENTRE.md` (curl examples); `docs/CHATGPT_CONNECTOR_SETUP.md` (recommended connector) |
| 12 | `docs/PHONE_ONLY_AUTOMATION_PLAN.md` (workflow + remaining manual Aaron steps); `docs/CODER_LAPTOP_COMMANDS.md` (full command list + cadence) |
| 13 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "Clear steps; automate first"; `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § "Remaining manual Aaron steps" |
| 14 | `docs/APP_DEVELOPMENTS.md` § "Active priority order" (parallel-priority list); `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` § "Evidence input roadmap (v1 / v2 / v3)" (workstream parallelism for readiness inputs) |
| 15 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "Coder report contract — rule 12" (extended with the no-idle-dependency clause); `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md` § Stage 3 prompt template (every dispatched template carries an explicit alternative non-blocking lane) |
| 16 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "No delayed instruction chains"; `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md` § Stage 3 prompt template; `docs/CONTROL_CENTRE_MVP_SPEC.md` § prompt refs / handoff prompts |
| 17 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "Deferred prompts/actions backlog"; `docs/MCP_CANONICAL_STATE.md` § public v2 tools and backlog state; `docs/CONTROL_CENTRE_MVP_SPEC.md` § prompt refs / handoff prompts |
| 18 | `docs/BACKLOG_AUTOMATION_SYSTEM.md` § "Action ledger"; `docs/MCP_CANONICAL_STATE.md` § action ledger surface; `docs/CONTROL_CENTRE_MVP_SPEC.md` § prompt refs / handoff prompts |
| 19 | This file § rule 19; `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § coordinator-cadence; `docs/CHATGPT_CONNECTOR_SETUP.md` (ChatGPT-side coordinator role) — rule 14 priorities + rule 15 coder obligation are the paired rules |
| 20 | This file § rule 20; `docs/CONTROL_CENTRE_MVP_SPEC.md` § all-idle notification handoff; `apps/mobile/app/admin-dev.tsx` § Owner alerts (in-app banner already shipped); `docs/MCP_PHONE_CONTROL_CENTRE.md` (notification surface integration) — paired with rule 19 |
| 21 | This file § rule 21; `docs/HUMAN_APPROVAL_GATE_SPEC.md` (canonical full spec); `docs/CONTROL_CENTRE_MVP_SPEC.md` § approval centre integration; `docs/BACKLOG_AUTOMATION_SYSTEM.md` § approval-gated lanes — paired with rule 7 (EAS cost control), rule 18 (action ledger), rule 20 (push surface) |
| 22 | This file § rule 22; `docs/AI_SPEND_GATES_SPEC.md` (canonical full spec) — paired with rule 7 (cost control), rule 21 (approval gate state machine + push wiring), `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md` (privacy floor) |
| 23 | This file § rule 23; `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` (canonical full spec) — paired with rule 7 (cost control), rule 9 (provisional health claims), rule 21 (approval gate state machine), rule 22 (AI-spend ladder; `deep_research_external` cost class) |

## How the rules surface in MCP / control-centre

| Surface | Carries the rules |
|---|---|
| `/mcp/v2` `tools/call name="project.get_operating_rules"` | No Auth. Returns `{ schemaVersion, generatedAt, rules: [{ id, title, body }, …] }`. |
| `/api/control_centre` (admin token) | Snapshot includes an `operatingRules` field: `{ count, ids: [1..23], titles: [...] }` (titles only; full body via the dedicated MCP tool). |
| `docs/OPERATING_RULES.md` (this file) | Authoritative full-body text. |

Consumers MUST cross-check the count + ids against this file.
A rule disappearing or reordering is a regression that the live
integration test will flag.

## Anti-rules

- **No coder-side rule edit without a doc commit.** Even
  rephrasing for clarity is a doc commit reviewed alongside
  the Worker constant change.
- **No silent rule deletion.** Removing a rule requires a
  Lane-3 batch (`docs/BACKLOG_AUTOMATION_SYSTEM.md` § Lane 3)
  with Aaron's written approval.
- **No surfacing the rules without ID.** Every rule has a
  stable id 1..23; consumers reference rules by id, not by
  string match.
- **No moving rule text into private surfaces.** These rules
  are public-safe by design — they describe coder discipline,
  not project internals.

## Cross-references

- `docs/APP_DEVELOPMENTS.md` Hard guardrails — top-level
  invariants that frame these operating rules.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` — three-lane risk model
  + the EAS cost rule + status wording.
- `docs/FEEDBACK_SUGGESTIONS.md` — candidate workflow +
  build-readiness parallel scale.
- `docs/POST_MCP_PRODUCT_LANES.md` — Lane A / Lane B gating
  for health reliability + readiness UI.
- `docs/MCP_CANONICAL_STATE.md` — why Apple Notes / website
  MCP are not canonical for this codebase's state.
