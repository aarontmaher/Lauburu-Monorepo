# Admin/Dev installed-proof gap

The proof gap between **AdminDev features visible to MCP / repo
inspection** and **AdminDev features verified on the installed
tester device**. Repo visibility is necessary; only installed-
device proof is sufficient.

This is a **doc-only checklist**. No app code. No EAS build.
No production release.

## 0. Why this gap exists

Recent sessions shipped substantial Admin/Dev surface — approval
gates (commit 87ebabc), AI spend gates (228160c), Deep Research
offload (11b8c75), release-gate boolean tile + idle / lane
breakdown (820dbb6), MCP freshness age cue, project.ping
diagnostic (1081d65), /mcp/v2 surface split (630bf3f). All of
those are **repo-visible and MCP-readable**. None of them is
yet **installed-device verified** — the live tester build is
Android v20 (EAS `58071abc`, commit `3d7122c`) which is the
Health Connect retest target and predates the gate-centre
commits.

Until installed-device proof exists, Aaron's phone is showing
either the v20 build's earlier surface (most of the new tiles)
OR a Metro / dev-client build that does NOT match what shipped
to the QA bundle. The architecture decision in
`docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` (§ 2 criterion (a))
explicitly waits on this gap closing before Developer Mode in
ChatGPT can be turned off.

## 1. Proof checklist

For each row, record on installed-device QA:

| # | Field / tile | What "proven" looks like | Source on the screen |
|---|---|---|---|
| P1 | **MCP freshness** | The "MCP" tile reads "MCP live · fresh · Ns ago" or "Nm ago" with a non-empty updatedAt timestamp. If stale, the warning chip below renders the same age + a non-empty staleReason. | Admin/Dev tab → Now section → MCP tile + (when stale) Stale writeback chip. |
| P2 | **Lane status** | The "Lanes" tile shows N (totalLanes from `mobile.get_lane_overview`) and a meta line listing per-status counts. The "Idle" tile shows the idle count plus "N working · N blocked · N review". Per-lane chips below render claude / codex (id, status, lastSummary). | Admin/Dev tab → Now section → Lanes tile + Idle tile + lane chips. |
| P3 | **Build gates / Release gate** | Release gate tile renders "iOS ✓/✕ · Android ✓/✕" booleans from `release.get_gate`; meta line carries the gate reason. Build-gate chip below carries the same booleans + installed Android v / iOS Build numbers + target build numbers when set. | Admin/Dev tab → Now section → Release gate tile + Build gate chip. |
| P4 | **Approval gates** | "Approval gates" Section renders ≥ 1 row per seeded gate (id, priority, actionType, status, countdown). Tap-expand reveals description, actionPayload, safeDefault, ledgerActionId. Approve / Defer 24h / Cancel buttons visible on active gates. "Copy last ledger note" appears after first approval. | Admin/Dev tab → Approval gates section. |
| P5 | **AI spend gates** | "AI spend gates" Section shows ≥ 1 row per seeded gate (priority, triggerType, cost class, status, countdown, precheck summary). Tap-expand shows reason for AI + proposed AI action + safeDefault + precheckRuleId. Approve spend / Defer 24h / Cancel + "Export prompt for ChatGPT" SelectableCopyButton. | Admin/Dev tab → AI spend gates section. |
| P6 | **Deep Research offload / cached artifact** | "Deep Research offload" Section shows ≥ 1 job (triggerType, status, artifactStatus, completion age). Tap-expand shows prompt + cached result (when present) + citations + freshnessWindowDays + supersededBy. Copy-prompt + paste-result box + Mark submitted / Mark complete / Cancel visible on active jobs. | Admin/Dev tab → Deep Research offload section. |
| P7 | **Action ledger** | The next-pending-action chip surfaces id + owner + priority + actionText + triggerCondition matching `data/action-ledger/pending_actions.json`. Top-N priorities chip lists rank 1–5 from `actionLedger.topPriorities`. | Admin/Dev tab → Now section → action-ledger surfacing (existing). |
| P8 | **v20 / installed build status** | "Build / repo" tile shows `Android v20` (or whatever versionCode the device reports via `expo-application` `nativeBuildVersion`) and matches `mobile.get_build_status` or the freshness-stamped MCP value. iOS row shows Build 19 (or current TestFlight). The on-device versionCode MUST match the value the QA bundle was built from. | Admin/Dev tab → Now section → Build / repo tile + Build / iOS chips. Cross-check with iPhone Settings → General → About when in doubt. |

A row is **proven** when:
- Aaron sees the on-device value match the MCP-readable value
  (or the freshness banner explains why it's stale).
- Aaron captures the screenshot listed in § 2.
- The screenshot is recorded against the AGENT_QA_RESULT_JSON
  bundle for that build.

A row is **NOT proven** if:
- The tile is missing on-device (it was added after the
  installed bundle was built).
- The on-device value is `unknown`, `—`, or `Loading…` and
  stays there past 60 seconds.
- The on-device versionCode doesn't match the value in the QA
  evidence (e.g. the device is on v18, not v20).

## 2. Screenshot capture spec

Aaron captures these screenshots, in this order, per
installed-device QA cycle. File names use the pattern
`p<row>-<platform>-v<versionCode>.png` so a future viewer can
sort by row.

| File | Platform | What it shows |
|---|---|---|
| `p1-android-v20.png` (or iOS equivalent) | Android v20 / iOS Build 19 | Admin/Dev tab → top of Now section. The MCP tile + Fetched tile + freshness banner all visible in one frame. |
| `p2-android-v20.png` | same | Admin/Dev tab → Lanes tile + Idle tile + lane chips for claude / codex. |
| `p3-android-v20.png` | same | Admin/Dev tab → Release gate tile + Build gate chip. iOS ✓/✕ + Android ✓/✕ booleans + reason text legible. |
| `p4-android-v20.png` | same | Approval gates section, expanded for at least one active gate (Approve / Defer / Cancel buttons visible; description text legible). |
| `p5-android-v20.png` | same | AI spend gates section, expanded for at least one gate; Export prompt button visible; precheck summary legible. |
| `p6-android-v20.png` | same | Deep Research offload section, expanded; Copy prompt button visible; paste box visible. |
| `p7-android-v20.png` | same | Next-pending-action chip + top priorities chip. |
| `p8-android-v20.png` | same | Build / repo tile (Android versionCode 20) + Build / iOS chip. Cross-check screenshot of the Settings → General → About page for the same build is OPTIONAL but useful. |

If a row's UI is **missing** in the installed build (because the
build predates the commit that landed it), capture the empty
state anyway, label the file `p<row>-android-v<versionCode>-MISSING.png`,
and record in the proof JSON that the tile was not yet shipped
in this bundle.

Anti-rules for screenshots:
- **Crop or blur** any text containing real Apple ID / Supabase
  email / device IMEI / push token / MCP admin Bearer.
- **Do NOT capture** the action-ledger detail pane if it
  surfaces raw user health values; the public-safe summary chip
  is enough.
- File names must NOT include device serial numbers.

## 3. Proof JSON shape

The screenshots ride alongside an AGENT_QA_RESULT_JSON delta
keyed `admin_dev_installed_proof`. Recorded via
`npm run bridge:agent-qa` so it lands in the connector handoff
table.

```json
{
  "schemaVersion": 1,
  "platform": "android",
  "installedBuild": {
    "versionCode": 20,
    "appVersion": "0.1.0",
    "channel": "internal_testing",
    "easBuildId": "58071abc",
    "repoCommit": "3d7122c"
  },
  "capturedAt": "2026-05-09T00:00:00Z",
  "proof": {
    "p1_mcp_freshness": "pass",
    "p2_lane_status": "pass",
    "p3_release_gate": "pass",
    "p4_approval_gates": "missing_in_bundle",
    "p5_ai_spend_gates": "missing_in_bundle",
    "p6_research_offload": "missing_in_bundle",
    "p7_action_ledger": "pass",
    "p8_installed_build": "pass"
  },
  "screenshotRefs": [
    "p1-android-v20.png",
    "p2-android-v20.png",
    "p3-android-v20.png",
    "p4-android-v20-MISSING.png",
    "p5-android-v20-MISSING.png",
    "p6-android-v20-MISSING.png",
    "p7-android-v20.png",
    "p8-android-v20.png"
  ],
  "notes": "v20 predates approval-gate / AI-spend-gate / research-offload commits. P1-P3, P7, P8 verified live; P4-P6 require a fresh QA build."
}
```

Allowed `proof.<row>` values:
- `pass` — verified live on the installed device, matches MCP.
- `partial` — tile rendered but at least one field shows
  `unknown` / `—` / stale past 60s.
- `mismatch` — tile renders but on-device value contradicts
  the MCP-readable value; capture both screenshots so the
  delta is reproducible.
- `missing_in_bundle` — tile is not present on-device because
  the build predates the relevant commit. Acceptable; triggers
  a follow-up "next QA build must include row X" ledger entry.
- `not_tested` — Aaron skipped the row this round (use
  sparingly; default to a follow-up cycle).

## 4. Developer Mode policy

> **Developer Mode in ChatGPT remains ON until Admin/Dev
> installed proof passes for rows P1–P8.**

This restates `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 2
criterion (a) in operational terms:
- (a) parity holds when every row in § 1 of this doc has a
  `pass` (or knowingly accepted `partial`) proof status from
  an installed-device QA cycle.
- Until then, Developer Mode is the only path that gives Aaron
  the same state surface from inside a ChatGPT chat. Turning
  it off prematurely would lose visibility on rows that haven't
  been proven on-device yet.

The policy is **conservative**: even one `missing_in_bundle`
row keeps Developer Mode ON. The cost of staying on Developer
Mode is low (a settings toggle); the cost of turning it off
prematurely is invisible-state surprises during Agent runs.

## 5. Notify-Aaron trigger

> **Notify Aaron when Developer Mode can be turned off.**

Operational definition for "can be turned off":

A new ledger action fires (id pattern
`adminDev-installed-proof-passes-<date>`, owner=Aaron,
priority=P2) when ALL of the following hold simultaneously
across one installed-device QA bundle:

1. AGENT_QA_RESULT_JSON written via `npm run bridge:agent-qa`
   for the current installed bundle.
2. `admin_dev_installed_proof.proof` has each P1–P8 row in
   `{ "pass" | "partial" }` (no `missing_in_bundle`, no
   `mismatch`, no `not_tested`).
3. The bundle's `installedBuild.versionCode` is ≥ the
   versionCode at which the last gate-centre commit
   (commit 11b8c75 today) was bundled into a tester build.
4. `release.get_gate` reports `publicSafe === true` and the
   reason text does NOT contain "stale" or "no_writeback".
5. § 2 criteria (b)–(f) of `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md`
   already hold (push wiring, Surface B, Agent fallback proven,
   coder workflow continues, no active MCP-creation-fix
   prompts).

When 1–5 hold, the bridge writes a ledger action surfacing the
recommendation to Aaron. The Admin/Dev tab's existing notification
banner (rule 20) AND the approval-gate centre (rule 21)
re-render the recommendation; once Aaron approves the gate,
Developer Mode flips OFF in his ChatGPT settings (manual one-tap;
the app does not control browser-side settings).

If 1–4 hold but 5 does NOT, the ledger entry surfaces as
"phase 2 ready, phase 3 still required" so Aaron knows the
on-device proof is ready but Surface B / push wiring are still
holding the migration.

The notify trigger is **never fired automatically by AI**. It
is fired by the bridge writer reading the QA bundle —
deterministic, no AI inference. AI may suggest Aaron run the
QA cycle but never decides on its own that Developer Mode is
safe to turn off.

## 6. Today's status (2026-05-09)

- Live installed bundle: Android v20 (EAS `58071abc`, commit
  `3d7122c`) — predates 87ebabc / 228160c / 11b8c75 / 820dbb6 /
  555c670. P1–P3, P7, P8 expected to render; P4–P6 expected
  `missing_in_bundle` until next QA build.
- iOS: Build 19 in TestFlight processing per
  `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md`. Same proof gap
  as Android.
- Therefore: Developer Mode in ChatGPT MUST stay ON. The
  proof bundle for v20 will report `missing_in_bundle` for the
  three gate centres, which is acceptable for v20 (it carries
  the Health Connect crash patch + debug surface only).
- Next QA build (requires Aaron approval, no EAS build today)
  must bundle the gate centres so the next proof cycle can
  flip P4–P6 to `pass`.

## 7. Cross-references

- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` — § 2 criteria
  (a)–(f) and § 3 parity table.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — installed-device
  QA gate Aaron runs per release.
- `docs/APPROVAL_GATES_AND_PUSH.md` — push setup blockers
  (criterion (b)).
- `docs/AGENT_MCP_ACCESS.md` — § 5 fallback workflow that the
  installed-proof passes obsoletes.
- `docs/MCP_CORE_AGENT_TROUBLESHOOTING.md` — diagnostic ladder
  if MCP / connector misbehaves during a proof cycle.
- `docs/RELEASE_AUTOMATION_SPEC.md` — § 6 Admin/Dev tile spec
  (T1–T6) and § 8 status wording ladder.
