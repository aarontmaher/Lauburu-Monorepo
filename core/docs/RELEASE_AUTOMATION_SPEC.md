# Release Automation Spec — Android Internal + iOS TestFlight

Status: spec only. No app code changes. No EAS build. No production
release. The Agent-confirmed + Aaron-approved gate is mandatory and
this doc does not relax it.

This doc unifies the existing pieces into one end-to-end state
machine and specifies what Admin/Dev shows at each step. It does NOT
re-spec the credential setup — those live in the linked docs and are
not duplicated here.

Companion docs:

- `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` — proxy / workflow_dispatch
  contract and secret model.
- `docs/PLAY_SUBMIT_SETUP.md` — Google Play service-account JSON +
  Internal Testing track wiring.
- `docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md` — App Store Connect API
  key + TestFlight Internal Testing group wiring.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — installed-device QA
  contract that must clear after every internal release.
- `docs/MOBILE_RELEASE_SYNC.md`, `docs/TESTFLIGHT.md` — historical
  notes; this spec supersedes them where they conflict.
- `docs/OPERATING_RULES.md` rule 6 (EAS build cost control), rule 7
  (no "fully done" without Aaron), rule 16 (deferred prompt/action
  backlog hygiene).

## 1. Anti-rules (apply at every step)

1. **No app code changes from this spec.** Any code change must be a
   separate, narrowly-scoped commit reviewed against the rest of the
   pipeline.
2. **No EAS build is started by this spec or by automation alone.**
   Aaron must approve each build after Agent confirms it is
   worthwhile.
3. **No production release.** Internal Testing (Android) and
   TestFlight Internal Testing (iOS) are the only release targets in
   scope.
4. **Coders must not claim shipped.** Repo / simulator / processing
   evidence does not clear the installed-device gate. The status
   wording ladder is fixed (see § 8).
5. **No mobile-app secrets.** EAS, Play SA JSON, Apple ASC API key,
   GitHub PAT — all live in GitHub Actions secrets / EAS server-side
   credentials / Railway env. The mobile app sees none of them, ever.
6. **No bypass of the workflow allowlist.** Mobile → backend proxy →
   GitHub `workflow_dispatch` only. No `push`-triggered release
   workflows. No free-text command input.
7. **Public MCP must stay redacted.** The release spec must not leak
   raw tokens, ASC issuer IDs, Play SA email, raw EAS build URLs, or
   personal device IDs onto `/mcp/v2`, `/mcp/v2/admin`, or
   `/mcp/v2/website`. Aggregates and short status enums only.

## 2. Current state — audit (2026-05-09)

| Component | State | Source |
|---|---|---|
| EAS build profiles | `development`, `preview`, `production` configured | `apps/mobile/eas.json` |
| EAS submit profile | `production` only — iOS group `Team (Expo)`, Android track `internal`, `releaseStatus: completed` | `apps/mobile/eas.json` `submit.production` |
| GitHub Actions release workflows | `mobile-typecheck.yml`, `android-aab-build.yml`, `ios-testflight-build.yml`, `backend-smoke.yml`, `release-audit.yml`, `ota-diagnostic.yml` | `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` § "Required workflows" |
| Backend `POST /api/admin/workflows/:workflowId/dispatch` | scaffolded, not implemented | `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` § "Implementation status" |
| Mobile Quick-actions buttons | disabled | `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` § "Implementation status" |
| Google Play SA JSON (`PLAY_SA_JSON`) | NOT set; auto-upload not wired | `docs/PLAY_SUBMIT_SETUP.md` |
| Apple ASC API key (EAS-cached) | NOT set; submit step not wired | `docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md` |
| Live release in flight | Android v20 AAB built (EAS `58071abc`, commit `3d7122c`); manual Play Console upload pending Aaron. iOS Build 19 in TestFlight processing. | `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` |
| Public release | none planned this window — Internal/TestFlight only | this doc |

## 3. Target workflow — end-to-end state machine

Each release passes through these states in order. Skipping a state
means the gate is not cleared and the build does not count as
shipped.

```
   ┌──────────────────────┐
0  │ implementation_complete_awaiting_agent_confirmation
   └──────────┬───────────┘
              │   coder commits + tsc/tests pass
              ▼
   ┌──────────────────────┐
1  │ agent_confirmed_ready_for_aaron_build_approval
   └──────────┬───────────┘
              │   Agent functional audit OK + bundle worthwhile
              ▼
   ┌──────────────────────┐
2  │ aaron_approved_for_eas_build
   └──────────┬───────────┘
              │   Aaron taps approve (in-app or via prompt)
              ▼
   ┌──────────────────────┐
3  │ build_started
   └──────────┬───────────┘
              │   `eas build` non-interactive
              ▼
   ┌──────────────────────┐
4  │ build_finished
   └──────────┬───────────┘
              │   AAB / IPA artifact URL available
              ▼
   ┌──────────────────────┐
5  │ submit_dispatched
   └──────────┬───────────┘
              │   `eas submit` upload to Play Internal / TestFlight
              ▼
   ┌──────────────────────┐
6  │ store_processing
   └──────────┬───────────┘
              │   Play Console / App Store Connect server-side processing
              ▼
   ┌──────────────────────┐
7  │ tester_installable
   └──────────┬───────────┘
              │   tester opens app on Play Internal / TestFlight
              ▼
   ┌──────────────────────┐
8  │ installed_device_qa_in_progress
   └──────────┬───────────┘
              │   AGENT_QA_RESULT_JSON via `npm run bridge:agent-qa`
              ▼
   ┌──────────────────────┐
9  │ qa_passed | qa_failed
   └──────────────────────┘
```

State 9 = `qa_passed` clears the gate for that specific build only.
A new build re-enters at state 0. There is no path from state ≥ 3
back to state 0 — once a versionCode/buildNumber is consumed it
cannot be reused (Play Console / App Store Connect both reject
duplicates).

State 9 = `qa_failed` does **not** consume the gate; it produces a
required-fixes list that lands as a new ledger action and a new
implementation cycle starts at state 0.

## 4. Android — submit / track requirements

(Cross-ref: `docs/PLAY_SUBMIT_SETUP.md`. Do not duplicate the setup
checklist here.)

**eas.json `submit.production.android`** (already set):

```json
{
  "serviceAccountKeyPath": "./google-services-key.json",
  "track": "internal",
  "releaseStatus": "completed"
}
```

**Required for state 5 (`submit_dispatched`) automation:**

- `PLAY_SA_JSON` GitHub Actions secret — Play Developer service
  account JSON with **Releases — Manage testing track releases
  (Internal testing)** + **App access — View app information**.
  Production / closed-testing permissions stay OFF.
- The service account must already be granted access in
  Play Console → Setup → API access (one-time).

**versionCode handling:**

- `apps/mobile/app.json` `android.versionCode` is bumped per build.
- `eas.json` `cli.appVersionSource: "local"` keeps the source of
  truth in the repo, not in EAS server-side.
- A consumed versionCode (any release that reached state 5+) cannot
  be reused. Skip-numbering (e.g. `19 → 20` even if v19 was never
  uploaded) is allowed; reverse-numbering is not.
- Pre-build check (Codex / coder responsibility, not automation):
  `git log -1 --pretty=format:%H apps/mobile/app.json` and confirm
  the bump commit is on `main` and HEAD before triggering build.

**Track:** internal only. Production / closed-testing require an
explicit additional approval flow not in scope for this spec.

**Submit dispatch flow (target):**

```
GitHub Actions android-aab-build.yml
  → eas-cli build --platform android --profile production --non-interactive
  → (if submitToPlay=true)
     download AAB → write PLAY_SA_JSON → eas submit --platform android
     --path app.aab --profile production --non-interactive
  → output: build URL + Play track + Play submission ID
```

## 5. iOS — submit / track requirements

(Cross-ref: `docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md`. Do not
duplicate the setup checklist here.)

**eas.json `submit.production.ios`** (already set):

```json
{
  "appleTeamId": "DLVKNS75NJ",
  "ascAppId": "6762436447",
  "groups": ["Team (Expo)"]
}
```

**Required for state 5 (`submit_dispatched`) automation:**

- App Store Connect API key (`.p8` + Key ID + Issuer ID), cached
  EAS-side via `npx eas-cli credentials --platform ios` →
  **production** → **App Store Connect API Key** → **Add new**.
  The key never lives in GitHub Actions or in the mobile app.
- The role on the ASC key must be **App Manager** (or Admin if
  production submission later). For internal-testing-only it is App
  Manager.
- TestFlight internal group `Team (Expo)` must already include the
  tester Apple IDs (one-time Play / ASC step).

**buildNumber handling:**

- `apps/mobile/app.json` `ios.buildNumber` is a string, bumped per
  build (`"19"` → `"20"` etc).
- ASC rejects duplicate `buildNumber` for the same `version`.
  Auto-increment on collision is **not** part of this spec — coders
  bump explicitly per build for traceability.
- `appVersionSource: "local"` (same as Android) keeps the source of
  truth in the repo.

**TestFlight auto-assignment:** the `groups` array on the iOS submit
profile auto-assigns the build to Internal Testing groups at upload
time. Without this, the build lands in **Ready to Submit** and stays
there until manual click.

**Submit dispatch flow (target):**

```
GitHub Actions ios-testflight-build.yml
  → eas-cli build --platform ios --profile production
  → (if submitToTestFlight=true)
     eas submit --platform ios --profile production --latest
     --non-interactive
  → output: build URL + TestFlight submission ID + group assignments
```

## 6. Admin/Dev tile spec

This section is the source of truth for the in-app release-progress
surface. Each release state from § 3 maps to one or more tiles. All
tiles are admin-email gated (`aaron.t.maher@gmail.com` only) and
read from MCP — the app never contacts EAS, Play Console, or App
Store Connect directly.

**Layout:** `Admin/Dev → Now → Release pipeline` (new section, sits
above the existing Release gate tile). Tiles are arranged in a 2×3
grid for portrait, single-column scrollable for landscape.

| # | Tile name | Source (MCP tool) | Display when state ∈ | Key fields |
|---|---|---|---|---|
| T1 | Build started | `mobile.get_build_overview` (core) + `mobile.get_build_status` (admin) | `build_started` | platform, profile, eas_build_id (last 6 chars only on public surface), elapsed time |
| T2 | Build complete | `mobile.get_build_status` (admin) | `build_finished`, `submit_dispatched` | platform, versionCode/buildNumber, AAB/IPA size, build URL (deep-link only when admin token present) |
| T3 | Upload submitted | `mobile.get_build_status` (admin) | `submit_dispatched` | platform, target track / TestFlight group, submission ID (last 6 chars only on public surface), elapsed time |
| T4 | Store processing | `mobile.get_build_status` (admin) | `store_processing` | platform, store enum (`google_play_processing` / `apple_processing`), expected window (e.g. "5–30 min"), poll attempt count |
| T5 | Tester installable | `release.get_gate` (admin) + `mobile.get_build_status` (admin) | `tester_installable`, `installed_device_qa_in_progress` | platform, install URL (deep-link only with admin token), versionCode/buildNumber visible to tester |
| T6 | QA passed/failed | `release.get_gate` (admin) + `qa.get_latest_result` (admin) | `qa_passed`, `qa_failed` | platform, gate enum (`pass` / `fail` / `partial`), required-fixes count, link to AGENT_QA_RESULT_JSON |

**Tile colour cues:**

- Green = state cleared, gate progressed.
- Amber = in-flight (build running, store processing, QA in progress).
- Red = QA failed, build failed, submit failed, or stale state (no
  update for > the freshness window of the underlying tool).
- Gray = state not yet entered.

**Required-tile invariant:** if `release.get_gate` returns
`buildAllowed.android === false` or `buildAllowed.ios === false`,
the corresponding T1 tile must be DISABLED (visually grayed) and
its tap target must surface the `reason` string from the gate
payload — Aaron cannot trigger a build whose gate is not cleared.

**Failure modes:**

- T1 disabled and `release.get_gate` reason mentions
  `Implementation-complete-awaiting-agent-confirmation`: Agent
  audit pending; Aaron should not approve.
- T2 stuck > 30 min: EAS build likely failed; admin tile shows
  `eas_build_status` enum and link to EAS build details.
- T4 stuck > 60 min on Android: Play upload likely succeeded but
  rollout to Internal Testing requires manual Play Console click
  (only when `releaseStatus !== "completed"`; should not happen
  since current submit profile is `completed`).
- T4 stuck > 24 h on iOS: Apple processing failed; check ASC
  TestFlight tab for processing errors (e.g. ITMS-90XXX warnings).
- T6 = `qa_failed`: required-fixes list lands as a new ledger
  action; release pipeline does not auto-retry.

## 7. MCP / connector data contract

The Admin/Dev tiles consume these MCP tools. Tools that require
admin token (every "full" payload) only render if the mobile app
has `EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN` configured at build time.

**Public-safe (`/mcp/v2` core, no auth):**

- `mobile.get_build_overview` — Android versionCode / iOS
  buildNumber + status enums (`repo-only`, `github_running`,
  `github_failed`, `github_success`). No EAS / submission UUIDs.
- `mobile.get_lane_overview` — for the existing lane breakdown
  tile.
- `project.get_current_state` — for the freshness banner.

**Admin-token (`/mcp/v2/admin`):**

- `mobile.get_build_status` — full payload incl. EAS build IDs,
  Play submission ID, TestFlight submission ID, build URL. Used by
  T1–T4.
- `release.get_gate` — `buildAllowed: { ios: bool, android: bool }`,
  `reason: string`, `installedBuild`, `targetBuild`. Used by T5
  and the existing Release gate tile.
- `qa.get_latest_result` / `qa.list_results` — public-safe summary
  of the latest Agent QA gate. Used by T6.
- `mobile.get_agent_qa_result` — full Agent QA payload (admin only).
  Used by T6 expanded view.

**Connector tables (Supabase) the worker reads from:**

- `connector_build_status` — Android + iOS release rows including
  IDs. Already populated by `npm run bridge:snapshot` from
  `data/agent-status/lanes/*.json`.
- `connector_handoff` — `agentQaResult`. Already populated by
  `npm run bridge:agent-qa`.
- `connector_work_status` — `currentPriority`, `currentBlocker`,
  `nextAction`, `latestQaGate`. Already populated.

No new schema is required by this spec. The Worker payloads are
already the right shape; the Admin/Dev change is rendering only.

## 8. Status wording ladder (canonical strings)

Coders, agents, and Aaron must use these exact strings — never
flatten to "done", "shipped", or "complete":

| State | Canonical wording |
|---|---|
| 0 | `Implementation-complete, awaiting Agent functional confirmation` |
| 1 | `Agent-confirmed, ready for Aaron build approval` |
| 2 | `Aaron-approved for EAS build` |
| 3 | `Build-started: <platform> <profile>` |
| 4 | `Built/tester-ready: <platform> <eas_build_id last-6>` |
| 5 | `Submit-dispatched: <platform> → <track or group>` |
| 6 | `Store-processing: <platform>` |
| 7 | `Tester-installable: <platform> <versionCode/buildNumber>` |
| 8 | `Installed-device QA in progress` |
| 9a | `Installed-device QA passed: <platform> <versionCode/buildNumber>` |
| 9b | `Installed-device QA failed: <required-fixes count> fix(es) needed` |

State 9a is the only state that may be referred to as "shipped to
internal" or "shipped to TestFlight". `Public release` requires a
separate gate not in scope for this spec.

## 9. Gate sequencing (mandatory)

Per § 3 + § 8:

1. **State 0 → 1** transition requires Agent confirmation only
   after: typecheck/tests pass, no obvious blockers, expected
   behaviour described, change is bundled if small. Agent says NO
   if any of those is missing.
2. **State 1 → 2** transition requires Aaron's explicit approval.
   The mobile Admin/Dev tile may render an `Approve build` button
   only when state is exactly 1. The button must show the bundle
   summary and the gate reason from `release.get_gate` before
   firing.
3. **State 2 → 3** transition is the workflow_dispatch call. The
   backend proxy must reject the call if the lane state is not
   exactly 2 (cross-checked against `connector_work_status` at
   request time).
4. **State 7 → 8** is when the tester opens the build on-device.
   No automation — this is a human action.
5. **State 8 → 9** is the AGENT_QA_RESULT_JSON record via
   `npm run bridge:agent-qa`.
6. **No state 0 → 9 shortcut.** Coders may not declare a build
   shipped without Agent QA evidence with the exact installed
   versionCode/buildNumber. Repo / simulator / processing evidence
   is rejected at state 9 by the bridge writer (already enforced).

## 10. Open follow-ups (NOT in this spec)

These are required to make the target workflow operational, but are
explicitly out of scope for this doc:

- **Backend `POST /api/admin/workflows/:workflowId/dispatch`** —
  scaffolded only (`docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` §
  "Implementation status").
- **Backend `GET /api/admin/workflows/runs`** — same.
- **Mobile Quick-actions buttons** — disabled
  (`docs/ADMIN_RELEASE_AUTOMATION_PLAN.md`).
- **`PLAY_SA_JSON`** GitHub Actions secret — not set
  (`docs/PLAY_SUBMIT_SETUP.md`).
- **App Store Connect API key** — not cached EAS-side
  (`docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md`).
- **`android-aab-build.yml` Play upload step** — documented but
  not added to the workflow file.
- **`ios-testflight-build.yml` submit step** — same.
- **Admin/Dev "Release pipeline" tile section** — design above; not
  yet rendered in `apps/mobile/app/admin-dev.tsx`. Codex handoff
  below covers this.

## 11. Codex handoff (next implementation batch)

When all five "Open follow-ups" credentials are in place AND Aaron
explicitly approves the implementation cycle, the next Codex prompt
is:

> Implement the Release pipeline tile section (T1–T6) in
> `apps/mobile/app/admin-dev.tsx` per
> `docs/RELEASE_AUTOMATION_SPEC.md` § 6. Reuse the existing
> `summariseReleaseGate` + `mcpV2Snapshot.releaseGate` shape; add
> a `summariseBuildPipeline` helper that reads
> `mcpV2Snapshot` (already fetches `mobile.get_build_overview` on
> core; will need `mobile.get_build_status` on admin for full
> payload) and returns the per-state colour + label per § 6.
> Anti-rules: no app code outside `admin-dev.tsx` and the MCP
> client; no new MCP tools; no EAS build; no production release.
> Tests: extend `test-mcp-v2-chatgpt-compat.ts` to assert
> `release.get_gate.installedBuild` shape stays compatible.
> Bundle with the next admin-dev change to keep EAS build cost
> down.

Human action required before that Codex prompt fires:

1. Aaron approves the spec (this doc).
2. `PLAY_SA_JSON` set as GitHub Actions secret per
   `docs/PLAY_SUBMIT_SETUP.md` § 2.
3. App Store Connect API key cached EAS-side per
   `docs/IOS_TESTFLIGHT_AUTOMATION_SETUP.md` § 3.A.
4. Backend `POST /api/admin/workflows/:workflowId/dispatch`
   implemented per `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md`.

Until those four are in place, the Admin/Dev release-pipeline tiles
would render mostly gray / "not configured", which is acceptable
and informative — the spec is forward-compatible with the partial
state.
