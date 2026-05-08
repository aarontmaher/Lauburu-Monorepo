# Installed-device QA release gate

Status: active gate. This is QA-only, not public release approval.

## v20 installed-device evidence — Android Health Connect "app not listed" (2026-05-09)

Aaron's installed-device evidence on v20: tapping Connect on the
Health Connect source row opens the Health Connect OS app, but the
Lauburu Grappling Map app is **NOT listed** under Health Connect
→ App permissions. This blocks the v20 gate.

Root cause hypothesis (patched repo-only, awaits a v21 retest):

- The Android 14+ Health Connect "Apps & permissions" UI requires
  a `<activity-alias android:name=".ViewPermissionUsageActivity"
  android:permission="android.permission.START_VIEW_PERMISSION_USAGE"
  android:targetActivity=".MainActivity">` with intent-filter
  `<action android:name="android.intent.action.VIEW_PERMISSION_USAGE"/>`
  and category `<category android:name="android.intent.category.HEALTH_PERMISSIONS"/>`
  for HC's intent resolver to register the app for permissions.
- The v20 manifest contained the rationale intent-filter on
  MainActivity (Android 13- compatibility) but **not** the
  Android 14+ activity-alias. HC consequently never registered
  the app, the OS dialog did not appear, and the Apps screen did
  not list the app.

Patch (repo-only, do NOT upload v21 yet):

- `apps/mobile/plugins/withAndroidHealthConnectPermissionDelegate.js`
  now adds the activity-alias on top of the existing rationale
  filter. Idempotent — safe to re-run on subsequent prebuilds.
- `apps/mobile/src/services/health.android.ts` exposes a runtime
  probe (`didLastPermissionRequestFailToRegister`) that detects
  the silent-rejection failure mode (zero grants returned, < 250ms
  round-trip, SDK still reports available).
- `apps/mobile/src/store/health-store.ts` threads
  `hcRegistrationStatus` (`'unknown' | 'registered' | 'did_not_register'`)
  through the public store API.
- `apps/mobile/src/components/HealthActionsPanel.tsx` surfaces
  a new "Health Connect did not register" status pill on the
  source row when the probe reports the failure mode, with a
  meta hint pointing the tester at HC → Apps and a primary action
  relabeled to "Retry permission request" (still calls the
  same `requestPermissions` flow — second tap should succeed
  once the activity-alias is present).

v21 retest path (after Aaron approves a new EAS build):

1. EAS build with the patched config plugin applied at prebuild.
2. Install on Aaron's Android device via internal testing.
3. Open Health → Manage Sources → tap **Connect** on the Health
   Connect source row. Expect: OS Health Connect permissions
   dialog appears.
4. After granting (or denying) at least one permission, open
   Health Connect → Apps. Expect: **Lauburu Grappling Map** is
   now listed.
5. If HC still does not list the app, verify that `expo prebuild`
   actually wrote the activity-alias to
   `android/app/src/main/AndroidManifest.xml` under
   `<application>` — search for `ViewPermissionUsageActivity`.
   If absent, the config plugin failed to apply; bisect the
   plugin chain.

Anti-rules:

- **No EAS build, Play upload, TestFlight upload, or production
  release** until Aaron approves a v21 build.
- The fix is **repo-only** until a v21 retest confirms the
  installed-device behaviour. Treat this section as a tracked
  hypothesis, not a verified pass.

Tests added (repo-only):

- `cloudflare-worker/test/test-android-health-connect-crash-guard.ts`
  now asserts the activity-alias markers, the runtime probe,
  the UI wiring, and that `onConnectHealthConnect` calls
  `requestPermissions` BEFORE any `openHealthConnectSettings`
  fallback.
- `cloudflare-worker/test/test-source-sheet-status-mapper.ts`
  pins the `'Health Connect did not register'` status string to
  the canonical `'setup required'` TruthLabel.

## Current build QA state

- iOS: build 19 submitted to TestFlight Team (Expo), Apple
  processing. Current EAS build reference from handoff:
  `9b11aeb1`.
- Android: **versionCode 20 build FINISHED.** Active gate target
  (Health Connect crash patch + new debug-card surface).
  EAS build reference: `58071abc`. Repo commit: `3d7122c`
  (versionCode bump on top of patch commit `5ea6b24`).
- Android v20 AAB local handoff path:
  `~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab`.
- Android v19 was built (EAS `d1f1a9a5`, commit `bc0b567`,
  local file
  `~/Downloads/lauburu-android-versionCode19-health-connect-fix.aab`)
  but **was not uploaded to Play Console** — superseded by
  v20 (which contains the same crash patch plus the debug-card
  surface). Kept locally as fallback retest target.
- Android v18 historical evidence preserved (failed
  Health Connect → Connect crash on 2026-05-08):
  EAS `36340071`, repo commit `0932c63`,
  local file `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab`.
  **Do NOT use v18 for any further upload — versionCode is
  consumed by Play Console.**
- Android Play/Internal submit is blocked on Aaron/Google credential
  flow or manual Play Console upload.

The local AAB path is okay in admin/local docs. Do not expose artifact
URLs, Google credentials, or private upload details on public MCP
surfaces.

## Next human action — Android manual upload (v20 active)

1. Open Play Console.
2. Select Lauburu Grappling Map.
3. Go to Testing -> Internal testing.
4. Create a new release.
5. Upload:
   `~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab`
6. Complete the Play Console review screens for the internal release.
7. Start rollout to Internal Testing only.
8. Wait for Play processing (~5–30 minutes).
9. Tester opens the internal-tester opt-in link from Google
   (or taps the existing Play Store internal-tester invite).
10. Install/update from Play Store on the Android device.
11. **Specifically retest Health Connect → Connect tap** — the
    v18 crash repro path. v20 includes the
    `withAndroidHealthConnectPermissionDelegate` config plugin
    + defensive permission gating from commit `99dd657`, AND the
    new Health Connect handshake-state debug-card surface from
    commit `5ea6b24`.
12. v20-specific tester checks: verify the new **Open Health
    Connect** secondary button on the disconnected source-row
    (deep-links to OS settings); verify the failed-permission
    alert offers an Open Health Connect action button; if you
    have admin/dev access, verify the Health Connect debug card
    surfaces SDK availability + last `permission_requested`
    timestamp + requested record types + granted metrics + last
    error.
13. Run installed-device QA and record results with
    `npm run bridge:agent-qa` (`platform: android`,
    `androidVersionCode: 20`).

## Next human action — iPhone TestFlight

1. Wait for Apple processing to finish for build 19.
2. Open TestFlight on iPhone.
3. Install/update Lauburu Grappling Map build 19.
4. Run installed-device QA.
5. Record results with `npm run bridge:agent-qa`.

## Gate rule

Repo-only, simulator-only, or processing-only evidence does not clear
installed-device gates. A pass must include exact installed iOS build
number and/or Android versionCode tested on a real device.

## Android Play Console manual upload — detailed handoff (v20 active)

This complements § "Next human action — Android manual upload"
above with per-screen specifics for the v20 Health Connect crash
patch + debug-surface build, so Aaron can drag-drop without
re-deriving each click.

### Build identifiers — v20 (active)

| Field | Value |
|---|---|
| Local .aab path | `~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab` |
| Size | 74,629,563 bytes (74.6 MB) |
| SHA-256 | `e26d1d2d9922b984397c28db69327967524d77fc80046ea6593cb7e42eac80e1` |
| EAS build ID | `58071abc` |
| versionCode | 20 |
| App version | 0.1.0 |
| Repo commit | `3d7122c` (versionCode bump; Health Connect debug surface in `5ea6b24`; crash patch in `99dd657`) |
| Track target | Internal testing (NOT Open / Closed / Production) |
| Bundle file type | Android App Bundle (.aab); Play Console processes to per-device APKs server-side |

Verify the local file integrity before uploading (avoids
"the artifact got corrupted on download"):

```bash
shasum -a 256 ~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab
# expected: e26d1d2d9922b984397c28db69327967524d77fc80046ea6593cb7e42eac80e1
```

### Step-by-step Play Console click path

1. Open `https://play.google.com/console`.
2. Sign in with the developer account that owns
   `com.lauburu.grapplingmap`.
3. Top-right app picker → **Lauburu Grappling Map**.
4. Left sidebar → **Testing → Internal testing**.
5. Tab: **Releases** (default). Click **Create new release**
   in the top-right.
6. **App bundles** section:
   - Click **Upload** OR drag the .aab from
     `~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab`
     into the drop zone.
   - Wait ~30s for Play to scan the bundle. Should show a row
     with `Lauburu Grappling Map · Bundle (release).aab ·
     versionCode 20 · ~74 MB`.
   - If Play complains about a duplicate versionCode, abort —
     means a prior versionCode-20 build was already submitted
     and we need a different versionCode (separate task).
7. **Release name** (auto-fills from versionCode): leave as
   `20 (0.1.0)` or whatever Play suggests. Recommended:
   `v20 Health Connect debug surface QA`.
8. **Release notes** — paste the following (multi-language
   tab; English (United States) is the default):
   ```
   Android v20 internal QA build at commit 3d7122c.

   Carries the v19 Health Connect crash fix
   (withAndroidHealthConnectPermissionDelegate config plugin +
   defensive permission gating) and adds a Health Connect
   handshake-state debug surface for tester diagnosis: a
   secondary "Open Health Connect" button on the disconnected
   source row, an "Open Health Connect" action on the failed-
   permission alert, and an admin/dev-gated debug card showing
   SDK availability, last permission_requested timestamp,
   requested record types, granted metrics, and last error.

   Retest specifically: Health / Manage Sources →
   Health Connect → tap Connect should NOT crash. Permission /
   unavailable / denied / connected / sync-failed / missing-field
   labels should render truthfully. No Apple Health wording on
   Android. The new Open Health Connect deep-link should reach
   the OS Health Connect settings cleanly.

   Internal testing only — not for public release.
   ```
9. Bottom-right → **Next**. Play screens:
   - **Side panel review**: confirms versionCode + release notes.
     If anything is wrong, click **Edit release** to go back.
   - **Errors / warnings panel**: read carefully. Common warnings
     (safe to ignore for internal QA): "no deobfuscation file
     uploaded", "missing native debug symbols". Common errors
     (do NOT proceed if shown): "Bundle has been signed by a
     different upload key" — that means upload-signing-key drift;
     stop and diagnose before forcing.
10. **Save** (top-right).
11. **Review release** (top-right blue button after save).
12. The **Review and roll out release** screen confirms:
    - Track: Internal testing
    - Testers: your existing Internal testers list (e.g.
      "Internal testers" group)
    - Countries / regions: leave at the existing Internal
      coverage; Internal testing is not country-restricted.
13. Click **Start rollout to Internal testing**.
14. Confirm dialog → **Rollout**.
15. Within 5–30 minutes the build is live for Internal testers.
    Aaron's Android device receives the update via the Play
    Store on the device (search for the app, or tap the Play
    Store internal-tester link emailed to the tester account).

### Anti-rules during the upload

- **Do NOT promote to Open / Closed / Production tracks** from
  this dialog. The "Promote release" / "Send to closed testing"
  affordances exist on the Internal testing page; ignore them.
- **Do NOT add new tester groups** in this flow — use the
  existing Internal testers list.
- **Do NOT change the upload signing key** if Play prompts. If
  Play says the bundle is signed by a different upload key, the
  build is not the right one for this app slot; STOP and diagnose
  separately.
- **Do NOT re-use this versionCode** for the next build —
  versionCode 20 is consumed once Play accepts the upload.
  The next QA build (post installed-device QA pass on v20)
  would use versionCode 21 and ship a different feature
  surface (FS-020 journal-import UI, FS-021 health input
  expansion, etc.). Do NOT bump to v21 until v20 installed-
  device retest verdict is recorded.

### After upload completes (Aaron's device side)

1. Open Play Store on Android device.
2. Search **Lauburu Grappling Map** OR tap the internal-tester
   email link from Google (or the Play Store internal-tester
   opt-in URL Aaron forwarded to the tester).
3. Install / update to versionCode 20.
4. Open the app. Confirm the version pill (if rendered) shows
   versionCode 20 / appVersion 0.1.0.
5. Health flow retest (the v18 crash repro):
   - Go to Health / Manage Sources.
   - Tap Health Connect → Connect.
   - **Expected**: no crash. Either Health Connect
     authorisation prompt opens, or the unavailable/denied
     state pill renders truthfully.
   - **Failure**: app crashes/closes/freezes on tap.
6. v20-specific check: on the disconnected Health Connect row
   in the source-sheet, verify the secondary **Open Health
   Connect** button is visible. Tap → verify deep-link to OS
   Health Connect settings → verify clean back-button return.
7. v20-specific check: trigger a permission denial (deny the
   OS prompt). Verify the failed-permission alert renders with
   an **Open Health Connect** action button. Tap → same
   deep-link behaviour.
8. v20-specific (admin/dev only — gated to Aaron's email):
   open the Health Connect debug card. Verify it surfaces SDK
   availability + last `permission_requested` timestamp +
   requested record types + granted metrics + last error.
9. Audit other screens for parity with the simulator-side
   audit (auth tap-flow / Manage Sources state pills /
   Grappling Readiness copy truthfulness / admin-dev gating).
   Same screens, same expectations as iOS.
10. Record verdict via `npm run bridge:agent-qa` interactively
    with `status: pass` (or `partial` / `fail`) +
    `platform: android` + `androidVersionCode: 20`. The
    release gate clears for Android once recorded with
    `status: pass`.

### AGENT_QA_RESULT_JSON template (Android v20)

For pass:

```json
{
  "status": "pass",
  "gate": "release_gate",
  "platform": "android",
  "deviceName": "<e.g. Pixel 7 / Galaxy S22>",
  "installedBuild": {
    "androidVersionCode": 20,
    "appVersion": "0.1.0",
    "channel": "production",
    "track": "internal_testing"
  },
  "results": {
    "androidHealthConnect": "pass",
    "healthManageSources": "pass",
    "grapplingReadiness": "pass",
    "adminControlCentre": "not_tested",
    "copyTruthfulness": "pass",
    "uiDensity": "pass"
  },
  "evidence": {
    "screenshotRefs": ["<screenshot or recording ref>"],
    "notes": "Health Connect Connect tap completed without crash."
  }
}
```

For fail (crash repro recurs):

```json
{
  "status": "fail",
  "gate": "release_gate",
  "platform": "android",
  "deviceName": "<device>",
  "installedBuild": {
    "androidVersionCode": 20,
    "appVersion": "0.1.0",
    "channel": "production",
    "track": "internal_testing"
  },
  "results": {
    "androidHealthConnect": "fail"
  },
  "requiredFixes": [
    "Health Connect Connect tap still crashes on v20. Capture exact crash signature (logcat or ADB) and diagnose plugin / permission delegate gap. Use the v20 debug card to capture last permission_requested timestamp + granted metrics + last error."
  ],
  "evidence": {
    "screenshotRefs": ["<crash screen recording>", "<debug card screenshot>"],
    "notes": "Crash recurred on v20. Patch in 99dd657 + 5ea6b24 not sufficient. Debug card output captured."
  }
}
```

For blocked (Play upload incomplete or device unavailable):

```json
{
  "status": "partial",
  "gate": "release_gate",
  "platform": "android",
  "deviceName": null,
  "installedBuild": {
    "androidVersionCode": null
  },
  "results": {
    "androidHealthConnect": "not_tested"
  },
  "requiredFixes": [
    "<exact reason: e.g. Play Console upload incomplete; tester device unavailable>"
  ],
  "evidence": {
    "notes": "<context>"
  }
}
```

### Historical evidence — Android v18 (failed 2026-05-08)

Preserved for traceability. **Do NOT upload v18 again** —
versionCode 18 is consumed.

| Field | Value |
|---|---|
| Local .aab path (historical) | `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab` |
| Size | 74,614,387 bytes |
| SHA-256 | `e7ecc09e14bec8b3a0ba5ce0c9be6e236e4056a3006e419558dda7e7d6ee5599` |
| EAS build ID | `36340071-ff49-4898-865a-9c349049532c` |
| versionCode | 18 |
| Repo commit | `0932c63` |
| Outcome | App crashed on Health Connect → Connect tap |
| Fix shipped in | `99dd657` (HealthConnect: fix Android permission crash guard) |
| Retest target | superseded by v20 (this doc § "Build identifiers — v20") |

### Historical evidence — Android v19 (built, NOT uploaded)

Preserved for traceability. **Do NOT upload v19 to Play
Console** — superseded by v20 (which contains the same crash
patch plus the diagnosis surface).

| Field | Value |
|---|---|
| Local .aab path (historical) | `~/Downloads/lauburu-android-versionCode19-health-connect-fix.aab` |
| Size | 74,614,695 bytes |
| SHA-256 | `4569ff13df6322ef6761d0f1a16830497dfdfe5f74e39f8c34be142906cb22dc` |
| EAS build ID | `d1f1a9a5-e2a0-40a6-b889-5c063cf9e87a` |
| versionCode | 19 |
| Repo commit | `bc0b567` (versionCode bump on top of crash patch `99dd657`) |
| Outcome | Built but never uploaded to Play; superseded by v20 |
| Why kept | Fallback retest target if v20 reveals an unexpected issue caused by the v20-only debug card surface |
| Active retest target | versionCode 20 (this doc § "Build identifiers — v20") |

## Android v20 — BUILT, awaits Aaron upload

**Status (2026-05-08):** v20 was approved + dispatched + built
on EAS. versionCode in `apps/mobile/app.json` is **20**. .aab
downloaded locally to
`~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab`.
**Aaron's next manual step**: upload the .aab to Play Console
Internal testing → wait for Play processing → tester opens
opt-in link → tester installs/updates → tester runs the
checklist → record AGENT_QA result.

### Why v20 was approved

The patch on commit `5ea6b24`
("HealthConnect: surface Connect handshake state for tester
diagnosis") sits on top of v19's commit `bc0b567`. The patch is
Android-only, Health-Connect-only, and adds:

- An admin/dev-gated Health Connect debug card exposing SDK
  availability, last `permission_requested` timestamp, requested
  record types, granted metrics, and last error.
- A reorganised Android source-sheet: the disconnected row now
  carries a primary **Connect** button (calls
  `react-native-health-connect`'s `requestPermission` API
  directly — same as v19) plus a secondary **Open Health Connect**
  button for tester troubleshooting.
- Failed-permission alert flow now offers an **Open Health Connect**
  action button so testers can verify OS-side state without
  leaving the app.

The commit message explicitly states:
**"No manifest, package, or native delegate changes — those were
already correct on versionCode 19."**

### v20 scope rules (non-negotiable)

| Rule | Why |
|---|---|
| **No iOS changes** | v20 is Android-only. iOS TestFlight build 19 (separate gate) is unaffected. |
| **No new permissions / no manifest changes** | The Android manifest already has the right Health Connect permissions on v19. v20 is purely diagnosis-surface. |
| **No package/native-delegate changes** | The `withAndroidHealthConnectPermissionDelegate` config plugin shipped in v19 (commit `99dd657`) and is unchanged on v20. |
| **No additional EAS builds after v20 in this gate** | Once v20 is built, the Health Connect crash gate has had its full attempt + diagnosis surface. The NEXT QA build cycle (versionCode 21) is a separate, non-Health-Connect feature build and requires its own approval. |
| **Do not bump versionCode pre-emptively** | Bumping `app.json` to 20 before Aaron approves the build wastes versionCode if v19 retest passes and v20 isn't needed. |
| **Tester device QA only** | v20, like v18 + v19, ships only to Play Internal testing. Never Open / Closed / Production. |

### When v20 is needed

- **v19 retest PASSES** (Health Connect → Connect tap completes
  without crash, permission flow works): v20 is **optional**
  diagnosis-surface improvement. Aaron may still approve v20
  for tester ergonomics, but the release gate clears on v19.
- **v19 retest FAILS** (crash recurs OR permission flow stalls
  in a non-crash failure mode): v20's debug card is the
  diagnosis surface that captures what went wrong on the OS
  side. Aaron approves v20, builds, retests.

### Tester checklist for v20 (when it ships)

The tester (Aaron, or Aaron's Android-device tester) runs this
ON TOP OF the v19 checklist (which v20 inherits — anything that
passed on v19 must still pass on v20):

1. Install v20 from Play Internal.
2. Open the app. Confirm the version pill (if rendered) shows
   versionCode 20 / appVersion 0.1.0.
3. Repeat the v19 Health Connect retest:
   - Health / Manage Sources → Health Connect → tap **Connect**.
   - **Expected**: no crash. Either the OS-side authorisation
     prompt opens, or the unavailable / denied / connected /
     sync-failed pill renders truthfully.
4. v20-specific: in the source-sheet for Health Connect, verify
   the **Open Health Connect** secondary button is visible on
   the disconnected row. Tap it; verify it deep-links to the
   Android Health Connect OS settings screen and returns to
   the app cleanly via back-button.
5. v20-specific: trigger a permission denial (deny the OS
   prompt). Verify the failed-permission alert renders with an
   **Open Health Connect** action button. Tap it; verify same
   deep-link behaviour.
6. v20-specific (admin/dev only): in the in-app Admin/Dev
   surface (gated to Aaron's email), open the **Health Connect
   debug card**. Verify it surfaces:
   - SDK availability (true / false).
   - Last `permission_requested` timestamp.
   - Requested record types list.
   - Granted metrics list.
   - Last error (if any).
7. Repeat the v19 checklist items 5–7 (auth tap-flow / Manage
   Sources state pills / Grappling Readiness copy truthfulness /
   admin-dev gating). Same screens, same expectations.
8. Record verdict via `npm run bridge:agent-qa` interactively
   with `status: pass` (or `partial` / `fail`) +
   `platform: android`. Reuse the AGENT_QA_RESULT_JSON template
   for v19 with `androidVersionCode: 20`.

### Codex handoff prompt for v20 — DISPATCHED + BUILD COMPLETE

Aaron approved the v20 build dispatch. Codex executed the
prompt below: bumped versionCode 19 → 20 (commit `3d7122c`),
ran `npx eas-cli build --platform=android --profile=production
--non-interactive`, and the build completed successfully on EAS
as build ID `58071abc...` (artifact downloaded to
`~/Downloads/lauburu-android-versionCode20-health-connect-debug-surface.aab`).
The handoff text is preserved here for traceability:

```
PROMPT-ID: CODEX-V20-ANDROID-EAS-BUILD-HEALTH-CONNECT-DIAGNOSIS-01
TYPE: CODEX
LANE: EAS Android v20 dispatch (gated on Aaron's explicit approval)

GOAL
Bump app.json android.versionCode 19 → 20 and dispatch one EAS
production-profile Android build for tester QA. Do NOT touch
iOS. Do NOT submit to Play Console (manual upload follows).

RULES
- Aaron MUST have approved this build dispatch in the prompt
  that triggered this handoff. If approval is unclear, STOP
  and ask Aaron.
- Android-only. iOS buildNumber stays 19.
- versionCode bump only — no other app.json changes.
- No manifest changes (the Health Connect permissions were
  correct on v19).
- production profile, distribution STORE, channel production,
  Play Internal track only.
- Do NOT use eas-cli build:submit to push to Play Console;
  Aaron uploads manually (Path B as for v19, since
  apps/mobile/google-services-key.json is absent).

TASKS
1. Verify HEAD includes commit 5ea6b24 (HealthConnect:
   surface Connect handshake state for tester diagnosis).
2. Bump apps/mobile/app.json android.versionCode 19 → 20.
   Commit ("QA: bump Android versionCode to 20 for Health
   Connect diagnosis-surface tester build").
3. cd apps/mobile && npx eas-cli build --platform=android
   --profile=production --non-interactive --no-wait.
4. Capture: EAS build ID + artifact URL once finished.
5. Update connector_build_status: android.versionCode=20,
   android.easBuildId=<id>, android.priorVersion={versionCode:19,
   qaResult:<v19 result>}.
6. Run bridge:snapshot.

OUTPUT (small)
- Status: dispatched / failed / blocked
- Pre-dispatch HEAD commit:
- New v20 commit:
- EAS build ID + artifact:
- connector_build_status updated: yes / no
- Remaining blocker:
```

### Public-safety reminder

The local AAB path (`~/Downloads/...`) and the SHA-256 hash are
**admin/laptop-side identifiers only**. They MUST NOT appear in:

- Public-safe MCP tool responses (`/mcp/v2 project.*`,
  `/mcp/v2 mobile.get_*_overview`, `handoff.get_latest`,
  `integrations.get_overview`, `project.get_operating_rules`).
- ChatGPT public-connector responses.
- Public docs commits (this doc IS local-only — the .aab path
  is on Aaron's laptop; sharing the doc with the path is fine
  because the file is not at that path on anyone else's
  machine).
- TestFlight / Play Internal release notes themselves (the
  notes I provided above are sanitised; no IDs leak).

Worker side: `cloudflare-worker/src/data/journal-canonical-terms.ts`
+ `journal-research-snippets.ts` are public-safe by
construction (no user data; generic drug names + general
background only). The build artifact URL (`expo.dev/artifacts/eas/...`)
is admin-token-gated by EAS; not exposed via our Worker.
