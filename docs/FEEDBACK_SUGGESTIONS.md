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

## Build-readiness wording (parallel scale)

The status enum above tracks **suggestion lifecycle**. A
parallel scale tracks **build-readiness lifecycle** for any
mobile-app candidate that needs to ship in an EAS build. Both
scales co-exist on a single candidate; coders MUST report both
when relevant.

| Build-status string | When | Who sets it |
|---|---|---|
| `Implementation-complete, awaiting Agent functional confirmation` | Code committed, tsc / tests pass, no obvious blockers, expected behaviour described. NOT yet build-ready. | coder (Claude / Codex) |
| `Agent-confirmed, ready for Aaron build approval` | Agent has run a functional audit and confirmed the change is worth testing on-device. | Agent |
| `Aaron-approved for EAS build` | Aaron has read the Agent confirmation and explicitly said "build it". | Aaron |
| `Built/tester-ready` | EAS build dispatched and the artefact is in TestFlight / Play Internal Testing. | Aaron / build workflow |

Coders MUST NOT skip a step (e.g. labelling a change
`Built/tester-ready` directly). Coders MUST NOT call mobile work
`fully complete`, `done`, or `shipped` — only Aaron can promote
to `approved_done` (suggestion-side) AND only Aaron-tested
on-device qualifies as "fully complete" (build-side). Until
Aaron tests, the longest-form build-status string is the only
correct phrasing.

Full body of the EAS build cost control rule lives in
`docs/BACKLOG_AUTOMATION_SYSTEM.md` § "EAS build cost control
rule" and `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` § "Safety
gates".

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
| FS-019 | Native iPhone automation controls from TestFlight app, not Expo-only | mobile-native-automation | approved_active | Aaron iPhone app request. Add a native/TestFlight-safe mobile control-centre path so Aaron can view live MCP project state and trigger only safe approved automation/control-centre actions from the installed iPhone app. Admin-gated, no exposed secrets, clear live/stale/fallback labels. Top active mobile priority above P1/P2. Spec at `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (FS-019 sub-batches B-19a..g). |
| FS-020 | Journal import + term normalization + macro ratio + personal insights (extends FS-018) | feature_idea | candidate | Per `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md`. Three new tables (`journal_term_normalizations` + `nutrition_daily_log` + `journal_imports`) + shared dictionary + research-snippets static files + 5-shape parser (Apple Notes / WHOOP CSV / Cronometer CSV / generic CSV / free-text) + term-confirmation modal + macro ratio derivation + 4-window pattern engine (same-day / next-day / rolling 3 / rolling 7) + DESIGN-ONLY cross-user aggregate (B-20h deferred). 8 sub-batches. NEVER causation claims; only `associated with`. `confidence: high` reserved. Lane 3 (DB + privacy). Codex handoff at § 11 (B-20a + B-20b paired). |
| FS-001 | ChatGPT public MCP connector consistency | mcp | candidate | Tools list snapshotted at chat-start; some chats can't bind new tools. Diagnostic tool `get_public_mcp_health` shipped (commit `ce98f80`); doc `CHATGPT_CONNECTOR_SETUP.md` written. Active candidate scope: enforce a single canonical connector entry, document re-init steps, watch for ChatGPT-side regressions. |
| FS-002 | Duplicate / stale ChatGPT connector cleanup | mcp | candidate | Cleanup table is in `CHATGPT_CONNECTOR_SETUP.md` § 4. Active candidate scope: Aaron walks his ChatGPT settings, deletes the listed duplicates, leaves exactly one entry pointing at `…/mcp/public` with No Auth. |
| FS-003 | Admin/Dev iPhone first-screen control centre | admin_dev | candidate | Spec at `docs/CONTROL_CENTRE_MVP_SPEC.md` (commit `8d06042`). Active candidate scope: implement Phase 1 Worker route + Phase 3 mobile UI per the spec. Mobile UI is Codex's lane; Worker route is Claude's lane. No version bump. |
| FS-004 | App live MCP consumer in next tester build | mobile_release | candidate | Mobile already auto-appends `/api` and reads `EXPO_PUBLIC_MCP_BASE_URL`. Active candidate scope: set the env in EAS for the next paired build, dispatch from Admin/Dev → Primary actions, verify on tester device. NO version bump in this work. |
| FS-005 | Feedback suggestions approval workflow visible in Admin/Dev | admin_dev | candidate | The mobile Admin/Dev surface should display `candidateCount` and `awaitingApprovalCount` from the Control Centre snapshot per `CONTROL_CENTRE_MVP_SPEC.md`. Active candidate scope: backend (Worker) reads counts from a future `connector_backlog_items` table; mobile renders the section. Phase-2/Phase-3 work, gated on the Phase-1 Worker route landing first. |
| FS-006 | Health / Data Source reliability after MCP/AdminDev stabilises | health | candidate | Apple Health (iOS) + Health Connect (Android) reliability is Priority 2 in `APP_DEVELOPMENTS.md` and stays gated behind the MCP/AdminDev work. Active candidate scope: tester-device verification of cards visibility + missingness honesty. Health source logic itself is OUT OF SCOPE for the candidate intake — it goes through its own approval flow when MCP work stabilises. |
| FS-007 | P0.3 — "Polar via hub" label propagation audit (mobile) | health_data_issue | candidate | Per `HEALTH_NUTRITION_READINESS_AUDIT.md` § 3 P0. Codex Phase-1 audit of every UI string + MCP response field that mentions Polar — confirm none say "Polar Direct" / "Polar live". Bundled with next mobile batch; NO standalone build. |
| FS-008 | P1.1+P1.2 — WHOOP OAuth callback off Railway → Cloudflare Worker + Supabase token storage | source_integration_issue | candidate | Per `HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.4. Lane-3 (DB + secrets); blocks on Aaron approval + Aaron pasting WHOOP client secret to Worker secret + WHOOP developer-console redirect URI update. After migration, WHOOP truth label flips to `seed/provisional` for ≥7 days before promotion to `live`. |
| FS-009 | P1.4 — Nutrition manual + photo path tester-verified on iPhone + Android | health_data_issue | candidate | Code is live; verification is the gate. Bundle with next mobile batch. NO build solely for this. |
| FS-010 | P1.5 — Mobile health-source label audit per `HEALTH_NUTRITION_READINESS_AUDIT.md` § 7 Codex prompt | ux_issue | candidate | Phase-1 audit of `IntegrationCards.tsx` / `HealthActionsPanel.tsx` / `health-source-ui.ts` strings against the six canonical truth labels. Codex's lane. ≤20 line changes per file. |
| FS-011 | P2.1–P2.4 — Grappler Readiness v1 batches B/C/D + provisional UI | feature_idea | candidate | Per `GRAPPLER_READINESS_PROTOTYPE_PLAN.md` + `HEALTH_NUTRITION_READINESS_AUDIT.md` § 6.2. Gated on FS-006 / FS-007 / FS-009 / FS-010 holding for ≥2 tester-build cycles. confidence: provisional floor; hedge language only. |
| FS-012 | P3.1 — Polar AccessLink (Polar Direct) OAuth wiring | source_integration_issue | candidate | Reserved label; vendor OAuth + token storage; bundled with WHOOP migration if practical. Lane 3. |
| FS-013 | P3.2 — Bluetooth HR sensor Phase-1 native scaffold | feature_idea | candidate | Per `BLUETOOTH_MVP_SPEC.md` § 11 Codex handoff prompt. Native scaffold ONLY (no UI, no schema). Train-session lane. |
| FS-014 | P3.3 — Generic conditioning file import (FIT / TCX / CSV) | feature_idea | candidate | `manual_imports` table accepts envelope; parser routing planned. Lane 2. |
| FS-015 | P3.5+P3.6 — Blood test + DEXA upload UI + storage | feature_idea | candidate | Per `DEXA_BLOOD_TEST_UPLOAD_PLAN.md`. Quarterly evidence; "context only — not medical advice" caption mandatory. Lane 2. |
| FS-016 | P3.7 — Journal upload (free-text, evidence only, never readiness input) | feature_idea | candidate | Per `HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.13. Per-user storage; never appears in MCP / connector. Lane 2. |
| FS-017 | v2 — Hub-fed body-composition scale audit (Withings / Garmin Index / Renpho via Apple Health / Health Connect) | health_data_issue | candidate | Per `GRAPPLER_READINESS_PROTOTYPE_PLAN.md` § "Evidence input roadmap" v2. Hub-only path; no direct vendor API. `WeightRecord` + `BodyFatRecord` + `LeanBodyMassRecord` provenance label rendering. Lane 2. |
| FS-018 | v2 — Custom timeline journal (interventions / peptides / supplements / training changes) + metric-effect window analysis | feature_idea | candidate | Per `docs/CUSTOM_JOURNAL_HEALTH_EFFECTS_SPEC.md`. Schema (journal_items / journal_events / journal_dose_periods / metric_effect_windows) + beginner UX + readiness confidence-modulation integration. NEVER causation claims, only `associated with` / `appeared to`. `confidence: high` reserved. Lane 3 (DB + privacy). |

### Per-candidate approval log

Each candidate gets a row here when Aaron acts. Append-only.

```
FS-001 | (awaiting Aaron approval)
FS-002 | (awaiting Aaron approval)
FS-003 | (awaiting Aaron approval)
FS-004 | (awaiting Aaron approval)
FS-005 | (awaiting Aaron approval)
FS-006 | (awaiting Aaron approval)
FS-007 | (awaiting Aaron approval)
FS-008 | (awaiting Aaron approval)
FS-009 | (awaiting Aaron approval)
FS-010 | (awaiting Aaron approval)
FS-011 | (awaiting Aaron approval)
FS-012 | (awaiting Aaron approval)
FS-013 | (awaiting Aaron approval)
FS-014 | (awaiting Aaron approval)
FS-015 | (awaiting Aaron approval)
FS-016 | (awaiting Aaron approval)
FS-017 | (awaiting Aaron approval)
FS-018 | 2026-05-08 approved by Aaron — dispatched CODEX-CUSTOM-JOURNAL-V1-SCHEMA-AND-UI-01 to codex-lauburu pane
FS-019 | approved_active 2026-05-08 Aaron — note: native iPhone/TestFlight automation controls are the top active mobile priority above P1/P2.
FS-020 | 2026-05-08 approved by Aaron — dispatched CODEX-FS020-JOURNAL-IMPORT-SCHEMA-AND-DICTIONARY-01 (B-20a + B-20b paired) to codex-lauburu pane
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
