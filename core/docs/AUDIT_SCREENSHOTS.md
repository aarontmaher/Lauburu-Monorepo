# Audit screenshots — `npm run audit:screenshots`

Local-first capture of per-screen PNGs + a manifest from a
booted iOS Simulator or Android emulator. Aaron drives the
navigation; the script handles platform detection, build
identity, screenshot capture, and the manifest.

This is the **v1.5 capture tier** referenced in
`docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 1 — semi-auto
capture without the v2 admin-only in-app button and without
the v3 Maestro click-through flows. It works against any
simulator/emulator the team already runs; no new app
dependency, no EAS build.

## Quick start

```
npm run audit:screenshots
```

Then for each prompt, navigate the simulator/emulator to the
listed screen and press Enter. Press `s` to skip; `q` to
quit early.

Output:

```
artifacts/app-audit/<isoTimestamp>/
  home.png
  health.png
  manage-sources.png
  readiness.png
  journal.png
  train.png
  map.png
  settings.png
  admin-dev.png
  manifest.json
```

`artifacts/` is gitignored — bundles never reach the repo.

## Pre-requisites

| Platform | Need |
|---|---|
| iOS | Mac with Xcode + iOS Simulator running, with the Lauburu app launched. `xcrun simctl list devices booted` must show one Booted device. |
| Android | `adb devices` must show one device or emulator in `device` state. The Lauburu app should be in the foreground. |

The script does NOT need real Apple Health / Health Connect
permissions. The app gracefully renders unavailable / not-
granted states; the screenshot captures whatever the
simulator shows.

## Flags

```
node scripts/audit-screenshots.mjs --platform ios|android
node scripts/audit-screenshots.mjs --skip readiness,map
node scripts/audit-screenshots.mjs --device <udid|emulator-id>
node scripts/audit-screenshots.mjs --non-interactive
```

- `--platform`: forces ios / android. Default auto-detects iOS first, then Android.
- `--skip`: comma-separated screen ids to skip (e.g. when admin-dev is unreachable).
- `--device`: forces device id (overrides auto-detection).
- `--non-interactive`: captures the FIRST listed screen with whatever is currently on-screen, then exits. Useful for CI smoke; does NOT walk through every screen.

## Manifest schema

`manifest.json` shape (locked in
`cloudflare-worker/test/test-audit-screenshots-manifest.ts`):

```json
{
  "schemaVersion": 1,
  "captureTier": "v1.5_human_driven_auto_capture",
  "platform": "ios",
  "device": { "id": "<udid>", "name": "iPhone 15 Pro" },
  "build": {
    "appVersion": "0.1.0",
    "iosBuildNumber": "19",
    "androidVersionCode": 20,
    "iosBundleIdentifier": "com.lauburu.grapplingmap",
    "androidPackage": "com.lauburu.grapplingmap"
  },
  "repo": { "branch": "main", "shortHead": "0991468" },
  "capturedAt": "2026-05-09T12:00:00.000Z",
  "screens": [
    { "id": "home", "label": "Home", "route": "(tabs)/index", "file": "home.png", "capturedAt": "2026-05-09T12:00:01.000Z" }
  ],
  "skipped": [
    { "id": "admin-dev", "reason": "user-skipped" }
  ]
}
```

## Screen catalogue

The canonical 9-screen list (in capture order) lives in
`scripts/audit-screenshots-helpers.mjs` `AUDIT_SCREENS`. Add a
screen by appending an entry; the manifest schema doesn't need
to change.

| Order | id | Label | Route hint |
|---|---|---|---|
| 1 | `home`           | Home                        | `(tabs)/index` |
| 2 | `health`         | Health                      | `(tabs)/health` |
| 3 | `manage-sources` | Health → Manage Sources     | `(tabs)/health · sheet open` |
| 4 | `readiness`      | Grappling Readiness         | `(tabs)/health · readiness card` |
| 5 | `journal`        | Journal / Feedback          | `(tabs)/feedback` |
| 6 | `train`          | Train                       | `(tabs)/train` |
| 7 | `map`            | Map                         | `(tabs)/map-3d` |
| 8 | `settings`       | Settings                    | `(tabs)/settings` |
| 9 | `admin-dev`      | Admin / Dev                 | `admin-dev (admin email required)` |

## Privacy

- Bundles are local-first. `artifacts/` is gitignored. Do
  NOT commit a bundle, do NOT post it to public MCP, do NOT
  zip it for an unknown destination.
- Before sharing a bundle externally (e.g. to Agent or
  ChatGPT for proof per
  `docs/ADMINDEV_INSTALLED_PROOF_GAP.md`), blur or crop any
  pane showing real Apple ID / Supabase email / push tokens
  / EAS Bearer / artifact hashes.
- Never run the script while signed in with Aaron's account
  on a screen that exposes raw user health values. Sign out
  first or use a test account.

## How this fits the audit-automation spec

- v1 (manual screen recording, full screen movie) is still
  the right path when Agent needs end-to-end behaviour
  proof on installed-device.
- **v1.5 (this script)** captures discrete per-screen PNGs
  plus a structured manifest. Faster than v1 to flip
  through; matches the proof-row catalogue in
  `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` § 1.
- v2 (admin-only in-app "Capture audit bundle" button) is
  documented in
  `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 2; not yet
  shipped.
- v3 (Maestro click-through) is documented in § 3 of the
  same spec; not yet shipped.

## Cross-references

- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — the three-tier
  audit automation spec; this script is the v1.5 step.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — proof checklist
  P1–P8 the screenshots feed.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — installed-
  device QA gate every release passes through.
- `scripts/mobile-simulator-audit.mjs` — earlier
  single-screenshot helper with route-smoke + Metro check.
  This new script is a focused per-screen variant with a
  manifest.
