# scrcpy Android audit workflow — `npm run audit:android-scrcpy`

Real-Android companion to
`docs/IPHONE_MIRRORING_QA_WORKFLOW.md`. Aaron pairs the Android
device, runs `scrcpy` to mirror it onto the Mac, captures
screenshots with Cmd-Shift-4 → Space → click the scrcpy window,
then runs the script. The script collects new PNGs, refuses
suspicious filenames, prompts for labels + manifest fields, and
writes the bundle to
`artifacts/app-audit/android-scrcpy/<isoTimestamp>/`.

`artifacts/` is gitignored — bundles never reach the repo.

## Pre-requisites

| Item | Required |
|---|---|
| macOS | macOS 12+ recommended; the script hard-fails on non-darwin platforms because Aaron's audit chain is Mac-only. |
| Android device | USB or Wi-Fi-paired with `adb`. Developer options + USB debugging on. |
| `adb` | `brew install android-platform-tools` |
| `scrcpy` | `brew install scrcpy` |
| Lauburu app | Installed on the device (Play Internal tester build OR Expo dev client). |

Confirm:

```sh
adb devices             # one device should show "device" state
scrcpy --version        # ≥ 2.4 recommended
sw_vers -productVersion # macOS version (just for the manifest)
```

## Capture workflow

1. Plug the Android device in (or connect Wi-Fi adb).
2. In a separate terminal: `scrcpy`. A Mac window appears
   showing the device.
3. In the scrcpy window, navigate the app to each screen Aaron
   wants to audit.
4. For each screen: Mac-side keyboard shortcut **Cmd-Shift-4 →
   Space → click the scrcpy window**. macOS captures the device
   frame only (not the surrounding desktop).
   - Cmd-Shift-3 captures the whole Mac display (overkill).
   - Cmd-Shift-5 opens the screenshot palette.
5. The PNGs land in `~/Desktop` (or whatever Save-to is set to).
6. Run `npm run audit:android-scrcpy`.

The script:
- Defaults to `~/Desktop` as the watch dir (override with
  `--watch-dir`).
- Scans for `.png` files modified in the last 10 minutes
  (override with `--window`).
- Lists them in mtime order (the order Aaron captured).
- Prompts per file for a short label
  (e.g. `admin-dev-top`, `health-sources`).
- Refuses to ingest filenames containing token / secret / jwt /
  sk- / ghp_ / AKIA / password / bearer / whsec_ / apikey hints.
- Moves files into
  `artifacts/app-audit/android-scrcpy/<isoTimestamp>/` with a
  `01-<label>.png`, `02-<label>.png` naming.
- Prompts for manifest fields (Android versionCode, app version,
  device, Android version, macOS version, free-form notes).
- Writes `manifest.json`.

## Manifest schema

`manifest.json` is locked by
`cloudflare-worker/test/test-audit-screenshots-manifest.ts`.

```json
{
  "schemaVersion": 1,
  "captureMethod": "scrcpy_android",
  "androidVersionCode": 20,
  "appVersion": "0.1.0",
  "device": "Pixel 8a",
  "androidVersion": "15",
  "macosVersion": "15.2",
  "capturedAt": "2026-05-09T12:00:00.000Z",
  "screens": [
    { "filename": "01-admin-dev-top.png", "screen": "admin-dev-top", "notes": "" },
    { "filename": "02-health-sources.png", "screen": "health-sources", "notes": "" }
  ],
  "notes": ""
}
```

## Flags

```sh
node scripts/audit-android-scrcpy.mjs \
  --labels admin-dev-top,admin-dev-mcp,health-sources,home,settings \
  --android-version-code 20 \
  --app-version 0.1.0 \
  --device "Pixel 8a" \
  --android-version 15 \
  --macos-version 15.2 \
  --notes "v20 health-connect retest cycle 1" \
  --zip
```

Other flags:
- `--watch-dir <path>` — scan a different directory.
- `--window <minutes>` — how far back to scan (default 10).
- `--dry-run` — print what would happen without moving files.
- `--non-interactive` — required when no labels are supplied
  but you also don't want prompts; screens get fallback ids
  `screen-01`, `screen-02`, etc.

## `--zip` handoff

If you pass `--zip`, the script shells to the system `zip` and
produces `artifacts/app-audit/android-scrcpy/<ts>.zip` next to
the folder. AirDrop / share manually — the script never
auto-shares.

## Anti-rules

- **No commit of `artifacts/`.** The dir is gitignored.
- **No raw secrets / tokens / PII in screenshots.** Crop or
  blur before saving, or skip that screen. The script refuses
  obvious-token filenames as a last line of defence.
- **No autosharing to MCP / Slack / public surfaces.**
  Captures are local-first; Aaron decides every share.
- **No platform fallback.** macOS only — Linux / Windows are
  hard-failed early.
- **No app code changes from this workflow.** Pure shell-out
  + filesystem ops.
- **No EAS build.** This workflow audits whatever is already
  installed.

## Troubleshooting

- *"adb: command not found"* — `brew install android-platform-tools`.
- *"scrcpy: command not found"* — `brew install scrcpy`.
- *Device shows "unauthorized" on `adb devices`* — accept the
  USB debugging prompt on the device.
- *scrcpy launches but the window stays black* — confirm
  `Developer options → Stay awake` is on, lock-screen rotation
  is set, and the device isn't in Battery Saver.
- *"No .png files modified in the last 10 minutes"* — capture
  screenshots first; pass `--window 60` if you captured > 10
  min ago. Confirm `~/Desktop` is the actual Save-to folder via
  System Settings → Desktop & Dock.
- *"Refusing to ingest filenames…"* — rename or delete the
  flagged file. The heuristic protects against accidental
  secret captures. Rename the file if it's a false positive.

## Cross-references

- `docs/IPHONE_MIRRORING_QA_WORKFLOW.md` — iOS counterpart.
- `docs/AUDIT_SCREENSHOTS.md` — simulator/emulator driver.
- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — three-tier audit
  spec; this workflow slots into the v1.5 / real-device tier.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — proof checklist
  P1–P8 the screenshots feed.
- `apps/mobile/audit-flows/` — Maestro v3 flows that automate
  navigation entirely (run via `npm run audit:maestro`).
