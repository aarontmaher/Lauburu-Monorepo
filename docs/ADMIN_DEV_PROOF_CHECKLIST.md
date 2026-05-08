# Admin/Dev proof checklist

The tap-through Aaron uses to verify the **Admin/Dev tab is
the canonical operator surface** (Surface A per
`docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md`). Each row is a
proof point — when ALL rows pass on installed iOS + Android
builds, criterion (a) of the architecture doc § 2 holds and
Developer Mode for the ChatGPT MCP connector can be turned
off without losing the operator workflow.

This is **doc only**. No app code. No EAS build.

## 0. How to use this checklist

1. Run on the LATEST installed build (Android v20 + iOS build 19
   today). Record actual build identity in the audit manifest
   per `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` § 2.
2. Step through each row. For each: capture a screenshot
   into the audit folder + record `pass | partial | fail` in
   `agent_qa_result.json`.
3. Tag the run: `gate: admin_dev_proof_checklist`.
4. Audit cadence: run quarterly + after any FS-XXX that
   touches Admin/Dev + before turning off Developer Mode.
5. Privacy: real-user data on screen — redact / blur / use
   test account before sharing the bundle externally.

## 1. MCP freshness section

Anchor: Admin/Dev top → MCP freshness pill / writeback card.

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 1.1 | MCP freshness pill renders | Pill shows `Live` (= fresh) OR `Stale: <reason>` truthfully. Never silently shows `Live` with no underlying writeback. | rule 11 / rule 18 |
| 1.2 | Last-writeback age is shown | Relative age ("2 minutes ago") + ISO timestamp on long-press. | rule 12 |
| 1.3 | Stale-state surfaces actionable next step | If stale, the card surfaces what unblocks freshness (run `bridge:snapshot` / Worker deploy / Supabase env). | rule 11 |
| 1.4 | Tap to refresh works | Pulling-to-refresh re-fetches `project.get_current_state`. State updates within 3s. | architecture § 3.1 |

## 2. Lane status section

Anchor: Admin/Dev top → lane chips (Claude / Codex / Agent).

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 2.1 | All 3 lanes render | Three chips visible: Claude, Codex, Agent. | architecture § 3.1 |
| 2.2 | Status enum maps cleanly | Chip state matches `agents[].status` enum: `idle` / `working` / `blocked` / `needs_review` / `needs_user` / `complete_waiting_approval`. No unmapped state shows raw string. | rule 14 |
| 2.3 | Idle/working/blocked tile renders the canonical lane status | Single tile summarising "Lane: Claude — working: <task>" or "all idle". | architecture § 3.1 |
| 2.4 | Lane drift detection | If a lane has been `working` >30min on the same task without a writeback, the card flags drift. | rule 12 + rule 14 |
| 2.5 | All-idle banner triggers | When all 3 lanes idle + no blocker + no Aaron-pause, the all-worker direction banner fires (rule 20 in-app banner). | rule 20 |

## 3. Build gates section

Anchor: Admin/Dev → Build / repo card + release-gate chip.

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 3.1 | Repo HEAD + branch + dirty count | Card shows `branch: main`, short SHA matching live HEAD, dirty count if any. | architecture § 3.1 |
| 3.2 | Build identity (iOS + Android) | Android `versionCode: 20` + iOS `buildNumber: 19` shown. | rule 8 |
| 3.3 | Play / TestFlight track shown | Android `playStatus: aab_downloaded_local_awaits_aaron_upload` + `playTrack: internal`; iOS `testflightStatus: available_to_testers`. | INSTALLED_DEVICE_QA_RELEASE_GATE |
| 3.4 | Release-gate chip renders | Chip shows release-gate `partial / pass / fail` matching `agent_qa_result.releaseGate.newAndroidBuildAllowed` etc. | rule 9 + INSTALLED_DEVICE_QA_RELEASE_GATE |
| 3.5 | Installed vs target build delta | Shows installed Android v<N> + iOS Build <N> separately from target build identifiers. | INSTALLED_DEVICE_QA_RELEASE_GATE |
| 3.6 | "No EAS build until Agent confirms" note | Visible plain-text note enforcing rule 7. | rule 7 |

## 4. Approval gates section

Anchor: Admin/Dev → Approval centre panel (per `docs/HUMAN_APPROVAL_GATE_SPEC.md` § 4).

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 4.1 | Pending approval gates list | Each `waiting_for_approval` row visible: title (≤140 chars), why-it-matters, top-priority context, safe-default, expires-at. | rule 21 |
| 4.2 | Approve / Defer / Deny buttons | Each gate row has all 3 actions; tap maps to `project.update_approval_gate(gateId, action)`. | rule 21 |
| 4.3 | Deferred gates section | Collapsible section listing deferred gates with `deferredUntil` timestamp. | rule 21 |
| 4.4 | Approved last 7d audit | Recent decisions visible with actor + timestamp + reason. | rule 18 |
| 4.5 | Blocked / expired audit | Closed gates with reason. | rule 21 |
| 4.6 | Push permission setting | Per-category enable / disable toggles + Focus break-through opt-in. | PUSH_APPROVAL_AUTOMATION_SPEC § 2 + § 3 |
| 4.7 | Default expiry / default deferral | Settings card shows configured TTL (default 7d / 24h). | rule 21 |
| 4.8 | Deep-link from push works | Tapping a push notification opens admin-dev with the panel filtered to the correct `gateId`. | PUSH_APPROVAL_AUTOMATION_SPEC § 4 |

## 5. AI spend gates section

Anchor: Admin/Dev → AI spend panel (per `docs/AI_SPEND_GATES_SPEC.md`).

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 5.1 | Monthly AI budget + usage | Visible: `Used $X.YY / $5.00 (Z%)` (default $5/mo configurable). | rule 22 § 4 |
| 5.2 | Cost classifier | When a future task is classified, the panel shows `cost_class: free_deterministic / cheap_ai / expensive_ai / deep_research_external`. | rule 22 § 1 |
| 5.3 | Spend-gate approve UI | `expensive_ai` gates render with 4-button action set: Approve / Defer / Export prompt / Ignore. | rule 22 § 3 + PUSH_APPROVAL_AUTOMATION_SPEC § 2 |
| 5.4 | Threshold setting | "Always ask above $X" threshold visible + editable (default $0.50/call). | rule 22 § 4 |
| 5.5 | Pay-as-you-go credits (later) | Field present even if 0; never silently absent. | rule 22 § 4 |
| 5.6 | Budget cap behaviour | When monthly budget hits cap, expensive_ai calls auto-route to `deep_research_external` export-only. | rule 22 § 1.4 |
| 5.7 | Privacy floor reminder | Plain-text note: "Raw sensitive data never sent to AI without per-call approval. Default = summarise first, send minimal context." | rule 22 § 5 |

## 6. Action ledger section

Anchor: Admin/Dev → Action ledger card (per rule 18).

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 6.1 | Active ledger rows | Pending + active + blocked rows visible with: id (truncated), owner, lane, actionText, status, priority. | rule 18 |
| 6.2 | Audit findings sub-section | Per `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` § 6, last N audit findings visible with screenshotRefs. | INSTALLED_DEVICE_AUDIT_PLAYBOOK |
| 6.3 | Approval gate cross-link | Each `waiting_for_approval` ledger row links to the approval centre row via `gateId`. | rule 18 + rule 21 |
| 6.4 | Research artifacts cache | Per `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md`, cached research artifacts visible with reuseKey + citationCount + expiresAt. | rule 23 |
| 6.5 | Void / superseded rows | Visible in a collapsible "history" section with reason. | rule 18 |
| 6.6 | "Terminal is evidence, not memory" note | Plain-text reminder: "Anything discovered in terminal must be written back here before considered tracked." | rule 18 |
| 6.7 | Idempotent consume marker | When an approved gate's resume action runs, `consumedAt` is shown so re-reads don't double-fire. | PUSH_APPROVAL_AUTOMATION_SPEC § 5 |

## 7. v20 / installed build status section

Anchor: Admin/Dev → installed-build summary card.

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 7.1 | Installed build identity | Card shows installed `versionCode` (Android) + `buildNumber` (iOS) — pulled from app.json at build time, NOT from MCP. | INSTALLED_DEVICE_QA_RELEASE_GATE |
| 7.2 | Active gate target | `target: v20` (Android) + `target: build 19` (iOS). | INSTALLED_DEVICE_QA_RELEASE_GATE |
| 7.3 | Active gate type | "Health Connect crash retest" (Android) + "iOS TestFlight install audit" (iOS). | INSTALLED_DEVICE_AUDIT_PLAYBOOK Gate D + E |
| 7.4 | Health Connect debug card (admin-only, v20+) | Visible at admin-dev → Health → Debug section: SDK availability, last `permission_requested`, requested record types, granted metrics, last error. | commit `5ea6b24` |
| 7.5 | "Open Health Connect" deep-link button (v20+) | Visible on the disconnected source row + the failed-permission alert. Tapping deep-links to OS settings + back-button returns cleanly. | INSTALLED_DEVICE_QA_RELEASE_GATE § v20 |
| 7.6 | Historical evidence (v18 fail / v19 superseded) | Visible at INSTALLED_DEVICE_QA_RELEASE_GATE § Historical evidence in collapsible card. | INSTALLED_DEVICE_QA_RELEASE_GATE |
| 7.7 | "No EAS build until v20 retest" enforcement | Plain-text note enforcing rule 7 + the v20 active-gate state. | rule 7 |

## 7B. Phone-first control centre acceptance

Established by `CLAUDE-LIVE-STATUS-DISPATCHER` 2026-05-09 in
response to Aaron's installed-device evidence that MCP lane
status drifts from live pane state + the v20 Health Connect
"app not listed" P0. These rows are explicit phone-side
acceptance criteria — every row must pass on installed iOS +
Android before the Admin/Dev tab can be called "phone-first
complete".

| # | Proof point | Pass criterion | Source spec |
|---|---|---|---|
| 7B.1 | App refreshes project status on open / resume | `AppState` `active` transition triggers a `project.get_current_state` re-fetch within 1.5s. Stale-cache renders during the gap with a "refreshing…" indicator. | `LIVE_MCP_MODEL_SPEC` § 2 + new acceptance |
| 7B.2 | Manual refresh control exists | Pull-to-refresh on the Admin/Dev top section OR explicit refresh button. Tap re-fetches MCP within 1s; UI shows skeleton during. | new acceptance |
| 7B.3 | Stale badge visible when MCP fails | When `freshness.staleReason` is set OR `lastWritebackAt` is null, freshness pill renders `Stale: <reason>` (NOT `Live`). When MCP unreachable, pill renders `MCP unreachable` — never silent. | rule 11 unavailable branch + `LIVE_MCP_MODEL_SPEC` § 3.1 |
| 7B.4 | Worker lanes show age + freshness | Each lane chip shows `<status> · <heartbeatAgeSeconds>` (e.g. "Working · 2 min" / "Idle · 47 min"). When freshness is stale, lane status appends "· stale" + chip background turns grey. | `LIVE_MCP_MODEL_SPEC` § 1.2 + § 3.2 + new MCP-liveness P0 rule (`connector_work_status.mcpLivenessP0`) |
| 7B.5 | Build/QA gate status separated by stage | Build/release card explicitly partitions: `live now` / `repo-only` / `preview-only` (workers.dev) / `installed-verified` (real-device QA passed) / `planned-only`. Each row carries its own truth label. | `MCP_LONGTERM_ACCESS_ARCHITECTURE` § 1 + new acceptance |
| 7B.6 | Android HC "app-not-listed" blocker visible | When v20 retest evidence shows the app is not listed under Health Connect → App permissions, a P0 blocker card surfaces in Admin/Dev with "Health Connect did not register the app" copy + a retry button + a link to ledger entry `audit-2026-05-09T08:12-codex-hc-app-not-listed` + an "awaiting v21 patch" / "v21 patched, awaiting Aaron-approved EAS build" status. | `audit-2026-05-09T08:12-codex-hc-app-not-listed` ledger entry + `INSTALLED_DEVICE_QA_RELEASE_GATE.md` § "v20 installed-device evidence — Android Health Connect 'app not listed'" |

### Stale-worker semantics rule (canonical, P0)

Recorded in `connector_work_status.mcpLivenessP0`. Rule:

> When `freshness.staleReason` is set OR `lastWritebackAt`
> is empty, the UI MUST show **stale** or **unknown** for
> lane status — NEVER relay the cached `agent.status`
> value as `working`.

Rationale: terminal evidence has shown the cached
`agent.status` value drifting from live pane state (e.g.
MCP reports `claude: working` while the pane is idle).
Cached values are unreliable when freshness fails; honest
UI surfaces stale/unknown until writeback resumes.

### AGENT_QA recording for this section

`npm run bridge:agent-qa` with:
- `gate: phone_first_control_centre_acceptance`
- `platform: ios | android` (run on both)
- per-row pass / partial / fail (rows 7B.1–7B.6)
- `evidence.notes` calling out any platform-specific
  divergence + linking to the relevant ledger entry

Pass criteria for this section: all 6 rows pass on
installed iOS + Android. Section pass is a prerequisite
for the § 8 Developer-Mode-off pass criteria below.

## 8. Pass criteria — when does Developer Mode go off?

Run the full checklist (sections 1–7) on installed iOS +
Android. When ALL of the following hold:

- ≥95% of rows pass on both platforms.
- All §4 (approval gates) rows pass — the approval centre is
  fully wired.
- All §5 (AI spend) rows pass — the cost ladder is enforced.
- All §6 (action ledger) rows pass — rule 18 honoured.

…then `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2
criterion (a) is satisfied and Developer Mode for the
ChatGPT custom-MCP connector can be turned off without
losing operator workflow per § 2 of the architecture doc.

If <95% pass: surface the failing rows as FS-XXX candidates;
do NOT turn off Developer Mode yet.

## 9. AGENT_QA recording

After running the checklist:

```sh
npm run bridge:agent-qa
# When prompted:
#   gate: admin_dev_proof_checklist
#   platform: ios | android
#   installedBuild.{ios,Android}VersionCode: per § 2
#   results.{section}: pass | partial | fail (one per § 1-7)
#   evidence.screenshotRefs: artifacts/app-audit/<method>/<timestamp>/manifest.json
#   evidence.notes: any failing rows + remediation
```

The bridge writes to `data/agent-status/lanes/agent_qa_result.json`
and the next `bridge:snapshot` propagates to MCP per rule 12.

## 10. Anti-rules

- **No simulator evidence for §7 (real-device gates).** v20
  Health Connect retest + iOS TestFlight install audit MUST
  be on the actual installed build (Gate A + Gate D / E in
  the audit playbook).
- **No partial-pass override.** "Most rows pass" doesn't
  clear Developer-Mode-off — every gate-related row (§4 +
  §5 + §6) must pass.
- **No silent skip.** Every row must be either passed or
  recorded as a known failure with FS-XXX candidate. Skipping
  is a partial result.
- **No public sharing of raw checklist screenshots.** Real
  user data appears (especially in §6 ledger rows + §7
  Health Connect debug card). Redact before sharing.
- **No EAS build dispatched from this checklist.** Audits
  inform the build decision; they don't trigger it.

## 11. Cross-references

- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2-3 —
  Developer-Mode-off criteria + Surface A field requirements.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` § 4 — approval centre
  panel mockup.
- `docs/AI_SPEND_GATES_SPEC.md` — AI spend gate UX.
- `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md` — synthesis of all
  push-approval surfaces.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — release-gate
  state + v20 build identifiers.
- `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` — operator audit
  decision tree (Gate types A-F).
- `docs/OPERATING_RULES.md` § 9 (provisional) / § 11
  (MCP-first) / § 12 (laptop commands) / § 14 (parallel) /
  § 18 (action ledger) / § 21 (approval gates) / § 22 (AI
  spend) / § 23 (research cache).
