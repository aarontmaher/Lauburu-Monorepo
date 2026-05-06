# Feedback suggestions — candidate workflow

Suggestions that have been deduped from `docs/AGENT_AUDITS.md`,
tester feedback, owner notes, and connector observations, but are
NOT yet active work. Each one waits here until Aaron explicitly
approves it.

Companion to:
- `docs/AGENT_AUDITS.md` — historical recovered audit text.
- `docs/BACKLOG_AUTOMATION_SYSTEM.md` — three-lane risk model
  + workflow loop.
- `docs/APP_DEVELOPMENTS.md` — active priority order; only
  approved items can land in the active priorities.
- `docs/FEEDBACK_PRIORITY_MODEL.md` — 1–10 priority ladder used
  once suggestions are approved.
- `docs/CONTROL_CENTRE_MVP_SPEC.md` — the iPhone surface that
  shows pending suggestion counts to Aaron.

Updated 2026-05-07.

## Aaron approval rule (PINNED)

**A candidate suggestion does NOT become active work until Aaron
explicitly approves it.** "Active work" means: appearing in
`docs/APP_DEVELOPMENTS.md` priorities, getting a coder lane
assignment, ingesting EAS credits, or modifying production state.
Approval is a written line in this file (`approval: <YYYY-MM-DD>
Aaron`) plus a commit. Coders and ChatGPT MUST treat any item
without that approval line as not-yet-actionable.

The mirror rule: **a completed item is NOT removed from the
backlog without Aaron functional approval.** A coder claiming
"done" is not enough — Aaron has to mark `approved_done` after
verifying on a tester device.

## Status enum

| Status | Meaning |
|---|---|
| `candidate` | Newly captured. Has not been triaged yet. |
| `needs_review` | A coder has read it; needs Aaron's eyes before promotion. |
| `approved_active` | Aaron has signed off. Promotable to active priority. |
| `in_progress` | A coder is working on it under one of the three lanes. |
| `blocked` | Cannot proceed without an external action (Aaron, vendor, dependency). |
| `needs_aaron` | Owner-action required (manual step). |
| `ready_for_aaron_test` | Coder claims done; awaiting Aaron's tester-device verification. |
| `approved_done` | Aaron has tested and confirmed. Safe to remove from backlog. |
| `rejected` | Aaron explicitly declined. Stays here as a no-redo marker. |
| `deferred` | Recognised value but not now; gated on a different priority. |

Coders may move items: `candidate → needs_review` (after triage),
`approved_active → in_progress` (after starting), `in_progress →
ready_for_aaron_test` (after coder-side verification),
`anything → blocked` (when blocked).

Coders MUST NOT move items: `* → approved_active`, `* →
approved_done`, `* → rejected`. Those transitions are Aaron-only.

## Workflow

```
[audit / tester feedback / owner note / connector observation]
              │
              ▼
       capture in AGENT_AUDITS.md (raw, frozen, source-labelled)
              │
              ▼
       dedupe + add to FEEDBACK_SUGGESTIONS.md
              │  status: candidate
              ▼
       coder triages
              │  may move to needs_review
              ▼
       Aaron reviews in chat or in Admin/Dev
              │  Aaron writes approval: line
              ▼
       status: approved_active
              │
              ▼
       coder picks up under correct lane
       (per BACKLOG_AUTOMATION_SYSTEM.md three-lane model)
              │  status: in_progress
              ▼
       coder finishes; status: ready_for_aaron_test
              │
              ▼
       Aaron verifies on tester device
              │  status: approved_done OR back to in_progress
              ▼
       removal from backlog (Aaron-only)
```

## Active candidates (awaiting approval)

Categories the most recent overnight prompt called out as the
current active candidate set. Each line below is a candidate, not
a commitment. Aaron's approval line lives in the per-item table
that follows.

| ID | Title | Category | Status | Notes |
|---|---|---|---|---|
| FS-001 | ChatGPT public MCP connector consistency | mcp | candidate | Tools list snapshotted at chat-start; some chats can't bind new tools. Diagnostic tool `get_public_mcp_health` shipped (commit `ce98f80`); doc `CHATGPT_CONNECTOR_SETUP.md` written. Active candidate scope: enforce a single canonical connector entry, document re-init steps, watch for ChatGPT-side regressions. |
| FS-002 | Duplicate / stale ChatGPT connector cleanup | mcp | candidate | Cleanup table is in `CHATGPT_CONNECTOR_SETUP.md` § 4. Active candidate scope: Aaron walks his ChatGPT settings, deletes the listed duplicates, leaves exactly one entry pointing at `…/mcp/public` with No Auth. |
| FS-003 | Admin/Dev iPhone first-screen control centre | admin_dev | candidate | Spec at `docs/CONTROL_CENTRE_MVP_SPEC.md` (commit `8d06042`). Active candidate scope: implement Phase 1 Worker route + Phase 3 mobile UI per the spec. Mobile UI is Codex's lane; Worker route is Claude's lane. No version bump. |
| FS-004 | App live MCP consumer in next tester build | mobile_release | candidate | Mobile already auto-appends `/api` and reads `EXPO_PUBLIC_MCP_BASE_URL`. Active candidate scope: set the env in EAS for the next paired build, dispatch from Admin/Dev → Primary actions, verify on tester device. NO version bump in this work. |
| FS-005 | Feedback suggestions approval workflow visible in Admin/Dev | admin_dev | candidate | The mobile Admin/Dev surface should display `candidateCount` and `awaitingApprovalCount` from the Control Centre snapshot per `CONTROL_CENTRE_MVP_SPEC.md`. Active candidate scope: backend (Worker) reads counts from a future `connector_backlog_items` table; mobile renders the section. Phase-2/Phase-3 work, gated on the Phase-1 Worker route landing first. |
| FS-006 | Health / Data Source reliability after MCP/AdminDev stabilises | health | candidate | Apple Health (iOS) + Health Connect (Android) reliability is Priority 2 in `APP_DEVELOPMENTS.md` and stays gated behind the MCP/AdminDev work. Active candidate scope: tester-device verification of cards visibility + missingness honesty. Health source logic itself is OUT OF SCOPE for the candidate intake — it goes through its own approval flow when MCP work stabilises. |

### Per-candidate approval log

Each candidate gets a row here when Aaron acts. Append-only.

```
FS-001 | (awaiting Aaron approval)
FS-002 | (awaiting Aaron approval)
FS-003 | (awaiting Aaron approval)
FS-004 | (awaiting Aaron approval)
FS-005 | (awaiting Aaron approval)
FS-006 | (awaiting Aaron approval)
```

When Aaron approves an item, the line becomes:

```
FS-XXX | approved_active 2026-MM-DD Aaron — note: <one line>
```

Coders never edit this log without an Aaron approval line above
the change.

## Foundation-done items (do not re-open as candidates)

Mirror of the "Foundation done" section in
`docs/AGENT_AUDITS.md`. Listed here so coders triaging this file
don't accidentally re-promote them:

- Supabase connector tables (`0003_connector_status_tables.sql`,
  applied).
- Local tmux bridge producer (`scripts/bridge-snapshot-lanes.sh`,
  live).
- Worker `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` secrets set.
- `/api/coder_lanes` returning real bridge data
  (`dataSource.source: supabase`).
- `/api/terminal_summary` returning real entries.
- Railway deprecated; Cloudflare Worker + Supabase is the active
  path.

If a new audit asks for any of these, link to the commit in
`docs/AGENT_AUDITS.md` § "Foundation done"; do not re-add to
the candidate set.

## How items leave this file

Two valid exit routes. Anything else is a coder-side error.

1. **Aaron approves and item ships.** When `approved_done` lands
   in the per-candidate approval log AND Aaron has tester-device
   verified, the row stays in this file under a "Closed" section
   (added when first row needs it) so the trail is preserved. It
   does NOT migrate into `APP_DEVELOPMENTS.md` once done — that
   doc tracks active priorities, not history.
2. **Aaron rejects.** `rejected` line in the approval log; row
   stays as a no-redo marker.

If a candidate becomes irrelevant (e.g. infrastructure fact has
moved on), it's marked `superseded by <commit-or-doc>` in the
notes column — never silently deleted.

## Anti-rules

- **No coder-side promotion to `approved_active` / `approved_done`
  / `rejected`.** Those are Aaron-only.
- **No silent deletion of candidates.** Every removal needs an
  approval-log line.
- **No app behaviour changes from candidate notes alone.** Only
  approved items can drive code changes.
- **No secrets, tokens, or raw terminal logs in candidate notes.**
  Same redactor rules as the rest of the connector pipeline.
- **No bypass of Lane 3 risk for "high-priority" candidates.**
  Risk lane is set per `BACKLOG_AUTOMATION_SYSTEM.md`; Aaron's
  approval doesn't change the lane, only the active/inactive
  status.
