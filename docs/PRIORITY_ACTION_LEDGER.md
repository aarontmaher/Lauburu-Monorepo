# Priority/action ledger

This is the compact repo source for the current priority order and
deferred action ledger. The bridge publishes the structured copy from
`data/action-ledger/pending_actions.json` into `connector_handoff`.

Public MCP surfaces may expose only compact, redacted counts and the
next pending action. Full action detail belongs behind admin-gated
handoff/control-centre surfaces.

## Current priority order

1. Health connectivity Phase 1 mobile truth labels + installed-device
   QA gate.
2. FS-019 native iPhone/TestFlight automation controls with safe
   admin-gated actions.
3. FS-020 journal import parser/macros confirmation and UI handoff.
4. FS-021 lactate, Daily Dozen-style checklist, and
   nutrition/recovery pattern inputs.
5. P1 actionable home screen.
6. P2 Start Training / Drill Timer on home.
7. P4-P9 product decisions that need Aaron approval.
8. C1-C5 code-can-build graph support work.

Old website backlog items such as P1/P2 stay queued. They do not
outrank the active mobile health/release gate.

## Action ledger rules

Every prompt, action, goal, human step, coder step, Agent step, or AI
step remains recorded until evidence proves it is completed,
superseded, void, unsafe/rejected, or no longer necessary.

Each action record includes:

- `id`
- `owner`
- `targetWorkerOrPerson`
- `lane`
- `actionText`
- `triggerCondition`
- `status`
- `priority`
- `createdAt`
- `updatedAt`
- `evidenceSummaryOrLink`
- `voidReason`
- `supersededBy`

The current pending set covers:

- iOS build 19 dispatch result.
- Android versionCode 18 dispatch approval/result.
- installed-device QA after builds are available.
- Agent QA JSON writeback.
- FS-020 parser confirmation.
- B-20d journal import UI after parser confirmation.
- FS-021 health-input expansion scope approval/refinement.
- P1/P2 mobile home work after the health/release gate clears.

The stale "ChatGPT cannot call MCP v2" follow-up is voided because the
read path is live; no-auth writes remain blocked by design.

The top-level Worker Supabase secret action was completed after both
top-level and preview `/mcp/v2` returned `source: supabase`,
`freshness.staleReason: fresh`, and `isStale: false`.
