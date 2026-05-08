# Push approval automation — the highest-leverage workflow

The synthesizing doc. Captures the **end state** Aaron is
optimising for: every long-running automation runs to
completion on its own except where Aaron's explicit decision
is required. Where decisions are required, Aaron taps
**Approve / Defer / Deny** on a lock-screen push notification
on his iPhone. No laptop, no Termius, no manual command typing.

This doc does NOT redefine any of the underlying mechanisms.
It synthesizes the existing rule + spec surfaces into the
single operator view, and adds the missing pieces that span
multiple gate types (lock-screen action design, app-open
fallback, automation-resume contract, single Admin/Dev
approval centre).

This is **doc only**. No app code. No EAS build.

## 0. Goal + relationship to existing specs

The end-state Aaron is optimising for: **automation pauses
ONLY for Aaron's approval/denial.** Everything that can be
deterministic / cached / pre-validated runs to completion
without intervention. Approval gates surface as push
notifications with inline actions. The Admin/Dev approval
centre (single surface) shows every pending gate, every
deferred gate, and every recent decision.

The mechanics are already specified across 4 existing docs +
5 operating rules. This doc is the **operator-view synthesis**.

| Existing spec | Role |
|---|---|
| Operating rule 20 | All-idle notification — fires when all 3 lanes idle (operator nudge to feed prompts). |
| Operating rule 21 | Human-approval push gate — base state machine: `waiting_for_approval` → `approved` / `deferred` / `expired` / `blocked`. |
| Operating rule 22 | AI spend gate — `expensive_ai` requests use rule 21. |
| Operating rule 23 | Deep research offload + cache — `deep_research_external` requests use rule 21 + cache; the same approval flow. |
| `docs/HUMAN_APPROVAL_GATE_SPEC.md` | Canonical approval-gate state machine + ledger schema + push UX. |
| `docs/AI_SPEND_GATES_SPEC.md` | Cost classes + per-call spend gate UX. |
| `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` | 10-state research-job lifecycle + import-back parser. |
| `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 | Push notification wiring (Codex handoff). |
| `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` | Release gate's role in the approval set (gate types involving real-device QA). |
| `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` | Operator audit decision tree triggered by some gate types. |
| `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 3 | Admin/Dev tab field requirements; this spec lists the new fields the approval centre adds. |

If you're implementing — read the spec doc for that gate type
first; this synthesizing doc is for the operator who needs to
understand "what does the workflow feel like" not the engineer
who needs the field-level contract.

## 1. Approval gate model — the single state machine

Every approval gate, regardless of what's being approved
(EAS build, Worker deploy, Supabase migration, AI spend,
research offload, FS-XXX release promotion, public release),
uses the same state machine from rule 21 + spec § 1:

```
              ┌───────────────────────┐
              │ waiting_for_approval  │
              └──┬──────┬──────┬──────┘
                 │      │      │
       ┌─────────┘      │      └─────────┐
       │                │                │
       ▼                ▼                ▼
   approved          deferred          blocked
       │                │                │
       │                │                │
   resume         re-fire after     close gate;
  automation     deferred_until     follow-up
                                   prompt required
                 ┌──────────────┐
                 │   expired    │ ──► (auto → blocked)
                 └──────────────┘
```

Research-job gates extend this with 4 additional states
(`running` / `imported` / `cached` / `stale`) for the
post-approval external-AI workflow — see rule 23.

The advantage of one state machine across all gate types: the
operator learns it once, the Admin/Dev approval centre is one
panel, the push payload format is one schema.

## 2. Lock-screen notification actions

iOS notification categories let us declare up to 4 inline
actions per push. The action set matches the gate's cost
profile:

| Gate type | Inline actions | Defer default |
|---|---|---|
| Standard human-approval gate (rule 21) | Approve / Defer / Deny (= block) | 24h |
| AI spend gate `expensive_ai` (rule 22) | Approve / Defer / Export prompt / Ignore | 24h |
| AI spend gate `deep_research_external` (rule 22 + 23) | Approve / Defer / Copy prompt / Import result | 24h |
| All-idle nudge (rule 20) | Open Admin/Dev (no Approve/Deny — it's a nudge, not a gate) | n/a |

iOS quirks to honour:

- **Inline action visibility on the lock screen** depends on
  the user's Settings → Notifications → Lauburu setting.
  Aaron should set: Allow Notifications ON, Lock Screen ON,
  Banner Style "Persistent" (so the notification stays
  visible until acted on), Action buttons enabled.
- **Critical alerts** are NOT used (those require a special
  entitlement and are reserved for health/safety alarms).
  Approval gates are normal-priority pushes that respect
  Focus Modes.
- **Focus Mode break-through:** Aaron may opt-in to a
  "Lauburu approvals can break through Focus" toggle in the
  app's Notification Settings panel. Default OFF (respect
  Focus); Aaron flips ON for time-critical batches like
  EAS-build approval windows.
- **App badge:** the badge count reflects pending approvals
  ≤7 days old. Older pending gates have already auto-flipped
  to `expired` per rule 21 and don't badge.

## 3. Fallback if iOS requires opening app

iOS can demand the app be opened in two cases:

1. **Notification action requires authentication.** When the
   user has FaceID-on-Notifications enabled, tapping an
   action button surfaces "Open Lauburu to verify your
   identity". Tap once → FaceID → returns to lock screen
   with the action carried out.
2. **Notification grouping collapsed.** When multiple gates
   are pending, iOS may group them — the user must tap to
   expand before action buttons are visible.

Fallback flow when push action can't complete on lock screen:

1. Tap notification → app opens → lands on Admin/Dev
   approval centre filtered to the specific gate id (deep
   link `lauburu://admin-dev/approval-centre/<gateId>`).
2. Same Approve / Defer / Deny / Export / Import actions,
   rendered as full-size buttons in-app.
3. Same write path under the hood (admin-token-gated MCP
   tool call). The push payload's `data.deepLink` field
   carries the URL.

If Aaron is offline (no network):

- Tapping Approve queues the action locally; the app shows
  "Will sync when online".
- On reconnect, the queued action is replayed via the MCP
  tool. The action ledger captures `pendingSync: true` until
  the round-trip completes.
- Aaron sees a small toast confirming sync.

If the app is uninstalled / deleted:

- Push notifications stop firing for that device's expo
  token.
- All pending gates remain `waiting_for_approval` server-side
  until Aaron re-installs OR until `expiresAt` (default 7
  days) when they auto-`blocked`.

## 4. Admin/Dev approval centre — single surface

One panel in `apps/mobile/app/admin-dev.tsx` shows every
pending gate across all categories, plus deferred / approved
/ blocked recent decisions for audit.

```
┌─ Approval centre (admin-only) ─────────────────────┐
│                                                    │
│ Waiting (3)                                        │
│  ⚠ EAS Android v21 build approval                  │
│    Why: deducts 1 build credit · 88% used          │
│    Default: No build · Expires: 2026-05-16 09:30   │
│    [ Approve ]  [ Defer 24h ]  [ Deny ]            │
│                                                    │
│  ⚠ AI: 7-day journal summary (~$0.85)              │
│    Default: Defer · Cost class: expensive_ai       │
│    [ Approve ]  [ Defer ]  [ Export prompt ]       │
│                                                    │
│  ⚠ Research: BPC-157 mechanism deep research       │
│    Default: Export · Cost class: deep_research_ext │
│    [ Copy prompt ]  [ Import result ]  [ Defer ]   │
│                                                    │
│ Deferred (2)        ▸                              │
│ Approved last 7d (5) ▸                             │
│ Blocked / expired (3) ▸                            │
│ All-idle nudges last 24h (4) ▸                     │
│                                                    │
│ [ Settings: push permission · Focus break-through  │
│    · default expiry · default deferral             │
│    · per-category enable/disable ]                 │
└────────────────────────────────────────────────────┘
```

Tap-handlers map directly to the existing MCP tools per the
4 specs:

- Standard gate: `project.update_approval_gate(gateId, action, reason?)` (rule 21).
- AI spend gate: `project.update_ai_spend_gate(gateId, action)` (rule 22).
- Research job: `project.update_research_job(jobId, action)` + `project.research_artifact_import(jobId, rawText)` (rule 23).
- Idle nudge: dismissed locally (no server-side state).

The approval centre is the **canonical write path** —
notification actions are convenience; tapping them dispatches
the same MCP write. Aaron's mental model: push tells me
something needs me; lock-screen action is the fast path;
approval centre is the full surface.

## 5. Automation resume contract

When a gate flips to `approved`, the automation that was
paused MUST resume from the EXACT next step. The resume
contract:

1. **Every gate has a `resumeContext`** in its ledger row —
   a structured pointer to the action that should run on
   approval. Example for an EAS build gate:
   ```json
   {
     "type": "eas_build",
     "platform": "android",
     "profile": "production",
     "versionCodeBumpFrom": 20,
     "versionCodeBumpTo": 21,
     "commitMessage": "QA: bump Android versionCode to 21 for ..."
   }
   ```
2. **The Worker (or coder, when laptop-side) consumes
   `resumeContext`** when the gate flips to `approved`.
   Worker-side resume happens for all-Worker actions (e.g. a
   public-tool unlock); coder-side resume happens for actions
   that need laptop access (EAS build dispatch, git commit,
   wrangler deploy).
3. **No "approved but nothing happened" states.** If the
   resume action fails, the ledger row carries a
   `resumeError` field and the gate flips to `blocked` with
   reason `resume_failed: <details>`. Aaron sees the failure
   on the next push round.
4. **Idempotent resume.** A gate that's already `approved`
   and consumed must not double-fire. The ledger has
   `consumedAt` set on first successful resume; subsequent
   reads ignore it.
5. **Audit trail.** Every resume writes a state-transition
   row with actor (`worker`, `claude`, `codex`, `aaron`),
   timestamp, evidence link.

For deferred gates: when `deferred_until` elapses, the gate
re-fires push (per rule 21). The ledger row's
`pushHistory[]` accumulates each fire; the throttle (rule 21
§ 3.3) prevents over-firing.

## 6. Safety rules per category

The hard floor — what types of action MUST require Aaron's
approval before proceeding. Pulled from the existing rule
bodies; reproduced here as the operator-view summary.

| Category | Approval required | Cross-rule | Notes |
|---|---|---|---|
| **Production app release** (App Store / Play Production) | YES — every release. | Rule 7 + rule 8 + rule 21. | Release approval is BOTH an approval gate AND a "no fully-done without Aaron" gate. |
| **EAS build** (any platform, any profile that costs credits) | YES — every build. | Rule 7 + rule 21. | Internal-tester builds count too. Default expiry 24h; defer-aware. |
| **Cloudflare Worker production deploy** | YES — when promoting to top-level / production env. | Rule 7 + rule 21. | Preview deploys (`*.workers.dev`) NO unless they're being promoted to prod. |
| **Supabase migration on the production project** | YES — schema changes touching live data. | New per rule 21. | Read-only migrations may be exempt; Codex / Claude judges. |
| **Destructive Supabase mutation** (DROP, TRUNCATE, mass UPDATE) | YES. | New per rule 21. | Per-row updates from the bridge are exempt. |
| **Force-push to main / git reset --hard on shared branches** | YES. | System git-safety rule + rule 21. | Local-only resets (e.g. soft-reset for fix-up) NO. |
| **Rotating shared secrets** (`ATHLETE_MEMORY_API_TOKEN`, Supabase service role) | YES. | New per rule 21. | Only Aaron has the credentials anyway; the gate ensures coordination + audit. |
| **Adding a new public MCP tool** | YES — Aaron approves the public surface change. | Rule 7 + connector-sanitisation rules + rule 21. | Internal admin-token tools NO unless they expose new data classes. |
| **AI spend `expensive_ai`** | YES — per call, gate respects the spend ladder. | Rule 22. | Default approval threshold $0.50/call (configurable). |
| **AI spend `deep_research_external`** | YES — and uses the artifact cache (no re-run if cached). | Rule 22 + rule 23. | Default action is "Copy prompt" (export to external AI). |
| **Publishing a `validated` technique to public 3D map** | YES — public-release-equivalent. | Rule 21 + `EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md` § 4. | Three transitions in technique evolution use this gate: suggested→approved_private, validated→instructional_ready, filmed→published. |
| **FS-XXX release promotion** | YES — moving from "Agent-confirmed" to "Aaron-approved for EAS build" or to public. | Rule 7 + rule 8 + rule 21. | The four-status sequence is mandatory; this is the third transition. |

What does NOT require an approval gate:

| Action | Why exempt |
|---|---|
| Doc edit | Standard Lane-1 / Lane-2; coder commits directly. |
| Worker preview deploy | Not production. |
| Local typecheck / test runs | Read-only. |
| `bridge:snapshot` / `project.update_work_status` | Already gated on rule 12 + admin token; covered by rule 18 ledger writeback. |
| Adding a new spec doc | Doc lane. |
| Local git commit (not push) | Coder lane; rule 2 governs. |
| `cheap_ai` calls within budget | Rate-limited per rule 22; metered into the budget but no per-call gate. |
| Cache hit on `deep_research_external` | Cited artifact, no re-run, no spend, no gate per rule 23. |

## 7. Installed-device QA requirements

Some approval gates open the door to a **real-device audit**
before they can be cleared. The release-gate is the canonical
example; FS-XXX functional confirmation is the second.

| Gate type | Real-device QA required? | Audit method |
|---|---|---|
| EAS build approval (pre-build) | NO — the build happens AFTER approval. The push only confirms it's worth burning credits. | n/a (pre-build sanity per Gate F in `INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` may run on the previous installed build, no new audit needed). |
| Release-gate clear (Android v20 install + retest) | **YES** — canonical Gate A. | iPhone Mirroring or screen-record per `INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` § 1. Records `agent_qa_result.json` `status=pass`. |
| FS-XXX functional confirmation | YES — Gate B. | Targeted simulator audit OR real-device audit depending on FS-XXX scope. |
| AI spend gate | NO — software-only. | n/a |
| Research offload gate | NO — software-only. | n/a |
| Worker / Supabase deploy | NO — server-side. | Smoke test on the live preview before promoting; no device involved. |
| Technique publishing | YES — `filmed` → `published` requires watching the filmed instructional through end-to-end. | Real-device playback audit. |

The audit-playbook decision tree (`docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md`)
governs how audits are run. This spec just records WHICH gate
types trigger them.

## 8. Codex handoff status

Implementation handoffs for the underlying mechanics are
already staged in their respective spec docs. This synthesis
doc does NOT add a new handoff — it lists the existing ones
in dependency order:

1. `CODEX-FS-XXX-ALL-IDLE-PUSH-NOTIFICATION-01`
   (`docs/CONTROL_CENTRE_MVP_SPEC.md` § 10) — push wiring
   foundation. Ships expo-notifications setup that everything
   else builds on.
2. `CODEX-FS-XXX-HUMAN-APPROVAL-GATE-IMPL-01`
   (`docs/HUMAN_APPROVAL_GATE_SPEC.md` § 6) — base approval-
   gate state machine + admin-dev approval centre + the
   `project.update_approval_gate` MCP tool.
3. `CODEX-FS-XXX-AI-SPEND-GATES-IMPL-01`
   (`docs/AI_SPEND_GATES_SPEC.md` § 6) — AI cost classifier +
   spend gate (uses gate from #2).
4. `CODEX-FS-XXX-DEEP-RESEARCH-OFFLOAD-IMPL-01`
   (`docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` § 7) — research-job
   lifecycle + cache + import parser (uses gate from #2 +
   spend ladder from #3).
5. `CODEX-FS-XXX-EVIDENCE-DRIVEN-TECHNIQUE-EVOLUTION-IMPL-01`
   (`docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md` § 7) —
   technique state machine that reuses gate from #2 for 3
   push-gated transitions.

When all 5 are dispatched (in order, each gated on Aaron's
explicit approval per rule 7) and shipped, the highest-leverage
push automation workflow is operational end-to-end.

The order matters: handoff #1 is the prerequisite for #2-#5;
#2 is the prerequisite for #3-#5. Codex should NOT skip
ahead.

## 9. Anti-rules

- **No silent approval.** Every state transition past
  `waiting_for_approval` MUST have Aaron's explicit action
  recorded in the ledger. No "presumed approved after 24h"
  — that's `expired`, which auto-`blocked`, not approved.
- **No bypass via direct MCP write.** Coders cannot mark a
  gate `approved` on Aaron's behalf even with admin token.
  Only Aaron's actorId may write `approved`.
- **No payload PII / token leak in pushes.** Same redaction
  surface as `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`.
- **No Critical Alerts entitlement.** Health-safety alarms
  only; not for app workflow approvals.
- **No badge inflation.** Badge counts pending ≤7d only;
  expired gates don't badge.
- **No Focus break-through by default.** Respect Aaron's
  Focus Mode unless he explicitly opts in.
- **No automation resume without `consumedAt`.** Approved
  gates that haven't been consumed must not double-fire on
  re-read.
- **No production release without explicit approval.**
  Reaffirms rule 7 + rule 8.
- **No EAS build without Agent-confirmed + Aaron-approved.**
  Reaffirms rule 7.
- **No installed-device QA bypass.** Real-device-required
  gates per § 7 must NOT be cleared on simulator-only or
  repo-only evidence (per `INSTALLED_DEVICE_QA_RELEASE_GATE.md`
  § Gate rule).

## 10. Cross-references

- `docs/OPERATING_RULES.md` § 7 / § 8 / § 11 / § 18 / § 20 /
  § 21 / § 22 / § 23 — all rules this synthesis sits on
  top of.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — canonical gate
  state machine + ledger schema.
- `docs/AI_SPEND_GATES_SPEC.md` — cost classes + per-call
  spend gate.
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` — 10-state research-
  job lifecycle.
- `docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md` —
  technique state machine (3 push-gated transitions).
- `docs/CONTROL_CENTRE_MVP_SPEC.md` § 10 — push wiring
  Codex handoff.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — release-gate
  real-device QA requirement.
- `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` — operator
  audit decision tree triggered by some gate types.
- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 3 —
  Admin/Dev tab field requirements; the approval centre is
  one of the named fields.
- `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (FS-019) —
  Supabase JWT + email allowlist auth model the approval
  centre uses.
- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § 5 — Aaron's
  remaining manual steps; this spec converts MOST of them
  into push-approval gates.
