# iPhone Mirroring QA workflow — `npm run audit:iphone-mirroring`

Phone-first audit for the **real installed iPhone build**.
Aaron mirrors the iPhone onto the Mac (macOS 15+ Continuity
feature), captures screenshots with the standard Mac shortcut,
and the script collects them, names them, and writes a
manifest. No USB, no dev cert, no UI automation, no Aaron
sitting at the laptop typing commands per screen.

This is the **real-iPhone companion** to
`scripts/audit-screenshots.mjs` (simulator/emulator driver in
`docs/AUDIT_SCREENSHOTS.md`). Both write into
`artifacts/app-audit/<sub-path>/<isoTimestamp>/` — `simulator/`
vs `iphone-mirroring/` — and use the same JSON-shape principles.

This workflow honours the **complete mobile-only admin /
developer workflow** quality bar in
`docs/APP_DEVELOPMENTS.md` § Permanent improvement
categories: Aaron taps screenshots on the iPhone (or the
mirrored window on the Mac); the script handles the rest.

## Pre-requisites

| Item | Required |
|---|---|
| macOS | **15.0 or later** (iPhone Mirroring shipped with macOS 15 / Sequoia) |
| iPhone | iOS 18 or later, signed in to the same iCloud account as the Mac, two-factor auth on |
| Network | iPhone unlocked, on the same Wi-Fi as the Mac OR within Bluetooth range |
| App | iPhone Mirroring app installed in `/Applications/` (macOS ships it; absent only if you've manually deleted it) |

Confirm: `sw_vers -productVersion` reports ≥ 15. The script
itself refuses to run on any other platform.

## One-time setup

1. iPhone → Settings → General → AirPlay & Continuity →
   **Mirror My iPhone** → ON.
2. Mac → open **iPhone Mirroring** app from Launchpad. The
   first launch displays the iPhone's Lock Screen.
3. Tap **Get Started** on the iPhone screen, then on the iPhone
   itself unlock + approve the connection.
4. Once mirrored, the iPhone screen renders inside a small
   floating window on the Mac. Macros / dock / Mission Control
   work as normal.
5. Optional: System Settings → Desktop & Dock → "Save
   screenshots to" → choose a stable folder such as
   `~/Desktop` or `~/Downloads`. Pass the same folder to the
   script with `--watch-dir`; do not manually move screenshots
   between folders before ingestion.

## Capture workflow

For each screen Aaron wants to audit:

1. In the iPhone Mirroring window, tap through to the screen.
2. On the Mac, press **Cmd-Shift-4 → Space → click the iPhone
   Mirroring window**. macOS captures the iPhone-shaped frame
   only.
   - Cmd-Shift-3 captures the whole Mac display (overkill for
     this flow).
   - Cmd-Shift-5 opens the screenshot palette if Aaron prefers
     a configurable shortcut.
3. The PNG lands in the configured Save-to folder.
4. Repeat for as many screens as the audit requires. The
   recommended 9-screen catalogue from
   `docs/AUDIT_SCREENSHOTS.md` § "Screen catalogue" is a good
   starting point; add Manage-Sources / Approval-gates /
   Spend-gates expansions per
   `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` § 1.

Then run the script against that same Save-to folder:

```
npm run audit:iphone-mirroring -- --watch-dir ~/Downloads
```

The script:
- Defaults to `~/Desktop` as the watch dir.
- Expands `~` and `~/...` correctly, leaves absolute and
  relative paths unchanged, and rejects `~username/...` paths
  with a clear error.
- Scans for `.png` files modified in the last 10 minutes.
- Lists them in mtime order (the order Aaron captured).
- Prompts per file for a short label
  (e.g. `admin-dev-top`, `admin-dev-mcp`, `health-sources`).
- Refuses to ingest filenames containing token / secret /
  jwt / sk- / ghp_ / AKIA / password / bearer / whsec_ /
  apikey hints.
- Moves files into
  `artifacts/app-audit/iphone-mirroring/<isoTimestamp>/`
  with a `01-<label>.png`, `02-<label>.png` naming.
- Prompts for manifest fields (iOS build number, app version,
  device, iOS version, macOS version, free-form notes).
- Writes `manifest.json`.

## Naming convention

```
01-admin-dev-top.png
02-admin-dev-mcp.png
03-health-sources.png
04-home.png
05-settings.png
```

The leading 2-digit prefix keeps Finder + Agent reviewers
sorted in capture order. Aaron is free to add screens beyond
05; the script will continue 06-, 07-, ...

The label is the part Aaron types when prompted; it's
slugified (`Admin/Dev MCP — top` becomes `admin-dev-mcp-top`).

## Manifest schema

`manifest.json` is locked by
`cloudflare-worker/test/test-audit-screenshots-manifest.ts`.

```json
{
  "schemaVersion": 1,
  "captureMethod": "iphone_mirroring",
  "iosBuildNumber": "20",
  "appVersion": "0.1.0",
  "device": "iPhone 15 Pro",
  "iosVersion": "18.2",
  "macosVersion": "15.2",
  "capturedAt": "2026-05-09T12:00:00.000Z",
  "screens": [
    { "filename": "01-admin-dev-top.png", "screen": "admin-dev-top", "notes": "" },
    { "filename": "02-admin-dev-mcp.png", "screen": "admin-dev-mcp", "notes": "" }
  ],
  "notes": ""
}
```

Field defaults: missing string fields land as `null`;
`screens` always an array (possibly empty); `notes` always a
string (possibly empty).

## Flags (skip the prompts)

```
node scripts/iphone-mirroring-audit.mjs \
  --watch-dir ~/Downloads \
  --labels admin-dev-top,admin-dev-mcp,health-sources,home,settings \
  --ios-build 20 \
  --app-version 0.1.0 \
  --device "iPhone 15 Pro" \
  --ios-version 18.2 \
  --macos-version 15.2 \
  --notes "v20 health-connect retest cycle 1" \
  --zip
```

Other flags:

- `--watch-dir <path>` — scan a different directory (e.g.
  `~/Downloads` or `~/Pictures/Screenshots` if that is your
  macOS screenshot Save-to folder).
- `--window <minutes>` — how far back to scan (default 10).
- `--auto-launch` — opt-in helper that opens iPhone Mirroring
  before scanning; screenshots still need to be captured into
  the watched folder.
- `--dry-run` — print what would happen without moving files
  or writing the manifest.
- `--non-interactive` — required when no labels are supplied
  but you also don't want prompts; the screens get fallback
  ids `screen-01`, `screen-02`, etc. Useful from CI.

## `--zip` handoff

If you pass `--zip`, the script shells to the system `zip`
binary (built into macOS) and produces
`artifacts/app-audit/iphone-mirroring/<ts>.zip` next to the
folder. AirDrop the zip to whoever is reviewing — Aaron is
the courier; the script never auto-shares.

## Anti-rules

- **No commit of `artifacts/`.** The dir is gitignored.
  `git status` should stay clean after a capture run.
- **No raw secrets / tokens / PII in screenshots.** Crop or
  blur before saving, or skip that screen. The script
  refuses obvious-token filenames as a last line of defence;
  it does NOT OCR the image.
- **No autosharing to MCP / Slack / public surfaces.**
  Captures are local-first; Aaron decides every share.
- **No platform fallback.** macOS only — Linux / Windows are
  hard-failed early. iPhone Mirroring is a macOS feature.
- **No app code changes from this workflow.** Pure shell-out
  + filesystem ops.
- **No EAS build.** This workflow audits whatever's already
  installed; bumping the build is a separate Aaron-approved
  flow.
- **No installed-device product QA claim from mirroring alone.**
  Mac-side iPhone Mirroring screenshots are workflow evidence;
  release gates still need the matching installed-device QA
  verdict and any Apple Health device checks.

## Troubleshooting

- *"No .png files modified in the last 10 minutes"* —
  capture screenshots first; or pass `--window 60` if you
  captured > 10 min ago. Confirm the script's `--watch-dir`
  matches the actual Save-to folder in System Settings →
  Desktop & Dock.
- *"Refusing to ingest filenames…"* — rename or delete the
  flagged file; the heuristic protects against accidental
  secret captures. If it's a false positive, rename the
  file (e.g. `Screenshot 2026-05-09 token.png` →
  `Screenshot 2026-05-09 reference.png`).
- *iPhone Mirroring won't launch* — Mac System Settings →
  General → AirPlay & Handoff: confirm AirDrop is on; iPhone
  Settings → AirPlay & Continuity → Mirror My iPhone is on;
  iPhone is unlocked; both devices on the same iCloud
  account with 2FA active.

## Cross-references

- `docs/AUDIT_SCREENSHOTS.md` — simulator/emulator driver
  (`npm run audit:screenshots`); same `artifacts/` parent.
- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` — three-tier audit
  spec; this workflow slots into the v1 manual tier with
  much less manual overhead.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — proof checklist
  P1–P8 the screenshots feed.
- `docs/INSTALLED_DEVICE_QA_RELEASE_GATE.md` — installed-
  device QA gate every release passes through.
- `docs/APP_DEVELOPMENTS.md` § Permanent improvement
  categories — the "complete mobile-only admin / developer
  workflow" quality bar this workflow satisfies.
- `scripts/iphone-mirroring-audit.mjs` — the script.
- `scripts/audit-screenshots-helpers.mjs` — shared helpers
  (manifest builder, slug, suspicious-filename guard).
