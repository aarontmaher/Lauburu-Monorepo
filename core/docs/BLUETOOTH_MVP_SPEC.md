# Bluetooth MVP — repo-backed spec

The smallest, safest Bluetooth (BLE) feature that earns its
place in the app. Train-session data only. No readiness scoring,
no native rebuild that adds risk to the existing tester pipeline,
no privacy gap.

This doc is **spec only**. No BLE implementation lands in the
same commit. No mobile UI changes. No native dependency added.
Code-side work is gated on a separate owner-approved batch per
the candidate workflow in `docs/FEEDBACK_SUGGESTIONS.md`.

Companion to:
- `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md` (existing wearable
  audit; this doc explicitly does NOT contradict it)
- `docs/HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md`
- `docs/WHOOP_POLAR_SYNC_STRATEGY.md`
- `docs/POST_MCP_PRODUCT_LANES.md` (Lane B Grappler Readiness
  gates this work — readiness data does NOT come from BLE in
  the MVP)
- `docs/CONNECTOR_SANITIZATION_RULES.md` (the same redactor
  rules apply to anything BLE-adjacent that flows into the
  control-centre / MCP surface)
- `docs/PRIVACY.md`

Updated 2026-05-07.

## 1. Scope

**The MVP exposes one BLE feature:** read live heart rate from a
standard Bluetooth Heart Rate Service (HRS, GATT service UUID
`0x180D`) into the **Train tab session log**. That's it.

This is intentionally narrow. It earns the right to ship by:

- Using the universally-supported HRS profile (chest straps,
  watches, even some smartwatches in broadcast mode), not a
  vendor-specific protocol.
- Writing to the existing `TrainingSession` schema on
  Aaron's device only — no per-user backend write, no MCP
  surface, no readiness compute consumption.
- Adding zero new native dependencies beyond what
  `react-native-ble-plx` (or equivalent expo-ble plugin) needs;
  the choice is documented in § 5 but the dependency does NOT
  ship in this spec commit.

**The MVP does NOT do:**

- Vendor-specific Polar protocols (HR-only via HRS works for
  most Polar devices; deeper RR / HRV / temp / ECG comes via
  vendor SDK and is not in scope).
- Garmin BLE.
- Any wearable that requires a paired smartphone app to relay
  data (that's a "via hub" path, not BLE).
- Background BLE scanning. Foreground only, while the Train
  tab session is live.
- BLE writes (no firmware updates, no characteristic writes).
- Pushing BLE data into readiness scoring or the
  `normalized_daily_metrics` Supabase table.

## 2. Why Train-session first, not readiness

Readiness wants smoothed, multi-day, provenance-tagged metrics.
HR mid-roll is too noisy and too BLE-availability-dependent
to feed readiness without a full sensor-fusion design that's
well outside MVP scope. Putting BLE on the Train tab keeps the
contract simple:

- **Train tab → BLE HR is a session signal.** Aaron sees his
  HR while drilling / sparring, and the session log records
  the time-series (or a compact summary). Missing HR doesn't
  break the session — the existing manual perceived-intensity
  field stays the source of truth for grappling load.
- **Health tab is unaffected.** Apple Health / Health Connect
  remain the canonical source for resting HR, HRV, sleep, and
  recovery proxies. BLE HR does NOT write into either of those
  hubs.
- **Readiness is unaffected.** Per
  `docs/POST_MCP_PRODUCT_LANES.md` Lane B, readiness UI is
  gated on Lane A (Apple Health / Health Connect reliability)
  and ships with explicit per-bucket provenance. BLE HR is
  *not* a readiness bucket — it's a session datum.

This separation is the point of the spec. If BLE later proves
itself across many sessions, a future spec batch can argue for
promoting BLE-derived metrics into the recovery layer with
explicit `provenance: 'bluetooth_hr'` tags. That batch is NOT
this one.

## 3. Source labels (for any UI that surfaces HR)

| Label | Meaning | Status |
|---|---|---|
| **Apple Health hub** | iOS HealthKit aggregating from any of Apple's accepted sources (Apple Watch, third-party app writing to HealthKit) | live (existing) |
| **Health Connect hub** | Android Health Connect aggregating from any registered source app | live (existing) |
| **Polar via hub** | Polar Flow → Apple Health / Health Connect bridge (data appears under Apple Health / Health Connect) | live (existing) |
| **Polar Direct** | Polar device paired directly via vendor protocol or Polar's API | **planned** — explicitly NOT live; see § 8 |
| **Bluetooth HR sensor** | Any HRS-compliant device paired in-app | **planned** — this MVP describes the spec; not yet implemented |

The Health tab and the Train tab MUST render the source label
verbatim. No "smart" abbreviation, no fallback that pretends
"Polar Direct" when the data path was actually "Polar via Apple
Health". Honesty about the source is the contract.

## 4. Privacy rules

These are non-negotiable. They apply to every UI surface, every
log line, every Supabase row, every MCP response, every commit.

| Rule | Surface | Reasoning |
|---|---|---|
| Never display BLE MAC addresses or peripheral UUIDs in any UI | Train tab pairing flow, Settings, Admin/Dev, error toasts | MAC addresses are stable cross-app identifiers. |
| Never log MAC / peripheral UUID to crash reporting / analytics | All native + JS log paths | Same reasoning; same redaction posture as the connector pipeline. |
| Never include MAC / peripheral UUID in any MCP route response | `/mcp/public`, `/mcp/v2`, `/mcp` private | Even private MCP — these are device identifiers, not project state. |
| Never ship MAC / peripheral UUID in the `connector_*` Supabase tables | `connector_terminal_summary`, etc | Same. |
| Per-session storage keyed by `(user_id, session_id)` | `TrainingSession` (existing) | Aligns with existing user-scoped + session-scoped pattern. |
| BLE-derived data is local-first | Device storage | Sync happens via the same paths existing TrainingSession uses; no new sync surface. |
| User must explicitly enable BLE per session | Train tab session-start flow | No background scanning, no implicit pairing. |
| Pairing flow shows ONLY: vendor-supplied device name (e.g. "Polar H10") + signal strength bar | Train tab pairing flow | Device name is human-meaningful and not a stable cross-device ID; signal strength is stateless. |
| Re-pairing each session by default | Train tab session-start flow | Avoids implicit always-on relationship that would surprise the user. The "remember this device" toggle is a separate batch. |
| Native permission strings explicit about purpose | iOS `NSBluetoothAlwaysUsageDescription` + Android `BLUETOOTH_SCAN` / `BLUETOOTH_CONNECT` rationale | Per Apple/Google review guidelines and the project's privacy doc. |

The redactor in `docs/CONNECTOR_SANITIZATION_RULES.md` does NOT
currently match BLE MAC patterns (`XX:XX:XX:XX:XX:XX`) or
peripheral UUIDs (16-byte hex sequences). When BLE work
implements MAC-shaped patterns appearing in any
control-centre-bound text field, **the redactor MUST be
extended FIRST** with an explicit pattern + test. Adding the
extension is a Lane-1 docs/test commit, not bundled with the
BLE wiring.

## 5. Native rebuild requirements

The Train-session HRS feature requires native code paths that
the current `npx expo run:ios` / `npx expo run:android` build
does not include. Capturing the requirements here so the
implementation batch knows exactly what native rebuild changes
to make. **None of this lands in the spec commit.**

### iOS

- Phase-1 scaffold choice: `react-native-ble-plx` `^3.5.1`,
  already present in `apps/mobile/package.json`. The first
  implementation batch keeps it central-only, foreground-only,
  and UI-hidden until a native rebuild is verified.
- Add `NSBluetoothAlwaysUsageDescription` to `Info.plist` (or
  `expo-build-properties` `ios.infoPlist.NSBluetoothAlwaysUsageDescription`)
  with copy: "Used during a training session to read live
  heart rate from a paired sensor. Never sent off-device
  without your action."
- Permission prompt fires on first BLE scan, not on app launch.
- BLE peripheral discovery uses CoreBluetooth via the chosen
  RN library (`react-native-ble-plx` is the most-used choice;
  any equivalent that exposes raw HRS reads is acceptable).
- Background mode `bluetooth-central` is **NOT enabled** —
  foreground-only BLE per § 1.
- Pre-build verification: `npx expo prebuild --platform ios`
  produces an `ios/` directory containing the
  `NSBluetoothAlwaysUsageDescription` entry; pre-rebuild
  CI must include `xcodebuild -showBuildSettings` smoke if a
  workflow is set up.

### Android

- Phase-1 scaffold choice: `react-native-ble-plx` `^3.5.1`,
  already present in `apps/mobile/package.json`. A local Expo
  config plugin sets `android:usesPermissionFlags="neverForLocation"`
  on `BLUETOOTH_SCAN` during prebuild.
- Add `BLUETOOTH_SCAN` (`android:usesPermissionFlags="neverForLocation"`)
  and `BLUETOOTH_CONNECT` permissions to `AndroidManifest.xml`
  (or `expo-build-properties` `android.permissions`) for
  Android 12+ behaviour.
- For Android 11 and below, also `ACCESS_FINE_LOCATION`
  scoped only to BLE-scan duration.
- Permission prompt fires on first BLE scan.
- BLE GATT discovery via the chosen RN library.
- No `BLUETOOTH_ADVERTISE` (we are central, not peripheral).
- Health Connect declaration is **unaffected** — BLE HR does
  NOT register a Health Connect data type; it stays in the
  app's own session log.

### Both platforms

- Bumping `app.json` `android.versionCode` + `ios.buildNumber`
  is the **owner-tap action that gates the next paired tester
  build**, per the existing release flow in
  `docs/APP_DEVELOPMENTS.md` and
  `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md`. The BLE
  implementation batch MUST NOT bump versions itself; that's
  a separate Aaron-tap.
- Pre-rebuild type check: `npx tsc --noEmit` in `apps/mobile`
  must remain clean.
- The implementation batch ships behind the existing
  `isAdminEmail` gate for the first paired build so only Aaron
  + girlfriend see the BLE pairing UI; tester rollout is a
  later batch after the eight-rule equivalent of
  `docs/LOCAL_BRIDGE_WORKFLOW_PLAN.md` Stage 5 is satisfied
  for BLE.

## 6. Do-not-promote-yet list

These are **NOT live**. Documenting here so future audits don't
re-open them as candidate work.

- **Polar Direct** — vendor-specific protocol or Polar API path
  is documented in `docs/WHOOP_POLAR_SYNC_STRATEGY.md` as a
  candidate but **not implemented**. Do NOT mark Polar Direct
  as live in any UI, source label, or connector response. The
  source label `Polar Direct` is reserved.
- **BLE-derived data into readiness compute** — even after the
  Train-session MVP ships, BLE HR does NOT feed
  `normalized_daily_metrics`, the readiness compute in
  `packages/shared/src/backend/services/readiness/grappler-readiness.ts`,
  or any per-bucket provenance entry without an explicit
  separate spec batch.
- **Background BLE scanning** — foreground only.
- **BLE characteristic writes** — read-only.
- **Garmin BLE** — out of scope.
- **WHOOP-via-BLE** — WHOOP doesn't expose a public BLE HRS
  profile; the existing `WHOOP_DIRECT_SETUP.md` OAuth path is
  the only WHOOP integration. Do not attempt BLE WHOOP.
- **Multi-device session capture** — pair one HR sensor per
  session in the MVP. Multi-sensor (chest + watch) is a later
  spec batch.
- **Cross-device "remember this device" persistence** — every
  session re-pairs in the MVP. Saved-device support is a later
  batch with an explicit privacy review.
- **BLE pairing UI on the Health tab** — Train tab only. Per
  `docs/POST_MCP_PRODUCT_LANES.md` Lane A, the Health tab
  surface stays focused on Apple Health / Health Connect
  reliability.
- **Tester rollout** — first paired build after implementation
  ships with `isAdminEmail`-gated UI. General tester
  visibility lands only after Aaron + girlfriend have used it
  across multiple sessions without regressions.

## 7. Acceptance criteria

The implementation batch is "done" when ALL of the following
hold on Aaron's iPhone (Apple Watch chest-strap proxy or any
HRS-compliant device) AND girlfriend's Android (any HRS-compliant
device):

1. **Pairing flow**: Train tab session-start screen shows a
   "Pair HR sensor" button. Tap → permission prompt (first run
   only) → scan list with vendor name + signal-strength bar
   only. Selecting a row connects.
2. **Live HR readout**: While the session is live, current bpm
   is visible. Updates ≥1 Hz. Connection-loss flagged with a
   chip; HR field reverts to "—". Session continues.
3. **Disconnect on session end**: Ending the session
   disconnects the peripheral. Re-entering Train tab does NOT
   show the device as connected.
4. **Re-pair next session**: New session = new pairing flow.
   No "auto-reconnect" surprise.
5. **No MAC / UUID surfaced**: Search the live screen, the
   pairing list, settings, error toasts, crash reports.
   Vendor-supplied name only.
6. **Source label verbatim**: TrainingSession log entry shows
   `Bluetooth HR sensor` as the source for HR points captured
   this session — never `Polar Direct`, never bare "Polar".
7. **Health tab unchanged**: No BLE pairing entry point on the
   Health tab; existing Apple Health / Health Connect cards
   render identically.
8. **Readiness unchanged**: `AthleteStateStrip` /
   readiness compute returns identical values whether or not
   BLE was used during the day.
9. **No new MCP surface**: `/api/control_centre`,
   `/mcp/public`, `/mcp/v2`, and `/mcp` admin routes return
   the same shape as before BLE shipped. No BLE-specific
   field, no MAC, no peripheral UUID.
10. **Permission language matches the spec**: Strings on the
    iOS prompt and the Android rationale match § 5 verbatim.
11. **Tester gate**: Initial build is `isAdminEmail`-gated.
    A non-admin tester does NOT see the "Pair HR sensor"
    button.
12. **Privacy walk-through**: Open `docs/PRIVACY.md` (or its
    rendered website page), confirm BLE HR is described
    accurately. The website privacy text MUST be updated
    in the same paired build that ships BLE.

## 8. Phone test checklist (post-implementation)

Manual checks Aaron walks through on a tester device once the
implementation batch ships behind the admin gate:

- [ ] Open Train tab. Tap "Pair HR sensor". Permission prompt
      appears. Scan list shows ≥1 device with vendor name +
      signal strength.
- [ ] Connect. Live bpm visible within 5s. Updates fluidly.
- [ ] Walk out of BLE range. Chip flips to "disconnected".
      Walk back. Reconnects (or session continues with HR
      gap, never crashes).
- [ ] End session. Verify the session log records HR points
      with `source: 'Bluetooth HR sensor'` (or the documented
      schema-equivalent).
- [ ] Open Settings → Privacy → confirm no MAC / peripheral
      UUID anywhere. Long-press / inspect any BLE-adjacent
      field; copy clipboard; nothing leaks.
- [ ] Open `/api/control_centre` and `/mcp/v2 project.get_current_state`
      from the laptop curl path. Diff before/after BLE
      session: no new fields, no leaked identifiers.
- [ ] Force airplane mode mid-session. App handles loss
      gracefully; session continues with HR gap.
- [ ] Crash reporter (Sentry / Expo equivalent if wired):
      simulate a JS error during the BLE flow. Verify the
      crash payload contains zero MAC / UUID strings. If
      any leak, redactor extension MUST land before the
      paired build dispatch.
- [ ] Health tab on iOS: Apple Health card renders
      identically to pre-BLE build. Same on Android Health
      Connect.
- [ ] Readiness UI (when it ships per Lane B): no change
      attributable to BLE session presence.
- [ ] iOS `Info.plist`: `NSBluetoothAlwaysUsageDescription`
      string matches § 5.
- [ ] Android manifest: `BLUETOOTH_SCAN` / `BLUETOOTH_CONNECT`
      present; no `BLUETOOTH_ADVERTISE`.

## 9. Implementation phases

Captured here so the spec doesn't dictate batch shape but does
make the dependency order explicit. Each phase is a separate
owner-approved batch; do NOT bundle them.

| Phase | What | Lane | Gate |
|---|---|---|---|
| Spec — this commit | Spec doc, no code | Lane 1 | None — landed |
| Redactor extension | Add MAC + peripheral-UUID patterns to `redactTokenLikeSubstrings` + tests | Lane 1 | Spec landed |
| Native scaffolding | Add the chosen BLE library + `expo-build-properties` permissions; rebuild without BLE UI; verify the iOS / Android build still passes | Lane 2 (build autopilot — needs paired build dispatch) | Aaron approves; redactor extension landed; spec acceptance § 5 walked |
| Train-tab pairing UI | Pair / connect / live readout UI behind `isAdminEmail` gate | Lane 2 | Native scaffolding shipped to Aaron + girlfriend |
| Session log persistence | TrainingSession schema extension to capture HR points + source label | Lane 2 (schema-equivalent edit per BACKLOG_AUTOMATION_SYSTEM.md) | Pairing UI verified on tester device |
| Tester rollout | Remove `isAdminEmail` gate; update website privacy copy in same paired build | Lane 3 | ≥4 sessions clean across both tester devices; redactor proven; privacy doc current |

## 10. Anti-rules

- **No BLE code in the spec commit.** Every line of BLE
  implementation lands in a later batch.
- **No mobile UI changes here.** Train tab visuals stay as
  Codex's lane.
- **No native dependency added in this commit.** No
  `package.json` edit, no Expo plugin entry.
- **No readiness coupling.** BLE HR is session data, full
  stop. Readiness compute changes need their own spec.
- **No "Polar Direct" rename.** The label is reserved; using
  it in any UI / connector / log before vendor-specific
  protocol work ships is a regression.
- **No raw MAC / peripheral UUID anywhere — UI, logs, MCP,
  Supabase, crash reports.** This is the floor below every
  BLE feature.
- **No "remember this device" by default.** Re-pair per
  session.
- **No background BLE scanning.** Foreground only.
- **No coupling to the in-flight tester build.** The current
  paired build pipeline (Codex-driven Android run + iOS
  TestFlight) does NOT ship BLE; this work waits for its own
  dispatch after the implementation batch.

## 11. Codex handoff prompt

Use this prompt verbatim when the implementation batch is
ready to start. Do NOT run it in this docs commit.

```
PROMPT-ID: CODEX-BLUETOOTH-MVP-IMPL-PHASE-1-NATIVE-SCAFFOLD-01
TYPE: CODEX
LANE: Mobile / native scaffolding
PRIORITY: Bluetooth Train-session HR MVP

Source of truth: docs/BLUETOOTH_MVP_SPEC.md.

Phase 1 only: native scaffolding. NO Train-tab UI in this batch.

Do:
1. Add the chosen BLE library (react-native-ble-plx OR equivalent
   expo plugin). Document the choice in
   docs/BLUETOOTH_MVP_SPEC.md § 5 by appending the picked
   library + version to the iOS and Android subsections.
2. Add native permissions via expo-build-properties:
   - iOS: NSBluetoothAlwaysUsageDescription with the verbatim
     string from § 5.
   - Android: BLUETOOTH_SCAN (neverForLocation) +
     BLUETOOTH_CONNECT. Android 11- ACCESS_FINE_LOCATION
     scoped to scan only.
3. Run npx expo prebuild --platform ios and …--platform android
   in clean sandboxes; verify the manifest / Info.plist
   contain the expected entries.
4. tsc --noEmit clean in apps/mobile.
5. Do NOT add any Train-tab UI.
6. Do NOT add any session-log schema changes.
7. Do NOT bump app.json versionCode / buildNumber.
8. Commit the native scaffolding only.
9. Hand off to Phase 2 (Train-tab pairing UI) when Aaron
   has approved this scaffold on a paired build.

Verification:
- iOS prebuild produces the expected Info.plist key.
- Android prebuild produces BLUETOOTH_SCAN + BLUETOOTH_CONNECT.
- No new MCP-route surface added.
- No mobile health source logic touched.

Output:
- changed files
- chosen BLE library + version (record in spec § 5)
- native permission keys present yes/no per platform
- tsc clean yes/no
- next step: Phase 2 Train-tab pairing UI behind isAdminEmail
- committed yes/no
- whether Aaron's next paired build dispatch will ship the
  scaffolding
```

## 12. What this doc is NOT

- An implementation plan with line-by-line file edits.
- A library lock-in. The `react-native-ble-plx` mention is the
  current likely choice; the Phase-1 implementation batch
  can pick an equivalent that satisfies § 5.
- A backend change. The Cloudflare Worker, `connector_*`
  Supabase tables, and `/api/*` routes are unaffected.
- A readiness change. See § 2 + § 6.
- A privacy-policy update. The website privacy copy MUST be
  updated in the tester-rollout batch, not this spec.

## 13. Cross-references

- `docs/POST_MCP_PRODUCT_LANES.md` Lane A and Lane B — BLE
  MVP fits between them: not Lane A (which is Apple Health /
  Health Connect reliability), not Lane B (readiness UI),
  but a third Train-session lane that doesn't gate either.
- `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md` — names the
  current live wearable surface; this doc explicitly does not
  contradict it, only adds the BLE HR row in the
  do-not-promote-yet posture.
- `docs/CONNECTOR_SANITIZATION_RULES.md` — to be extended
  with MAC and peripheral-UUID patterns before any BLE data
  flows into a control-centre-bound text field.
- `docs/PRIVACY.md` — to be extended with a BLE HR section in
  the tester-rollout batch.
