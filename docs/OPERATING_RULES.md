# Operating rules — canonical

The rules every coder, agent, and consumer of this codebase
must follow. **Pinned and visible** — both as this doc and as
a tool exposed by the Worker MCP at
`project.get_operating_rules` (No Auth) AND as an
`operatingRules` field on `/api/control_centre`.

**Read rule 11 first.** "MCP-first" means: before starting any
new task, check the MCP / control-centre state. The other
ten rules govern HOW the work is done; rule 11 governs WHEN
to start it.

This doc is the source of truth. The Worker constant in
`cloudflare-worker/src/operating-rules.ts` is the **mirror** —
when the doc changes, the constant must change in the same
commit, and the live test asserts the two stay in sync (count +
hash of the rule strings).

Updated 2026-05-07.

## The eleven rules

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

## How the rules surface in MCP / control-centre

| Surface | Carries the rules |
|---|---|
| `/mcp/v2` `tools/call name="project.get_operating_rules"` | No Auth. Returns `{ schemaVersion, generatedAt, rules: [{ id, title, body }, …] }`. |
| `/api/control_centre` (admin token) | Snapshot includes an `operatingRules` field: `{ count, ids: [1..10], titles: [...] }` (titles only; full body via the dedicated MCP tool). |
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
  stable id 1..10; consumers reference rules by id, not by
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
