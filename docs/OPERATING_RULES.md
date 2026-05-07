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
obsolete ones.

This doc is the source of truth. The Worker constant in
`cloudflare-worker/src/operating-rules.ts` is the **mirror** —
when the doc changes, the constant must change in the same
commit, and the live test asserts the two stay in sync (count +
hash of the rule strings).

Updated 2026-05-08.

## The seventeen rules

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
11. **MCP-first start.** Before starting any new task, every
    coder / agent / ChatGPT MUST check the MCP / control-centre
    state. Required check order:
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
    If MCP is stale, say "MCP stale", use the latest
    terminal / control-centre state as fallback, AND continue
    fixing MCP canonical sync as a priority. Never start from
    memory, Apple Notes, screenshots, or old docs unless the
    MCP / control-centre is unavailable.
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

## How the rules surface in MCP / control-centre

| Surface | Carries the rules |
|---|---|
| `/mcp/v2` `tools/call name="project.get_operating_rules"` | No Auth. Returns `{ schemaVersion, generatedAt, rules: [{ id, title, body }, …] }`. |
| `/api/control_centre` (admin token) | Snapshot includes an `operatingRules` field: `{ count, ids: [1..17], titles: [...] }` (titles only; full body via the dedicated MCP tool). |
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
  stable id 1..17; consumers reference rules by id, not by
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
