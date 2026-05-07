# Backlog automation system

How Aaron + the AI runners (ChatGPT, Claude Code, Codex) work
through the backlog quickly without making unsafe changes. Three
lanes: safe autopilot, build autopilot with confirmation, human
approval required.

Companion to `APP_DEVELOPMENTS.md` (the active priorities),
`IN_APP_DEV_BACKLOG_PLAN.md` (the structured backlog),
`CONNECTOR_BACKLOG_TOOLS_PLAN.md` (the connector tools),
`CONNECTOR_SECURITY_MODEL.md` (the invariants),
`FEEDBACK_PRIORITY_MODEL.md` (the priority ladder),
`AGENT_AUDITS.md` (frozen historical audit text), and
`FEEDBACK_SUGGESTIONS.md` (deduped candidates awaiting Aaron approval).

Updated 2026-05-07.

## Source of truth

Repo docs are the source of truth for backlog and roadmap state:

- `docs/APP_DEVELOPMENTS.md` — active top priorities and manual
  owner steps.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` — how items move through
  capture, triage, prompt, coding, terminal bridge result, Aaron
  approval, and done/return.
- `docs/MCP_PHONE_CONTROL_CENTRE.md` — phone-first runbook for
  the MCP connector/control-centre read path.

Apple Notes is stale for planning. It remains a human scratchpad
for rough thoughts only. A note does not become backlog until it
is copied into the repo-backed flow or captured in Admin/Dev.

## MCP-first operating rule

Before starting any new task, every Claude / Codex / Agent /
ChatGPT worker must check MCP / control-centre state first:

1. `get_work_status`
2. `list_pending_suggestions`
3. `get_automation_state`
4. `get_handoff`
5. `/api/control_centre` if available

The worker must then report the MCP state, freshness/staleness,
chosen next task, and whether terminal / control-centre fallback
was needed. If MCP is stale, the worker must say "MCP stale", use
the latest terminal / control-centre state as fallback, and keep
MCP canonical sync as a priority.

## Three lanes

### Lane 1 — Safe autopilot (no confirmation)

Runs without owner approval. Items in this lane:

- Documentation edits inside `docs/`.
- Copy fixes that don't change product semantics (typos, label
  capitalisation, body-text clarification).
- Small UI fixes that don't change navigation, change permission
  prompts, or move tabs around.
- Backlog triage (move items between status enums per the
  ladder, set `triaged`, suggest priority, set `needsReview`).
- Prompt generation via the existing template bridge (no API).
- Status updates: writing CHATGPT_STATUS blocks, refreshing the
  `Now` chips in Admin/Dev to match the workflow store.
- `tsc --noEmit` runs and reading their output.

Bound: every Lane-1 item lands as a regular commit + push on
`main`. Reverts are easy via `git revert`.

### Lane 2 — Build autopilot with confirmation

Requires explicit owner confirmation in chat or in Admin/Dev
before running. Items in this lane:

- App patches that change behaviour (state machine edits, store
  schema additions, new components, route guards).
- Triggering predefined GitHub Actions workflows (`mobile-
  typecheck`, `release-audit`, `backend-smoke`, `android-aab-
  build`, `ios-testflight-build`, `ota-diagnostic`).
- Tester build dispatches (Android Internal Testing, iOS
  TestFlight) — these cost EAS credits and ship to real testers.
- Backend route additions that match the existing auth model.
- Schema-equivalent edits to durable stores
  (`owner-backlog-store.ts` field additions).

Bound: confirmation is a human "yes" in chat or a tap on the
Admin/Dev confirm Alert. The runner names the cost (e.g. "EAS
build credit") in the confirm copy.

### EAS build cost control rule

Coders may mark a feature or patch
`Implementation-complete, awaiting Agent functional confirmation`
when code is committed, typecheck/tests pass, no obvious blockers
remain, and the expected behaviour is clearly described.

They must not request, trigger, or recommend a new EAS/tester build
yet. A new EAS build is allowed only after all are true:

1. Agent performs a functional audit of the completed change.
2. Agent confirms the change is worthwhile to test on-device.
3. The change is bundled with other meaningful mobile changes where
   possible.
4. Typecheck/tests pass.
5. Aaron explicitly approves the EAS build.

Default:

- no EAS build
- no tester build
- no "quick build to check"
- no build for docs/backend/MCP-only changes
- no build for tiny copy/UI tweaks unless bundled

Use instead:

- mobile typecheck
- unit tests
- local inspection
- simulator/dev-client if already available
- Admin/Dev MCP status
- Agent audit confirmation

Every generated Claude / Codex / Agent prompt that mentions build
or tester-build work must include: "Do not run EAS builds unless Agent has confirmed a worthwhile on-device change and Aaron approves."

Every generated Claude / Codex / Agent / ChatGPT prompt must also
include the MCP-first operating rule above before the task body.

Use these build-gate statuses:

- `Implementation-complete, awaiting Agent functional confirmation`
- `Agent-confirmed, ready for Aaron build approval`
- `Aaron-approved for EAS build`
- `Built/tester-ready`

Do not call user-facing mobile work `fully complete` until Aaron has
tested or approved it.

### Lane 3 — Human approval required

Runner cannot do these autonomously, period. Items in this lane:

- Production releases (Play production track, App Store public
  release).
- Billing / membership / payments code paths (IAP product setup,
  Stripe, Shopify, entitlement promotion).
- Paid AI API usage (any call that incurs OpenAI / Anthropic /
  Google charges).
- Supabase database pushes / migrations.
- Raw health data edits (mutations to `normalized_daily_metrics`,
  `raw_source_events`, athlete artifacts).
- Stable athlete-memory promotion (moving a memory candidate to
  permanent state).
- Privacy / legal / store-listing declarations (Privacy policy
  copy, Data safety questionnaire, Health Connect declaration,
  App Tracking Transparency text).
- Deletion / archive of major backlog sections.
- Token rotation (Railway env, EAS, GitHub PAT).
- Public-facing copy on the website.

Bound: human signs off in writing (chat reply, commit message
co-authored by Aaron, or a doc commit).

## Structured backlog item shape (target)

Mostly already in `apps/mobile/src/store/owner-backlog-store.ts`.
Spec for the next iteration extends fields per
`IN_APP_DEV_BACKLOG_PLAN.md`:

```ts
interface BacklogItem {
  id: string;
  title: string;
  details: string;
  source: 'owner' | 'tester_feedback' | 'connector';
  type: BacklogType;
  priority: number;            // 1–11 ladder
  platform: 'ios' | 'android' | 'both';
  status: BacklogStatus;
  riskLevel: 'low' | 'medium' | 'high';   // NEW — drives lane choice
  approvalRequired: boolean;   // NEW — true when riskLevel === 'high'
  blocker?: string;            // already present
  needsBuild: boolean;         // NEW — true when item must ship in a paired build
  verification?: string;       // NEW — what to check on tester device after build
  canAutoRun: boolean;         // NEW — true when Lane 1 can pick it up without ask
  createdAt: string;
  updatedAt?: string;
  // (other fields per IN_APP_DEV_BACKLOG_PLAN.md)
}
```

Risk-level mapping (default per type):

| Type | Default riskLevel | Default lane |
|---|---|---|
| `bug` (small UI / copy) | low | 1 |
| `bug` (state / persistence / auth) | medium | 2 |
| `ux_issue` | low | 1 |
| `feature_idea` | medium | 2 |
| `release_blocker` | medium | 2 |
| `health_data_issue` | medium | 2 |
| `ai_coaching_idea` | high (gated on AI provider impl) | 3 |
| `monetisation_payment_idea` | high | 3 |
| `railway_backend_issue` | medium | 2 |
| `source_integration_issue` | medium | 2 |

The runner can override `riskLevel` upward but not downward.
`approvalRequired` follows `riskLevel === 'high'`.

## Backlog workflow loop

Every backlog item moves through the same explicit loop. The
source can be tester feedback, in-app audit events, an Aaron note,
or a connector observation, but the promotion path is identical:

1. **Capture** — feedback / audit / Aaron note / connector status
   becomes a candidate item. Raw logs, secrets, and raw health
   values are never copied into the item.
2. **Triage** — assign type, platform, risk level, owner lane,
   verification, and whether the item needs a tester build.
3. **Prompt** — generate a deterministic Claude / Codex prompt
   from the triaged item. Prompt generation is read-only; it does
   not execute code or call a paid AI API.
4. **Coder work** — Claude or Codex works only inside the lane's
   allowed ownership boundary and reports files changed,
   verification, blocker, and next step.
5. **Terminal bridge result** — the local tmux bridge records a
   compact, sanitized lane result into `coder_lanes` /
   `terminal_summary`. It never stores raw pane logs and never
   executes terminal text.
6. **Aaron approval** — Aaron reviews the result in chat or
   Admin/Dev. High-risk / Lane-3 items require explicit written
   approval before they move forward.
7. **Done or return to backlog** — if verified, mark done and
   keep the result in history. If incomplete, blocked, or failed,
   return the item to backlog with the blocker and next prompt.

No item is removed from the backlog solely because a coder claims
it is done. Removal / archive requires Aaron approval or an
explicit doc commit that names why the item is complete.

Functional-result rule: do not remove an item from the active
backlog until Aaron approves the functional in-app result. Passing
typecheck, committing code, or seeing a green workflow is not
enough when the item is user-facing. If Aaron has not confirmed
the app behaviour on the relevant screen/device, mark the item
`repo_only`, `built`, `needs_review`, or `blocked` and keep it in
the backlog.

## Coder report contract — rule 12

Updated 2026-05-07 against
`CLAUDE-WRITEBACK-CADENCE-RULE-12-FINALIZE-01`. Every coder
output (Claude / Codex / Agent) MUST open with the three
explicit fields below. They make the canonical-store
writeback discipline visible at a glance, so Aaron doesn't
have to ask "did you actually update MCP?" between turns.

```
PROMPT-ID: <id>
Status: DONE / PARTIAL / BLOCKED

MCP update attempted: yes / no
Bridge snapshot run:   yes / no
Stale reason if blocked: fresh | no_writeback | env_missing | unreachable | n/a

<existing report fields>
```

Field rules:

- **MCP update attempted** — `yes` if any of `bridge:snapshot`,
  `project.update_work_status`, or Supabase MCP `execute_sql`
  ran with the intent of refreshing canonical state during
  this session. `no` requires a one-line reason on the next
  line (e.g. "no — read-only audit, no state change to
  write").
- **Bridge snapshot run** — `yes` if `npm run bridge:snapshot`
  specifically ran and exited with code 0 during this session.
  `no` covers everything else (didn't run, ran but failed, ran
  via an alternative writer).
- **Stale reason if blocked** — copy the
  `freshness.staleReason` enum from the most recent
  `project.get_current_state` reading. `n/a` is acceptable
  only when the work is read-only and Aaron didn't ask about
  freshness.

These three fields are mandatory in every output, regardless
of prompt size or scope. They override any older report
template that omitted them.

## Agent role boundary

Agent is an app UX audit worker only. Its job is to inspect normal
tester screens, identify clutter/regressions, and produce focused
UX cleanup prompts or small mobile UI patches when explicitly
assigned. Agent must not own backend deploys, MCP auth/OAuth,
Supabase migrations/secrets, build dispatches, billing, health
source logic, or app version/build bumps.

## UX / IA placement rule

Daily and frequent workflows belong in the relevant feature tab.
Rare, admin, configuration, and debug workflows belong in Settings
or Admin/Dev.

Current placement defaults:

- Health owns nutrition targets, health-source status, source
  management, and sync/storage actions.
- Train owns weekly schedule, training plans, and session logging.
- Settings owns account, subscription, app version/build,
  notifications, permissions, support/feedback, and hidden
  Admin/Dev access.
- Admin/Dev owns diagnostics, connector/control-centre status,
  build/runtime detail, audit summaries, and prompt handoffs.

If a daily workflow appears in Settings, move it to the feature
tab unless doing so would require a risky rewrite. If debug copy
appears on a normal tester screen, hide it behind Admin/Dev or a
gated diagnostics disclosure.

## Bundle generator

The Prompt bridge in Admin/Dev already produces deterministic
prompts from `OwnerWorkflowContext`
(`apps/mobile/src/services/prompt-templates.ts`). Extending it
into a "task-bundle generator" means adding template variants
that consume a list of backlog item IDs:

```ts
buildTaskBundlePrompt({
  context,                      // existing OwnerWorkflowContext
  selectedItemIds,              // array of backlog ids
  laneOwnership,                // 'lane1' | 'lane2' | 'lane3'
  stopConditions,               // free text or []
}): string
```

Output shape (deterministic; no LLM):

```
PROMPT-ID: BUNDLE-{lane}-{idStamp}
TYPE: {runner}
LANE: {laneOwnership}

NON-NEGOTIABLES
- {protectedRules from context}
- {lane-specific limits}

CURRENT PRIORITY
{currentPriority}

TASK BUNDLE
{numbered list of selected items with title + details + verification}

VERIFICATION
- npx tsc --noEmit in apps/mobile
- {item.verification | join('\n- ')}

STOP CONDITIONS
- {stopConditions or default safeguards}

OUTPUT
End with a CHATGPT_STATUS_START / CHATGPT_STATUS_END block
covering: live / repo-only / blocked / verified / next.
```

Out of scope for this batch — the function shape is documented;
implementation lands when the connector reads
`/admin/backlog` and the in-app Quick capture has more items
worth bundling.

## First safe health-source bundle (live)

Health source basics shipped via prior tester builds:

- ✅ Apple Health primary on iOS, Health Connect primary on
  Android — un-gated from free tier (commit `d4827ba`).
- ✅ Apple Health does not appear on Android, Health Connect
  does not appear on iOS — `Platform.OS` gates in `health.tsx`.
- ✅ No raw WHOOP/Polar backend JSON in normal Health UI —
  `friendlyDirectSyncError()` helper (commit `a036fd5`).
- ✅ WHOOP/Polar under "More sources" disclosure — Health tab
  structure.
- ✅ Manual check-ins / training logs remain available — Train
  tab is BLE-state independent.

Per-build verification still happens after each paired tester
dispatch. The current paired build line is whatever Admin/Dev
reports on the Now / Android / iOS cards.

## MCP / Cloudflare bridge automation (live, Priority 1)

Added 2026-05-07. The MCP terminal bridge is now Priority 1 per
`APP_DEVELOPMENTS.md` and adds a new lane-1 pattern: read-only
status routes that any agent / mobile-app card can poll.

Live components:

- Cloudflare Worker `lauburu-mcp-preview` — five admin-token-gated
  connector routes (`/api/work_status`, `/api/coder_lanes`,
  `/api/build_status`, `/api/handoff`, `/api/terminal_summary`).
- Local tmux bridge — `npm run bridge:snapshot` writes the four
  connector artifacts under `data/agent-status/lanes/`. Read-only
  on tmux + git; no shell from pane content.
- Live integration test — `npm run mcp:test:live` against the
  deployed Worker.

Lane fit:

- The bridge snapshot script and the schema test are **Lane 1**
  (safe autopilot — read-only, no commits other than the JSON
  artifacts which are gitignored).
- Adding new MCP-shaped routes / new Supabase columns is **Lane
  2** (build autopilot with confirmation — schema-equivalent
  edit).
- Setting `SUPABASE_SERVICE_ROLE_KEY` on the Worker, applying the
  Supabase migration, or rotating any of the connector secrets
  is **Lane 3** (human approval required).

## Admin/Dev automation surface

Already exposes most of what's needed:

- "Now" chips: currentPriority / currentBlocker (or proof-result)
  / nextAction. Wired to `useOwnerWorkflowStore`.
- "Primary actions" section: Build Android + upload, Build iOS
  + submit, Run typecheck, Run release audit. Each with a
  confirm Alert that names the cost.
- "Prompt bridge": six deterministic templates including the
  Codex prompt, Claude Code prompt, ChatGPT status prompt,
  terminal-check prompt.
- "Quick capture" / Backlog: local owner backlog items.
- "Open shortcuts": Termius / GitHub Actions / EAS / Play /
  ASC.

Next iteration (not in this batch):

- "Run next safe bundle prompt" button that selects the top
  Lane-1 backlog items and emits a bundle prompt via the
  generator above.
- Approval-required items section that lists items with
  `approvalRequired: true` so the owner sees what's gated.

## Stop conditions for the runner

The runner stops without committing when:

1. tsc errors after the runner's edits (rolls back the edit,
   reports the error, asks for input).
2. A workflow dispatch returns non-2xx.
3. A doc edit collides with an existing pinned section
   (frontmatter `pin: true`).
4. The runner's planned action falls into Lane 3 without
   approval.
5. A test (when tests exist) fails in CI.
6. The runner detects a write that would leak a secret per
   `CONNECTOR_SECURITY_MODEL.md`.

In all stop cases, the runner emits a CHATGPT_STATUS block
naming the stop condition and the next required human action.

## Out of scope for tonight

- Implementing the bundle generator function (spec'd; implement
  when there's a real bundle of items to test it against).
- Backend `/admin/backlog` route (route shape reserved in
  `/admin/work-status.reserved.backlogReadRoute`).
- Auto-promote of `tester_feedback` records to backlog rows
  (Option A: derived view, no double-write).
- Any Lane 3 work (gated by definition).
