# Installed-device QA release gate

Status: active gate. This is QA-only, not public release approval.

## Current build QA state

- iOS: build 19 submitted to TestFlight Team (Expo), Apple
  processing. Current EAS build reference from handoff:
  `9b11aeb1`.
- Android: versionCode 18 build finished. Current EAS build reference
  from handoff: `36340071`.
- Android AAB local handoff path:
  `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab`.
- Android Play/Internal submit is blocked on Aaron/Google credential
  flow or manual Play Console upload.

The local AAB path is okay in admin/local docs. Do not expose artifact
URLs, Google credentials, or private upload details on public MCP
surfaces.

## Next human action — Android manual upload

1. Open Play Console.
2. Select Lauburu Grappling Map.
3. Go to Testing -> Internal testing.
4. Create a new release.
5. Upload:
   `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab`
6. Complete the Play Console review screens for the internal release.
7. Start rollout to Internal Testing only.
8. Wait for Play processing.
9. Install/update from Play Internal on the Android device.
10. Run installed-device QA and record results with
    `npm run bridge:agent-qa`.

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

## Android Play Console manual upload — detailed handoff

This complements § "Next human action — Android manual upload"
above with per-screen specifics for the 2026-05-08 build, so
Aaron can drag-drop without re-deriving each click.

### Build identifiers

| Field | Value |
|---|---|
| Local .aab path | `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab` |
| Size | 74,614,387 bytes (74.6 MB) |
| SHA-256 | `e7ecc09e14bec8b3a0ba5ce0c9be6e236e4056a3006e419558dda7e7d6ee5599` |
| EAS build ID | `36340071-ff49-4898-865a-9c349049532c` |
| versionCode | 18 |
| App version | 0.1.0 |
| Repo commit | `0932c63` |
| Track target | Internal testing (NOT Open / Closed / Production) |
| Bundle file type | Android App Bundle (.aab); Play Console processes to per-device APKs server-side |

Verify the local file integrity before uploading (avoids
"the artifact got corrupted on download"):

```bash
shasum -a 256 ~/Downloads/lauburu-android-versionCode18-commit0932c63.aab
# expected: e7ecc09e14bec8b3a0ba5ce0c9be6e236e4056a3006e419558dda7e7d6ee5599
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
     `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab`
     into the drop zone.
   - Wait ~30s for Play to scan the bundle. Should show a row
     with `Lauburu Grappling Map · Bundle (release).aab ·
     versionCode 18 · ~74 MB`.
   - If Play complains about a duplicate versionCode, abort —
     means a prior versionCode-18 build was already submitted
     and we need a different versionCode (separate task).
7. **Release name** (auto-fills from versionCode): leave as
   `18 (0.1.0)` or whatever Play suggests.
8. **Release notes** — paste the following (multi-language
   tab; English (United States) is the default):
   ```
   QA build at commit 0932c63.

   Includes: auth route fix (Create account / Sign in no longer
   open missing route), Settings auth-param consumption, stale-
   token recovery, Health Connect state-pill gaps closed
   (permission_needed + sync_failed pills now render),
   WHOOP/Polar Direct removed from core readiness, admin-dev
   workflow-dispatch button __DEV__-gated, ATHLETE_MEMORY_API_TOKEN
   rotated.

   Internal QA only — not for public release.
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
  versionCode 18 is now consumed once Play accepts the upload.
  The next QA build (post installed-device QA pass) uses
  versionCode 19.

### After upload completes (Aaron's device side)

1. Open Play Store on Android device.
2. Search **Lauburu Grappling Map** OR tap the internal-tester
   email link from Google.
3. Install / update to versionCode 18.
4. Run the simulator-side audit script (auth tap-flow / Health
   Manage Sources / Grappling Readiness / admin-dev gating)
   from § "Next human action — iPhone TestFlight" but on
   Android. Same screens, same expectations.
5. Record verdict via `npm run bridge:agent-qa` interactively
   with `status: pass` (or `partial` / `fail`) +
   `platform: android`. The release gate clears for Android
   once recorded.

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
