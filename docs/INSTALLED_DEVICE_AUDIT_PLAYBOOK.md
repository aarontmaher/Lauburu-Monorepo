# Installed-device audit playbook (operator side)

The **decision tree** for installed-device QA audits — when
to run one, who runs it, what to capture, how to interpret,
how to record `AGENT_QA_RESULT_JSON`. Pairs with Codex's
coder-side tooling:

- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — three-tier
  capture taxonomy (v1 screen-record / v1.5 simulator script
  / v2 in-app button / v3 Maestro automation).
- `npm run audit:screenshots` — simulator/emulator capture
  with manifest contract.
- (Forthcoming) iPhone Mirroring capture flow at
  `scripts/iphone-mirroring-audit.mjs` + companion doc — see
  `CODEX-IPHONE-MIRRORING-AUDIT-CAPTURE-01` (Codex's queued
  prompt as of this commit).

This playbook is **operator-side**: it tells Aaron (or a
delegated tester) WHAT to do, WHEN, and HOW to record
results. It does not cover capture-tool internals — those
live in the docs above.

This is **doc only**. No app code. No EAS build.

## 0. Audit gate types

Six distinct gates that may require an installed-device audit.
Each has its own capture set + AGENT_QA template.

| Gate | When | Capture set | Pass criterion |
|---|---|---|---|
| **A. Release gate** (canonical) | Before clearing `release_gate` for a Play Internal / TestFlight build. Currently active for Android v20 + iOS build 19. | Full 9-screen set (Codex's v1.5 + manual screen-record where Health Connect interactivity matters). | `agent_qa_result.json` flips `status=pass` + `releaseGate.newAndroidBuildAllowed=true` (or iOS equivalent). Recorded in `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § AGENT_QA template. |
| **B. FS-XXX functional confirmation** | When a coder reports `Implementation-complete, awaiting Agent functional confirmation` for an FS-XXX candidate per rule 4. | Targeted screens only — the screens that exhibit the new feature. | Agent confirms behaviour matches spec; FS-XXX moves to `Agent-confirmed, ready for Aaron approval` per rule 5. |
| **C. Forever Improve drift check** | Quarterly (or on Aaron request). Scans for drift from the quality bars in `docs/APP_DEVELOPMENTS.md` § Permanent improvement categories. | Per-category screens (e.g. for Mobile-only admin: admin-dev tab, approval centre, push toggles). | One-line freshness note per category; flag any drift; surface as candidate FS-XXX bundles. |
| **D. Health Connect crash retest** | Specifically the v18-crash repro (rule-9 truthfulness on Android Health Connect → Connect tap). | Health / Manage Sources / Health Connect → Connect specifically. v20 also: Open Health Connect button + debug card. | No crash + state pills render truthfully + debug card surfaces SDK availability + `permission_requested` timestamp + granted metrics + last error. |
| **E. iOS TestFlight build install audit** | After a new TestFlight build is processed. | Auth flow / Apple Health permission grant / Manage Sources state pills / Grappling Readiness copy / admin-dev gating. | All screens render correctly + no Apple-Health-Android wording / no Android Health-Connect-on-iOS wording (mixed-platform copy bug check). |
| **F. Pre-EAS-build sanity** | Before approving a NEW EAS build (rule 7). | Smoke check on the previous installed build to confirm it's not silently broken (otherwise we burn EAS credits on a build the previous gate didn't actually clear). | All previously-passing screens still render + no regressions. |

## 1. Capture method by gate type

Three capture methods are available; choose the cheapest that
covers the gate's needs.

| Method | Output path | When to use | Cost | Privacy notes |
|---|---|---|---|---|
| **Simulator script** (`npm run audit:screenshots`) | `artifacts/app-audit/<isoTimestamp>/` | Gate B (FS-XXX confirm), Gate C (Forever Improve drift), Gate F (pre-build sanity). Anything that doesn't require real-device sensors. | Free; runs locally. | Synthetic data; no real Aaron data on screen. |
| **iPhone Mirroring** (macOS 15+ Continuity feature) | `artifacts/app-audit/iphone-mirroring/<timestamp>/` | Gate B / C / E when the screen needs to come from the real installed app but no real-device-only sensor is required. Aaron's iPhone shows on Mac; Cmd-Shift-4 captures any window. | Free; built into macOS 15+. | Real Aaron data on screen — redact before sharing. Manifest must flag `containsRealUserData: true`. |
| **iPhone screen-record** (real device, on-device) | `artifacts/app-audit/iphone-screen-record/<timestamp>/` | Gate A (release gate, canonical), Gate D (Health Connect crash retest — needs to actually trigger the OS-level Connect flow on iOS) [iOS-equivalent of the Android Health Connect tap]. The only path that captures full live iOS behaviour including OS prompts. | Free; built into iOS. | Real data + OS prompts — redact before sharing. |
| **Android scrcpy** (real device, USB → Mac) | `artifacts/app-audit/scrcpy/<timestamp>/` | Gate A + Gate D (Android Health Connect → Connect tap). Real-device equivalent on Android. | Free; `brew install scrcpy` one-time setup. | Real data on screen — redact before sharing. |

The iPhone Mirroring path is the **default cheap path** for
most non-real-sensor audits — it's the lowest-friction way to
get real installed-app screens onto the Mac without USB cables
or dev certs.

## 2. Operator preflight

Before any audit run:

1. **MCP-first** (rule 11). Read `project.get_current_state`
   on the phone Admin/Dev tab or via ChatGPT MCP. Confirm:
   - `freshness: fresh` — if stale, run `bridge:snapshot`
     from the laptop or skip non-blocking audit.
   - Repo HEAD matches the installed build's commit.
2. **Confirm installed build identity.** Open the app →
   Settings (or Admin/Dev) → version pill. Cross-check
   against the gate doc:
   - Android: `versionCode` (per
     `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § Build
     identifiers — currently v20 active).
   - iOS: `buildNumber` (currently 19).
3. **Aaron-paused decisions.** Check
   `docs/APP_DEVELOPMENTS.md` priority order for any
   "Aaron-paused" rows that explicitly defer this audit.
4. **Privacy review.** If the audit will capture screens
   with Aaron's real data (journal text, health metrics,
   PII), pre-decide redaction strategy: blur on-device, crop
   before sharing, or capture a fresh test account on the
   simulator.

## 3. Execution

### 3.1 Simulator script (cheapest path)

```sh
# Boot iOS simulator (or Android emulator) with the installed dev build
npx expo run:ios --device "iPhone 16 Pro"
# Then in another terminal:
npm run audit:screenshots
# Follow on-screen prompts; manifest.json + PNGs land in artifacts/app-audit/...
```

For Android emulator, swap the boot step for `npx expo
run:android` against a running AVD.

### 3.2 iPhone Mirroring

(Codex's CODEX-IPHONE-MIRRORING-AUDIT-CAPTURE-01 ships the
full setup + helper script. This playbook references the
pattern.)

1. macOS 15+ on the Mac; iCloud signed-in matching the
   iPhone.
2. Open **iPhone Mirroring.app** on the Mac. Approve on the
   iPhone the first time.
3. Tap through target screens in the mirrored window.
4. Cmd-Shift-4 → window pick → save to the configured
   capture folder.
5. Run `npm run audit:iphone-mirroring` (when shipped) to
   move PNGs into `artifacts/app-audit/iphone-mirroring/<timestamp>/`
   and generate `manifest.json`.

### 3.3 Android scrcpy (real device, USB)

For Android real-device captures with no Continuity
equivalent. Mac-side mirroring + screenshot capture.

```sh
# One-time install (Mac):
brew install scrcpy

# Plug Android device via USB. On the device: Settings →
# About phone → tap Build number 7 times → Developer
# options → enable USB debugging. First connect prompts a
# pairing dialog on the device.

# Mirror + record full session:
scrcpy --record artifacts/app-audit/scrcpy/<isoTimestamp>/session.mp4

# OR per-screen screenshots (faster, no mirroring window):
adb -s <serial> exec-out screencap -p > screen.png
```

scrcpy outputs an `.mp4` of the entire mirrored session;
extract per-screen PNGs in post via `ffmpeg -ss <ts> -frames:v 1 ...`.
For repeatable per-screen captures, prefer `adb exec-out
screencap` driven by a small Bash script (Codex follow-up
in the Maestro spec § 7 covers this case at the v3 tier).

Output path: `artifacts/app-audit/scrcpy/<timestamp>/`.

Privacy: same as iPhone Mirroring — real-user data on
screen; redact before sharing.

### 3.4 iPhone screen-record (real device)

Used when the audit needs OS-level prompts captured (Health
permission grants, Health Connect → Connect crash repro).

1. On iPhone: Settings → Control Centre → Add **Screen
   Recording**.
2. Open the app from the home screen (do NOT use the dev /
   debug build — use the installed TestFlight / Play
   Internal build).
3. Swipe down Control Centre → tap Record.
4. Tap through the target flow.
5. Stop recording; AirDrop the .mov to the Mac.
6. Drop into `artifacts/app-audit/iphone-screen-record/<timestamp>/`
   manually + add `manifest.json` (template in
   `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § AGENT_QA
   template — same shape).

## 4. Target screens per gate

### Gate A (release) — canonical 9-screen set

1. Home / Coach
2. Train (with active session if available)
3. Map (3D taxonomy)
4. Health (Manage Sources)
5. Grappling Readiness (with truthful copy)
6. Journal / Feedback (Track-Something entry point)
7. Settings (top of stack)
8. Admin/Dev top (priority + lane chips)
9. Admin/Dev MCP freshness pill + writeback cadence

Plus (Android v20 specifically): Health Connect → Connect tap
flow recorded as a screen recording (the v18 crash repro path).

### Gate B (FS-XXX functional confirm)

Targeted to the FS-XXX scope. Only the screens the FS-XXX
batch touched. Listed in the FS-XXX card's "Acceptance
criteria" section.

### Gate C (Forever Improve drift)

One screen per category from `docs/APP_DEVELOPMENTS.md`
§ Permanent improvement categories. Confirms each category's
quality bar still holds.

### Gate D (Health Connect crash retest)

Screen recording — must capture the live tap on Connect to
prove no crash. Plus Admin/Dev → Owner alerts → Health
Connect debug card (admin-dev-only on v20+) showing the
last `permission_requested` timestamp + granted metrics.

### Gate E (iOS TestFlight install)

Auth flow (sign-up / sign-in, including the Settings
auth-param consumption from FS-019) + Apple Health permission
prompt + Manage Sources pills + Grappling Readiness copy +
admin-dev gating verification.

### Gate F (pre-EAS sanity)

Smoke screens only: Home / Health / Settings / Admin/Dev top.
Confirms no regression on the existing build before burning
credits on a new one.

## 5. Interpretation rubric

Each captured screen is judged against:

| Check | Pass means | Fail means |
|---|---|---|
| **Render correctness** | Screen renders without crash, no missing labels, no overlapping text. | Visual bug; flag with screenshot + screen name; FS-XXX candidate. |
| **Copy truthfulness** (rule 9) | Hedge language only ("provisional", "low confidence", "associated with"); no overclaiming. | Over-claiming language found; flag for copy fix. |
| **Cross-platform purity** | iOS-only words on iOS / Android-only words on Android — no "Apple Health" wording on Android, no "Health Connect" wording on iOS. | Mixed-platform string bug; flag with line + file. |
| **Auth gating** | Admin-only surfaces visible only when admin email is signed in; public-safe surfaces visible without sign-in. | Auth leak; STOP audit; flag as security concern. |
| **MCP freshness pill** | Pill shows `fresh` (or `stale: <reason>` truthfully); never silently shows "fresh" with no underlying writeback. | Stale-but-claiming-fresh = canonical-state divergence; flag. |
| **No PII / secret leak** | No tokens, no secrets, no other users' data on screen. | Found leak; STOP audit; flag immediately. |

## 6. Recording AGENT_QA result

After capture + interpretation:

1. Run `npm run bridge:agent-qa` interactively.
2. Choose `gate` matching the audit type:
   - Gate A → `release_gate`
   - Gate B → `fs_xxx_functional` (with FS id)
   - Gate C → `forever_improve_drift`
   - Gate D → `health_connect_crash_retest`
   - Gate E → `ios_testflight_install`
   - Gate F → `pre_eas_sanity`
3. Provide `installedBuild.androidVersionCode` or
   `installedBuild.iosBuildNumber` from the operator
   preflight § 2.
4. Record `status: pass | partial | fail`.
5. `evidence.screenshotRefs` should reference the local
   capture folder manifest path. Path conventions per Codex's
   shipped scaffolding:
   - Simulator script (`npm run audit:screenshots`):
     `artifacts/app-audit/<isoTimestamp>/manifest.json`.
   - iPhone Mirroring (forthcoming `npm run audit:iphone-mirroring`):
     `artifacts/app-audit/iphone-mirroring/<timestamp>/manifest.json`.
   - iPhone screen-record (manual): `artifacts/app-audit/iphone-screen-record/<timestamp>/manifest.json`.
   Screenshots themselves stay LOCAL — the ref is path-only,
   never a public URL.
6. `evidence.notes` describes any flags from § 5.
7. The bridge writes `data/agent-status/lanes/agent_qa_result.json`
   and the next `bridge:snapshot` propagates to MCP.

For Gate A specifically, follow the AGENT_QA template in
`docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § AGENT_QA
template (Android v20).

## 7. Fallback paths

When the primary capture path fails:

- **Simulator script fails to boot:** check `xcrun simctl
  list devices`; clear stale instances; rebuild dev client
  via `npx expo run:ios --clear`. Document the failure in
  the audit notes.
- **iPhone Mirroring unavailable** (macOS <15 / iCloud
  mismatch): fall back to iPhone screen-record + AirDrop.
- **AirDrop unavailable:** save recording to Files →
  iCloud Drive → pull on the Mac.
- **TestFlight build not yet processed:** wait for Apple
  processing; do NOT audit a development simulator build as
  a substitute for the real installed-device audit (Gate A
  fail criterion).
- **Real device unavailable** (lost / drained / borrowed):
  skip Gate A + record `status: partial` with reason. Other
  gates may proceed via simulator.

## 8. Anti-rules

- **No commits of `artifacts/`.** All capture output is
  local; `.gitignore` excludes the tree.
- **No public sharing of raw captures.** Even Agent review
  receives redacted versions where real-user data is on
  screen.
- **No auto-promotion of `partial` to `pass`.** Each AGENT_QA
  status reflects what was actually observed; never inflated
  to clear a gate.
- **No simulator evidence for Gate A.** Release gate requires
  real-device evidence (this rule is canonical in
  `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` § Gate rule).
- **No EAS build dispatched from this playbook.** Audits
  inform the build decision; they don't trigger one.
- **No silent skip of MCP-first preflight.** If MCP is
  unavailable, follow rule 11's stop-or-fallback-mode
  contract; do not audit blindly.

## 9. Cross-references

- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — coder-side
  capture tooling (v1 / v1.5 / v2 / v3 tiers).
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — Gate A
  canonical spec + AGENT_QA template + Play / TestFlight
  upload click paths.
- `docs/APP_DEVELOPMENTS.md` § Permanent improvement
  categories — Forever Improve quality bars referenced in
  Gate C drift checks.
- `docs/OPERATING_RULES.md` § 4 / § 5 / § 6 — re-audit on
  implementation-complete; Agent-confirmed gate;
  agent-not-confirmed = investigate.
- `docs/OPERATING_RULES.md` § 11 — MCP-first preflight.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 push gate
  for any audit-discovered approval needed.
