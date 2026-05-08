# In-app audit automation spec

How to enable real installed-app click-through audits without
manual screenshots. Three tiers from "Aaron records a screen
movie" to "every tab/card/modal captured automatically."

This is **doc only**. No app code. No Worker code. No EAS
build. The implementation prompts in § 5–7 fire only after
Aaron approves each tier.

Companion docs:

- `docs/IN_APP_AUDIT_SYSTEM.md` — local audit-event store
  (already shipped) that captures structured metadata about
  source state. Audit-events ride alongside whatever capture
  tier this spec enables.
- `docs/SIMULATOR_QA_AUDIT_HARNESS.md` — earlier simulator
  harness (different gate; this spec specifically targets
  installed-device audits).
- `docs/AGENT_AUDITS.md` — process for Aaron-pasting Agent
  audit results back to the bridge.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — installed-
  device QA gate every release passes through.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — proof checklist
  P1–P8; this spec extends that into automated capture.

## 0. Why this spec exists

Today's installed-device QA is a sequence of manual screenshots
Aaron captures by tapping every tab. The captures are
labour-intensive, easy to forget rows, and impossible for an
Agent to do unattended. As the Admin/Dev surface grows
(approval gates, AI-spend gates, research offload, release-gate
booleans) the screenshot count grows linearly. Without
automation:

- A thorough proof cycle (per `ADMINDEV_INSTALLED_PROOF_GAP.md`
  § 1) is ~8 screenshots Aaron captures by hand.
- The full app surface (Health tab, Train tab, Feedback tab,
  Map tab, Reference tab, Coaching History, Settings,
  Admin/Dev) is ~30+ screens.
- Any modal or sheet (sources sheet, sync detail, gate
  approval flow) doubles that.

The three tiers below are an explicit progression: ship v1
right now (no app code; just better Aaron handoff), v2 as a
small additive admin-only button when bundle credits allow,
v3 as an opt-in CI/local capture script — all OUT of the
production app binary.

## 1. v1 — Manual screen recording (today)

Aaron screen-records a full installed-device tap-through.
Agent (or Aaron, or a coder) audits the recording later. No
app code change. No EAS build.

### 1.1 Capture procedure

1. iPhone: Control Center → Screen Recording → Start.
   Android: Quick Settings → Screen Record → Start.
2. Open Lauburu, sign in if needed.
3. Tap each tab in this fixed order — repeat the script per
   QA bundle so every cycle is comparable:
   1. Home (`(tabs)/index`)
   2. Health (`(tabs)/health`) → Manage Sources sheet → close
   3. Train (`(tabs)/train`) → expand any active session card
      → close
   4. Feedback (`(tabs)/feedback`) → Import notes preview →
      close (post-FS-020 builds)
   5. Map (`(tabs)/map-3d`) → tap one node → back
   6. Reference (`(tabs)/reference`)
   7. Syllabus (`(tabs)/syllabus`)
   8. Coaching history (`(tabs)/coaching-history`)
   9. Settings (`(tabs)/settings`) → Admin/Dev → through
      every Section header in order
4. Stop recording. Trim to ≤ 5 minutes if longer.
5. Upload the video to wherever the audit is going next
   (Agent chat, ChatGPT chat, Codex laptop). Do NOT post it
   to a public surface — the recording carries device-frame
   chrome and possibly real Apple ID / Supabase email.

### 1.2 Agent audit handoff package (v1)

Agent receives in the same message:

- The screen recording (or a single concatenated MP4).
- A short text block:
  ```
  build:
    platform: <android|ios>
    versionCode: <int>      # iOS: buildNumber
    appVersion: <string>
    easBuildId: <string>    # last 6 OK on public surface
    repoCommit: <short SHA>
    channel: <internal_testing|testflight>
  recordedAt: <ISO>
  device:
    model: <e.g. iPhone 15 Pro>
    osVersion: <e.g. iOS 19.0>
  ```
- The current MCP/AdminDev snapshot (rung-3 curl from
  `docs/MCP_CORE_AGENT_TROUBLESHOOTING.md` — `project.get_current_state`).
- Any open ledger items the audit is meant to bisect (e.g.
  "P4 approval-gates expected in v20+ build").

Agent's deliverable: a per-row `pass | partial | mismatch |
missing_in_bundle | not_tested` map per
`docs/ADMINDEV_INSTALLED_PROOF_GAP.md` § 3, plus a short
required-fixes list. Agent must NOT claim shipped without the
recording matching the MCP snapshot.

### 1.3 Privacy on v1 captures

- Recording carries the device frame; blur or crop any pane
  showing real Apple ID / Supabase email / push tokens / EAS
  Bearer / AAB URL with the build artifact hash. The current
  Admin/Dev surface already redacts where it can; the
  recording catches anything that leaks.
- Recording lives on Aaron's device; transferred only to the
  Agent / Codex chat for that audit. Not committed to the
  repo. Not posted to public MCP.

## 2. v2 — Semi-auto: AdminDev "Capture audit bundle" button

A single Admin/Dev button (admin-email-gated) that, when
tapped, captures a structured audit bundle WITHOUT Aaron
having to record video. Bundle includes screenshots,
debug-state JSON, and an MCP snapshot.

NOT shipped today. Implementation gate: bundles with the next
admin-dev change so EAS build cost stays low (per rule 6 / 7).

### 2.1 What the button captures

| Item | Method | Notes |
|---|---|---|
| Native screenshot of current Admin/Dev tab top frame | `expo-screen-capture` (lazy-loaded) | Falls back to "tap-and-paste" guidance if the native module is unavailable. |
| Programmatic snapshot of every Section in Admin/Dev | walk the React tree of `apps/mobile/app/admin-dev.tsx`; capture each Section's title + child Row contents into a JSON array | No raw user health values; only the labels + sanitised values that already render on-screen. |
| MCP snapshot | `mcpV2DashboardSnapshot()` (already exists) | project.get_current_state + project.get_operating_rules + project.get_overview + project.get_work_status + mobile.get_lane_overview + mobile.get_build_overview + handoff.get_latest + release.get_gate. |
| AdminDev gate-store snapshot | read approval-gates-store + spend-gates-store + research-jobs-store getState() | Skip secret-shaped fields; flatten lists to id + status + priority + age. |
| Health Connect / HealthKit availability | reuse `HealthConnectService.getAvailabilityDetail()` and the iOS `HealthKitService.getAvailability()` paths | NOT the values; just the availability code + raw status enum. |
| Audit-event store tail | `useAuditEventStore.getState().events.slice(-50)` | Already redacted per `IN_APP_AUDIT_SYSTEM.md`. |
| Build / repo identity | `expo-application` `nativeApplicationVersion` + `nativeBuildVersion` | Plus `EXPO_PUBLIC_GIT_COMMIT` env (when set at build time). |
| Approval-gate proof-row map | derived from the 3 gate stores + the readable Admin/Dev tile state | maps onto the P1–P8 schema in `ADMINDEV_INSTALLED_PROOF_GAP.md` § 3. |

### 2.2 Bundle output shape

```json
{
  "schemaVersion": 1,
  "capturedAt": "2026-05-09T12:00:00Z",
  "build": {
    "platform": "android",
    "versionCode": 21,
    "appVersion": "0.1.0",
    "channel": "internal_testing",
    "easBuildId": null,
    "repoCommit": "0991468"
  },
  "screenshots": [
    { "id": "admin-dev-now-section", "uri": "file:///.../audit-bundle/now.png" },
    { "id": "admin-dev-approval-gates", "uri": "file:///.../audit-bundle/approval-gates.png" }
  ],
  "adminDevSections": [
    { "title": "Now", "rows": [{ "label": "MCP", "value": "MCP live · fresh · 47s ago" }, ...] },
    ...
  ],
  "mcpSnapshot": { "projectCurrentState": { ... }, "releaseGate": { ... }, ... },
  "gateSnapshot": {
    "approvalGates": [{ "id": "...", "status": "...", "priority": "..." }],
    "spendGates": [...],
    "researchJobs": [...]
  },
  "healthConnect": { "availability": "available", "rawStatus": "SDK_AVAILABLE", "permissionsGranted": ["read_steps", "read_heart_rate"] },
  "auditEventTail": [...],
  "proof": { "p1_mcp_freshness": "pass", ... }
}
```

### 2.3 Sharing the bundle

Mobile→Agent flow:
1. Bundle written to `FileSystem.documentDirectory/audit-bundles/<isoDate>/`.
2. Aaron taps "Share audit bundle" → `expo-sharing` opens
   the OS share sheet with the JSON + screenshot folder zipped.
3. Aaron drops the zip into the agent chat.

Agent does NOT receive the bundle directly; Aaron is always
the courier (matches rule 7 — coders cannot claim shipped
without Aaron). The bundle is local-first; nothing posts to
public MCP.

### 2.4 Privacy

- Screenshots run through a tiny redactor before save: blur
  the email row in Admin/Dev (Supabase JWT email), the EAS
  Bearer if surfaced, the action-ledger raw token-shaped
  text. Reuse `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
  patterns.
- The bundle never carries raw user health values. Health-
  data screens are explicitly excluded from the v2 walk; v3
  covers them with explicit consent.
- Bundle TTL on-device: 30 days. After that the audit-bundle
  folder auto-prunes (job runs on Admin/Dev open).

## 3. v3 — Automated click-through (Maestro / Detox / Appium)

A repo-side test script that drives the installed app from a
laptop / CI runner. Captures every tab, every modal, every
expandable card. Lives outside the app binary; never ships in
production.

NOT shipped today. Implementation gate: bundle with the next
non-trivial admin-dev / QA change; OK to start as a single-
device Maestro flow before expanding.

### 3.1 Tooling decision

| Tool | Pros | Cons | Recommended? |
|---|---|---|---|
| **Maestro** | YAML flows, no native build flag, runs against installed APK/IPA, good for "drive an installed app". | Limited assertion vocabulary; can't read store state. | **Yes — start here.** Lowest overhead; works against the same APK Aaron's tester has. |
| Detox | React Native-native, excellent assertion API, can read app state. | Requires a Detox-instrumented build (extra EAS build profile); native config diverges from production. | Phase later — only if Maestro hits an assertion ceiling. |
| Appium | Cross-platform; works against truly unmodified apps. | Heaviest setup; flaky at modal/sheet boundaries. | No — too heavy for solo-operator scale. |

Plan: ship Maestro as the v3 surface. If we ever need to assert
zustand store state from the test (today we get it from the
app's "Capture audit bundle" button instead), revisit Detox.

### 3.2 Required flow scripts

`apps/mobile/audit-flows/` (NEW dir; gitignored under the
`apps/mobile/.gitignore` so the same path holds local-only
dev-client artifacts; Maestro flows themselves are checked
in). One YAML file per flow:

| File | Captures |
|---|---|
| `00-launch.yml` | Cold launch + sign-in (skipped on dev-client where the device is already signed). |
| `01-home.yml` | Home tab → screenshot → assert headline. |
| `02-health.yml` | Health tab → Manage Sources sheet → screenshot → close. |
| `03-train.yml` | Train tab → expand active session → close. |
| `04-feedback.yml` | Feedback tab → Daily Journal → Import Notes preview (if FS-020 bundle present) → close. |
| `05-map.yml` | Map tab → tap a known node → screenshot → back. |
| `06-reference.yml` | Reference tab → screenshot. |
| `07-syllabus.yml` | Syllabus tab → screenshot. |
| `08-coaching-history.yml` | Coaching history → screenshot. |
| `09-settings-admin-dev.yml` | Settings → Admin/Dev → walk every Section header → screenshot each. |
| `10-admin-dev-approval-gates.yml` | Admin/Dev → Approval gates Section → expand each row → screenshot. |
| `11-admin-dev-spend-gates.yml` | Admin/Dev → AI spend gates Section → expand each row → screenshot. |
| `12-admin-dev-research-offload.yml` | Admin/Dev → Deep Research offload Section → expand each row → screenshot. |
| `99-teardown.yml` | Sign out (optional) so the next run starts cold. |

Each flow runs Maestro `screenshot` after the relevant tap,
named `<flow>-<step>.png`. Output dir keyed by build identity
so a v20 run and a v21 run don't overwrite each other:
`./audit-out/<platform>/<versionCode>/<flowFile>/<step>.png`.

### 3.3 Local invocation

```
cd apps/mobile
maestro test audit-flows/01-home.yml         # single flow
maestro test audit-flows/                    # full suite
```

Pre-req: device connected via ADB (Android) or simulator
running with the installed IPA (iOS). Maestro picks the
default device.

CI invocation (later): GitHub Actions workflow
`audit-installed-device.yml` (NEW) runs Maestro against an
EAS-uploaded build artefact. Scope is reading-only — no
write tools fire — so the workflow is safe to run on any
push to `main`. Out of scope for this spec; Codex handoff in
§ 5.

### 3.4 Privacy

- Maestro flows must NEVER drive a sign-in form with a real
  Apple ID / Supabase email. Use a dedicated test account
  whose data stays inside QA.
- Screenshots blurred via the same redactor as v2 OR
  excluded from public surfaces by default. The audit-out
  directory is gitignored; nothing reaches the repo.
- Health-data screens captured ONLY in v3 with explicit
  test-account consent. Never against Aaron's real account.

## 4. Agent input package (canonical shape)

Used by all three tiers. Agent receives this bundle and
derives the proof-row decisions. Identical to the proof-JSON
in `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` § 3 plus the
capture-tier metadata.

```json
{
  "schemaVersion": 1,
  "captureTier": "v1" | "v2" | "v3",
  "platform": "android" | "ios",
  "build": {
    "versionCode": 21,
    "appVersion": "0.1.0",
    "channel": "internal_testing",
    "easBuildId": "<short>",
    "repoCommit": "<short SHA>"
  },
  "device": {
    "model": "iPhone 15 Pro" | "Pixel 8a",
    "osVersion": "iOS 19.0" | "Android 15"
  },
  "capturedAt": "<ISO>",
  "routes": ["(tabs)/index", "(tabs)/health", "..."],
  "screenshots": [
    { "id": "<flow-step>", "route": "(tabs)/...", "uri": "<file or attachment ref>" }
  ],
  "mcpSnapshot": { "projectCurrentState": ..., "releaseGate": ... },
  "adminDevSections": [...],
  "gateSnapshot": { "approvalGates": [...], "spendGates": [...], "researchJobs": [...] },
  "healthConnect": {
    "availability": "available" | "provider_update_required" | "sdk_unavailable" | "unknown",
    "rawStatus": "<SDK_AVAILABLE|...>",
    "permissionsRequested": ["...record types..."],
    "permissionsGranted": ["...record types..."],
    "lastError": "<string|null>",
    "lastPermissionAttemptAt": "<ISO|null>"
  },
  "appleHealth": {
    "available": true | false,
    "permissionsGrantedSummary": "<string|null>"
  },
  "auditEventTail": [...],
  "proof": { "p1_mcp_freshness": "pass" | ... },
  "notes": "<short Aaron note>"
}
```

Agent's ONLY response shape is the proof-row map + a short
required-fixes list. Agent does not invent rows; it can only
report `pass | partial | mismatch | missing_in_bundle |
not_tested` against the canonical P1–P8 catalogue.

## 5. Android v20 Health Connect QA — explicit requirements

The currently-installable Android tester build is v20 (EAS
`58071abc`, commit `3d7122c`). Aaron's outstanding
installed-device QA is the Health Connect Connect path. The
audit automation tier needed for that QA is **v1 today**:

1. Aaron screen-records the Health tab → Manage Sources →
   tap Connect on the Health Connect row.
2. Confirm: no crash; OS prompt OR Lauburu listed in the
   Health Connect "App permissions" list; debug card (admin/
   dev) shows last `permission_requested` timestamp + the
   requested record types.
3. Aaron's recording + the rung-3 MCP snapshot + the build
   identity travel to Agent in the v1 handoff package.
4. Agent records `AGENT_QA_RESULT_JSON` with `gate:
   release_gate, platform: android, installedBuild.versionCode:
   20, results.healthConnectConnectPath: pass|fail,
   results.adminDevHealthConnectDebugCard: pass|fail`.

If v20 fails the HC Connect retest:
- Aaron records the failure with the screen recording.
- Required-fixes list lands as a new ledger action; the
  next QA build (v21+) bundles the fix.
- v2 / v3 capture tiers do NOT unblock v20 — the existing
  v1 path is enough.

If v20 passes:
- gate-health-connectivity-phase-1 ledger action moves to
  `completed`.
- Aaron approves a v21 build that bundles FS-020 journal
  import + the gate centre commits per
  `ADMINDEV_INSTALLED_PROOF_GAP.md` § 6 follow-up.
- v21 is the first build where the FULL P1–P8 proof
  checklist can be exercised; v2 (Capture audit bundle
  button) ships in v21 if Aaron approves the additive
  surface.

## 6. Anti-rules

- **No production install of Maestro / Detox / Appium.**
  All three tools are dev / QA only. They never ship inside
  the production AAB / IPA.
- **No real-account sign-in inside automated flows.** v3
  scripts use a dedicated test account; v1 and v2 use
  Aaron's account but never post the recording / bundle to
  public MCP.
- **No raw user health values in any capture.** Screenshots
  go through the redactor; bundles flatten to availability +
  permission state, never values.
- **No Agent-side authoring of bundles.** Agent reads
  bundles; Agent never generates them. The bundle is
  produced by the device (v1 manual / v2 button / v3
  Maestro flow).
- **No bypass of the Aaron-approval gate.** Agent's proof
  output is advisory; Aaron approves any required-fixes
  ledger action through the existing approval-gate centre.

## 7. Codex handoffs

Each handoff fires only after Aaron approves the matching
tier. Bundle with the next non-trivial admin-dev change to
keep EAS build cost down.

### 7.1 v2 implementation handoff (semi-auto button)

> Implement the Admin/Dev "Capture audit bundle" button in
> `apps/mobile/app/admin-dev.tsx` per
> `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 2. Add
> `expo-screen-capture` (lazy-loaded so it falls back to
> tap-and-paste guidance on Expo Go), `expo-file-system`,
> `expo-sharing`. Capture the bundle JSON shape from § 2.2.
> Reuse the existing redactor in
> `cloudflare-worker/src/data/CONNECTOR_SANITIZATION_RULES.md`
> for screenshot blur. Anti-rules: no app code outside
> admin-dev.tsx + new utilities; no new MCP tools; no EAS
> build until Aaron approves; bundle TTL 30 days local.
> Tests: extend `cloudflare-worker/test/test-mcp-public-redaction.ts`
> to assert the audit-bundle redactor strips emails / tokens
> / device serials. Privacy contract test required.

### 7.2 v3 implementation handoff (Maestro)

> Add `apps/mobile/audit-flows/` per
> `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 3.2 with the 14
> Maestro YAML flows. Add a single npm script
> `npm run audit:installed -- --platform <android|ios>` that
> shells out to Maestro and writes screenshots into
> `./audit-out/<platform>/<versionCode>/<flow>/<step>.png`.
> Verify the suite runs end-to-end against the installed
> APK on Aaron's tester device. Anti-rules: no Detox; no
> Appium; no production app code change; no real-account
> sign-in inside flows; .gitignore the audit-out dir;
> health-data screens require explicit test-account consent
> before a flow lands. Tests: schema-validate one captured
> bundle against the Agent input package shape in § 4.

### 7.3 GitHub Actions CI handoff (v3, later)

> Add `.github/workflows/audit-installed-device.yml` per
> `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 3.3. workflow_dispatch
> only; downloads the latest EAS Android build artefact;
> runs the Maestro flow suite against an Android emulator
> in the runner; uploads the bundle as a workflow artefact.
> Read-only; no write tools fire. Skip if the artefact is
> the same as the previous run. Anti-rules: workflow does
> NOT post the bundle outside the GitHub artefact (no
> Slack, no Drive). Bundle TTL 30 days per GitHub default.

## 8. Cross-references

- `docs/IN_APP_AUDIT_SYSTEM.md` — the local audit-event
  store this spec piggybacks on.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — proof checklist
  P1–P8 + screenshot capture spec the bundle JSON mirrors.
- `docs/MCP_LONGTERM_ACCESS_ARCHITECTURE.md` § 5 — fallback
  workflow where Agent reads Admin/Dev visually until
  Surface B ships.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — installed
  bundle identity (v20 today).
- `docs/AGENT_AUDITS.md` — process for Aaron-pasting Agent
  audit results back to the bridge.
- `docs/SIMULATOR_QA_AUDIT_HARNESS.md` — earlier simulator
  harness; complementary, not a substitute, since
  installed-device behaviour can diverge from the simulator.
- `docs/CONNECTOR_SANITIZATION_RULES.md` — redaction
  patterns reused in v2 + v3 capture redaction.
