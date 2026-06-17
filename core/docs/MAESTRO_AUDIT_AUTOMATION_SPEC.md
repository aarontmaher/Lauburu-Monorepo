# Maestro audit automation spec

The v3 capture tier referenced in `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md`.
Maestro auto-navigates every safe tab / card / modal,
captures screenshots, and outputs a manifest matching the
existing `audit-screenshots.mjs` schema.

This is **spec only**. No app code. No EAS build.
Implementation is a Codex follow-up batch gated on Aaron
approval per rule 7 + rule 13.

## 0. Where this fits

Three capture tiers exist today:

| Tier | Tool | Navigation | Screenshot | Manifest | Status |
|---|---|---|---|---|---|
| v1 | iPhone screen-record | Aaron taps | Aaron records video | None today | Manual (`docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 1) |
| v1.5 | `npm run audit:screenshots` | Aaron taps | Auto via `xcrun simctl io <udid> screenshot` | Auto JSON | Shipped (`fc8d7c3` + `docs/AUDIT_SCREENSHOTS.md`) |
| v2 | "Capture audit bundle" admin-dev button | App-internal | App-internal | App-internal | Spec only (`docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 2) |
| **v3** | **Maestro** | **Auto-navigate via flow file** | **Auto** | **Auto** | **THIS spec** |
| iPhone Mirroring (orthogonal) | macOS Continuity | Aaron taps | Aaron Cmd-Shift-4 | Auto via `npm run audit:iphone-mirroring` | Shipped (`412dab2` + `docs/IPHONE_MIRRORING_QA_WORKFLOW.md`) |

Maestro is the **highest-leverage audit path** for non-real-
device gates: zero human taps, full coverage, repeatable.
It does NOT replace iPhone Mirroring or screen-record for
gates that need OS-level prompts (Apple Health permission,
Health Connect → Connect crash repro) — Maestro can't drive
OS dialogs on iOS in unsigned builds.

## 1. What Maestro is + why this stack

**Maestro** (https://maestro.mobile.dev) is a YAML-driven
mobile UI testing tool. Distinct advantages over Detox /
Appium / Earl Grey for our use case:

- **No app code instrumentation.** Maestro drives the live
  app via accessibility identifiers + on-screen text +
  coordinates. No test runner injected into the bundle.
- **Cross-platform.** Same flow file runs on iOS Simulator
  (or real device with USB) and Android Emulator (or USB).
- **Screenshot-first.** `takeScreenshot` is a primitive
  step type — output goes to a per-flow folder.
- **Single binary.** `brew install maestro` + a Java
  runtime; no Xcode test targets / no Pods changes / no
  Gradle modifications.
- **Maintainable YAML.** Flow files are readable + diffable.

The trade-off vs simpler `xcrun simctl` driving: Maestro
needs a one-time install + a Java runtime. The v1.5 script
needs nothing but Xcode CLI tools. So we run BOTH in
production: v1.5 for "Aaron drives" mode + v3 Maestro for
"hands-off" mode.

## 2. Install + setup

### 2.1 macOS install

```sh
brew install maestro
# ~30s install; depends on Java (brew installs OpenJDK if missing).
maestro --version
# Should print 1.x.y
```

Verify against a booted simulator:

```sh
xcrun simctl boot "iPhone 16 Pro"
maestro hierarchy   # prints UI tree of foreground app — sanity check
```

### 2.2 Project-side files

`maestro/` directory at repo root, gitignored except for the
flow files themselves:

```
maestro/
  audit-flows/
    auto-click-through.yaml          # canonical 9-screen capture
    journal-import.yaml              # FS-020 verification
    approval-centre.yaml             # rule 21+22+23 verification
    grappling-readiness.yaml         # rule 9 + Forever Improve
  helpers/
    boot-sim.sh                      # boots a known-good simulator
    capture-bundle.sh                # wraps a flow + writes manifest
  artifacts/                          # gitignored; per-run output
    .gitkeep
```

`.gitignore` already excludes `artifacts/`; the new
`maestro/artifacts/` is also covered.

### 2.3 npm script

```json
{
  "scripts": {
    "audit:maestro": "bash maestro/helpers/capture-bundle.sh",
    "audit:maestro:journal": "bash maestro/helpers/capture-bundle.sh journal-import",
    "audit:maestro:approvals": "bash maestro/helpers/capture-bundle.sh approval-centre"
  }
}
```

## 3. Auto-click-through flow

The canonical 9-screen capture flow (`maestro/audit-flows/auto-click-through.yaml`):

```yaml
appId: com.lauburu.grapplingmap
---
- launchApp:
    clearState: false   # use whatever account is signed in
    stopApp: true       # ensure cold start

# Wait for home tab to render
- assertVisible: "Coach"        # tab label
- takeScreenshot: 01-home.png
- back

# Train tab
- tapOn: "Train"
- assertVisible: "Train"
- takeScreenshot: 02-train.png

# Map tab
- tapOn: "Map"
- assertVisible: "Map"
- takeScreenshot: 03-map.png

# Health tab
- tapOn: "Health"
- assertVisible: "Health"
- takeScreenshot: 04-health.png

# Health → Manage Sources
- tapOn: "Manage Sources"
- assertVisible: "Sources"
- takeScreenshot: 05-manage-sources.png
- back

# Health → Grappling Readiness card
- assertVisible:
    text: "Readiness"
    optional: true
- runFlow:
    when:
      visible: "Readiness"
    file: ../helpers/screenshot-readiness.yaml

# Journal / Feedback tab
- tapOn: "Feedback"
- assertVisible: "Feedback"
- takeScreenshot: 07-journal-feedback.png

# Settings tab
- tapOn: "Settings"
- assertVisible: "Settings"
- takeScreenshot: 08-settings.png

# Admin/Dev (only if admin email signed in)
- runFlow:
    when:
      visible:
        text: "Admin/Dev"
        optional: true
    file: ../helpers/screenshot-admin-dev.yaml
```

The screen IDs (`01-home`, `02-train`, etc.) match
`scripts/audit-screenshots-helpers.mjs` `AUDIT_SCREENS`
catalogue exactly. Manifest schema reuse is automatic.

## 4. Manifest output

Wrapper script `maestro/helpers/capture-bundle.sh` runs the
flow + writes `manifest.json` matching the existing schema:

```json
{
  "schemaVersion": 1,
  "captureMethod": "maestro_v3",
  "captureFlow": "auto-click-through.yaml",
  "iosBuildNumber": "19",
  "androidVersionCode": 20,
  "appVersion": "0.1.0",
  "device": "iPhone 16 Pro Simulator (iOS 18.2)",
  "platform": "ios",
  "capturedAt": "2026-05-09T02:30:00Z",
  "repoBranch": "main",
  "repoShortHead": "<sha>",
  "screens": [
    { "filename": "01-home.png",   "screen": "home",   "captureTimestamp": "..." },
    ...
  ],
  "containsRealUserData": true,
  "redactionRequired": true,
  "notes": ""
}
```

Output: `maestro/artifacts/<isoTimestamp>/` mirroring the
`audit-screenshots` script convention.

## 5. Real-device-only gates (Maestro skip list)

Maestro CANNOT drive these because they hit OS-level
permission prompts:

| Gate | Why Maestro skips |
|---|---|
| Apple Health permission grant (iOS) | OS-level prompt isn't accessible to Maestro on unsigned builds. Real device + screen-record OR signed Maestro Cloud run required. |
| Health Connect → Connect tap (Android) | Same — Health Connect's authorisation activity is OS-level, not in-app. Real device + screen-record required for Gate D. |
| Push notification action (Approve / Defer / Deny on lock screen) | Lock-screen action UI isn't part of the app process. Real device + manual capture required. |
| FaceID / TouchID prompts | OS-level. Skip. |
| iOS Settings deep-link verification (`UIApplication.openSettingsURLString`) | Leaves app process. Skip. |
| Apple Sign In auth flow | Apple-side modal; not driveable by Maestro on simulators. Real device required. |

Maestro flows that touch any of these MUST log a `skippedReason`
in manifest + the operator follows up via real-device capture
per `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` § 1 (iPhone
Mirroring or screen-record).

## 6. Per-gate flow files

In addition to `auto-click-through.yaml`, ship targeted
flows for the high-leverage gates:

### 6.1 `journal-import.yaml`

For Gate B (FS-020 functional confirmation):
1. Open Feedback tab → Track-Something.
2. Tap "Import journal data" entry point.
3. Paste a synthetic journal block (loaded from
   `cloudflare-worker/test/fixtures/journal-import-synthetic-fixtures.ts`
   via Maestro's `inputText` step).
4. Tap "Preview".
5. Capture screenshot of preview rows.
6. Verify ≥1 sensitive-category row shows "needs
   confirmation".
7. Cancel out (don't save real data).

### 6.2 `approval-centre.yaml`

For Gate C (Forever Improve drift) + § 4 of the proof
checklist:
1. Sign in with admin account (test fixture).
2. Open Admin/Dev → Approval centre.
3. If pending gates exist: capture the panel.
4. Capture deferred / approved-last-7d / blocked sections.
5. Tap a synthetic gate's "Approve" button (test gate
   only; never a real gate).

### 6.3 `grappling-readiness.yaml`

For rule 9 verification:
1. Open Health → Grappling Readiness card.
2. Capture the card with all hedge labels visible.
3. Run `assertVisible` checks for banned phrases:
   - SHOULD NOT see: "you are ready", "skip training",
     "guaranteed", "definitely".
   - SHOULD see one of: "provisional", "low confidence",
     "not enough data yet", "needs more observations".
4. Capture missing-data state (when applicable).

## 7. Codex handoff prompt — implementation

**Status update (2026-05-09):** Codex shipped a substantial
slice of this spec in commit `ce62e90` ("QA: Phase 3 audit
automation — Maestro flows + scrcpy Android helper") — 14
Maestro YAML flows under `apps/mobile/audit-flows/` (00-launch
through 99-teardown), `scripts/audit-maestro.mjs` wrapper
with manifest output to `artifacts/app-audit/maestro/<isoTimestamp>/`,
and `scripts/audit-android-scrcpy.mjs` for the real-Android
companion path. The handoff prompt below is preserved as a
historical reference + as the contract any follow-up batch
must continue to honour.

Stored as ready-to-paste. Aaron MUST explicitly approve
dispatch before this prompt goes to Codex.

```
PROMPT-ID: CODEX-FS-XXX-MAESTRO-AUDIT-AUTOMATION-IMPL-01
TYPE: CODEX
LANE: Audit automation / Maestro flow files + helper scripts

MCP-FIRST: call project.get_current_state. Bridge → Supabase
direct upsert is LIVE; bridge:snapshot for end-of-task cadence
per rule 12.

Reference (read first):
- docs/MAESTRO_AUDIT_AUTOMATION_SPEC.md (this doc — canonical).
- docs/IN_APP_AUDIT_AUTOMATION_SPEC.md (v1/v1.5/v2/v3 tier
  taxonomy).
- docs/AUDIT_SCREENSHOTS.md (v1.5 manifest contract — Maestro
  output reuses this schema).
- docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md (operator decision
  tree).

GOAL
Wire the Maestro v3 audit tier:
- maestro/ directory + audit-flows/ + helpers/ scaffold.
- 4 flow files: auto-click-through, journal-import,
  approval-centre, grappling-readiness.
- helper scripts: boot-sim, capture-bundle.
- npm scripts: audit:maestro, audit:maestro:journal,
  audit:maestro:approvals.
- Schema-locked manifest test extension.

SCOPE PHASE 1 (this prompt)
1. Maestro install verification helper:
   maestro/helpers/check-install.sh — fails fast with
   install instructions if maestro CLI missing.
2. Boot helper: maestro/helpers/boot-sim.sh — boots
   "iPhone 16 Pro" simulator OR a configured Android
   emulator; idempotent.
3. Capture bundle wrapper: maestro/helpers/capture-bundle.sh
   <flowName?> — runs flow + collects PNGs + generates
   manifest.json reusing scripts/audit-screenshots-helpers.mjs
   buildManifest pure function for schema parity.
4. Flow files per § 3 + § 6:
   - audit-flows/auto-click-through.yaml (9 screens).
   - audit-flows/journal-import.yaml (Gate B / FS-020).
   - audit-flows/approval-centre.yaml (Gate C / § 4).
   - audit-flows/grappling-readiness.yaml (rule 9).
5. Sub-flow helpers (called via runFlow):
   - helpers/screenshot-readiness.yaml.
   - helpers/screenshot-admin-dev.yaml (admin-only path).
6. .gitignore: maestro/artifacts/.
7. package.json scripts.
8. Schema test extension: lock the captureMethod="maestro_v3"
   variant in cloudflare-worker/test/test-audit-screenshots-manifest.ts.

ANTI-RULES
- No app code change (no accessibility identifiers added at
  this stage; rely on visible text + Maestro's automatic
  hierarchy detection). Future FS-XXX may add accessibility
  ids if flows prove brittle.
- No EAS build.
- No real-device-only gate driving (Apple Health permission /
  Health Connect Connect / push action / FaceID). Each
  flow MUST skip + log skippedReason where appropriate.
- No raw Aaron-account fixture in committed flow files.
  Use synthetic test fixtures (already in
  cloudflare-worker/test/fixtures/).
- artifacts/ never committed; manifests local-first.
- npm run rules:test PASS (23 rules unchanged).
- npm run mcp:test:public-redaction PASS.

VERIFICATION
- maestro/helpers/check-install.sh PASS on a Mac with
  maestro installed; exits with install instructions
  otherwise.
- Manual: boot iOS sim + run maestro test
  maestro/audit-flows/auto-click-through.yaml; confirm 9
  screenshots land in maestro/artifacts/<isoTimestamp>/ +
  manifest.json validates against the locked schema.
- Manual: same against Android emulator.
- Manual: confirm flow handles missing admin-dev access
  gracefully (sub-flow runs only if visible).
- bridge:snapshot at end-of-task.

OUTPUT (small)
- Status: implementation-complete-awaiting-Agent-confirmation
  / partial / blocked
- Maestro install verified: yes / no
- New files added (4 flow + 3 helper + 1 npm script):
- Existing files touched:
- Tests run:
- MCP / bridge writeback evidence:
- Open questions for Aaron / Agent confirmation:
- Recommendation for follow-up (FS-XXX next batch — e.g.
  Maestro Cloud signed-build run for real-device-only
  gates):
```

Approval-gated: do NOT dispatch this prompt without Aaron's
explicit approval per rule 7 + rule 13.

## 8. Anti-rules

- **No accessibility-id pollution at v3.** Flows rely on
  visible text + hierarchy. Adding `accessibilityIdentifier`
  to RN components is a future FS-XXX if flows prove
  brittle.
- **No real-device-only gate driving.** Maestro skips per
  § 5 list; operator runs those manually.
- **No fixture-account credentials in flow files.** Test
  fixtures only.
- **No EAS build dispatched from Maestro.** Audits inform
  the build decision; they don't trigger it.
- **No artifacts/ committed.** Local-first; gitignored.
- **No silent flow regressions.** Every commit that touches
  a flow file MUST link to a fresh successful manifest
  run.

## 9. Cross-references

- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — v1/v1.5/v2/v3
  taxonomy.
- `docs/AUDIT_SCREENSHOTS.md` — v1.5 manifest schema this
  doc reuses.
- `docs/INSTALLED_DEVICE_AUDIT_PLAYBOOK.md` — operator
  decision tree; § 5 fallback paths.
- `docs/IPHONE_MIRRORING_QA_WORKFLOW.md` — the orthogonal
  real-device path.
- `docs/AGENT_AUDIT_BUNDLE_SPEC.md` — what gets bundled
  for Agent review (consumes Maestro output).
- `docs/ADMIN_DEV_PROOF_CHECKLIST.md` — § 4-6 rows that
  Maestro can verify automatically.
- `docs/EVIDENCE_DRIVEN_TECHNIQUE_EVOLUTION_SPEC.md` —
  audit-trail discipline that Maestro outputs feed into.
