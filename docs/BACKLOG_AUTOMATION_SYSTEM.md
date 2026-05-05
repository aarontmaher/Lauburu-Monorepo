# Backlog automation system

How Aaron + the AI runners (ChatGPT, Claude Code, Codex) work
through the backlog quickly without making unsafe changes. Three
lanes: safe autopilot, build autopilot with confirmation, human
approval required.

Companion to `IN_APP_DEV_BACKLOG_PLAN.md` (the structured
backlog), `CONNECTOR_BACKLOG_TOOLS_PLAN.md` (the connector tools),
`CONNECTOR_SECURITY_MODEL.md` (the invariants), and
`FEEDBACK_PRIORITY_MODEL.md` (the priority ladder).

Updated 2026-05-06.

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

## First safe health-source bundle (already shipped on `main`)

The bundle the user prompt asks about is largely on `main`:

- ✅ Apple Health primary on iOS, Health Connect primary on
  Android — un-gated from free tier (commit `d4827ba`).
- ✅ Apple Health does not appear on Android, Health Connect
  does not appear on iOS — `Platform.OS` gates in `health.tsx`.
- ✅ No raw WHOOP/Polar backend JSON in normal Health UI —
  `friendlyDirectSyncError()` helper (commit `a036fd5`).
- ✅ WHOOP/Polar under "More sources" disclosure — already in
  the Health-tab structure.
- ✅ Manual check-ins / training logs remain available — Train
  tab is BLE-state independent.

In flight (already dispatched):

- 🟡 Android v15 build + Play upload (run `25384901407`,
  in_progress).
- 🟡 iOS Build 16 + TestFlight submit (run `25384907135`,
  in_progress).

Pending after device install:

- Verify Apple Health card visible to free-tier user on Aaron's
  iPhone post-Build 16.
- Verify Health Connect card visible to free-tier user on
  girlfriend's Android post-v15.
- Verify metrics surface or correctly say "missing".

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
