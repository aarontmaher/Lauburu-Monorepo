# Maestro audit-flows

YAML flow scripts that drive the installed Lauburu app through every
tab + every Admin/Dev section + every gate row using
[Maestro](https://maestro.mobile.dev/). The flows are checked in; the
Maestro binary itself is installed locally per Aaron's preference.

This is the **v3 capture tier** referenced in
`docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 3. v1 manual recording and
v1.5 (`npm run audit:screenshots`) still work; v3 is the
fully-automated path.

## Pre-requisites

```sh
brew tap mobile-dev-inc/tap
brew install maestro
maestro --version    # expect ≥ 1.40
```

Plus: a booted iOS Simulator OR Android emulator/device with the
Lauburu app installed (Expo dev client OR a tester build). The flows
target `appId: com.lauburu.grapplingmap` which matches the production
bundle identifier on both platforms.

## Run

```sh
# Single flow:
maestro test apps/mobile/audit-flows/01-home.yml

# Basic launch + Home + Health/Manage Sources + Admin/Dev smoke:
audit-system/run-audit.sh --platform ios --flow 00-smoke-basic

# iOS simulator audit path:
audit-system/run-audit.sh --platform ios --suite ios

# Full suite:
maestro test apps/mobile/audit-flows/

# Or via the wrapper that builds a manifest + zips screenshots:
npm run audit:maestro
```

Wrapper output:

```
artifacts/app-audit/maestro/<platform>/<build>/<isoTimestamp>/
  01-home.png
  02-health.png
  ...
  manifest.json
  agent-audit-manifest.json
  agent-handoff.md
```

`artifacts/` is gitignored; bundles never reach the repo.

## Flow catalogue

| File | Captures |
|---|---|
| `00-smoke-basic.yml` | Launch + Home + Health/Manage Sources + Settings/Admin/Dev. |
| `00-launch.yml` | Cold launch + sign-in (skipped on dev-client where the device is already signed). |
| `01-home.yml` | Home tab. |
| `02-health.yml` | Health tab → Manage Sources sheet → close. |
| `03-train.yml` | Train tab → expand active session → close. |
| `04-feedback.yml` | Feedback tab → Daily Journal → Import Notes preview (post-FS-020) → close. |
| `05-map.yml` | Map tab → tap a known node → back. |
| `06-reference.yml` | Reference tab. |
| `07-syllabus.yml` | Syllabus tab. |
| `08-coaching-history.yml` | Coaching history tab. |
| `09-settings-admin-dev.yml` | Settings → Admin/Dev → walk every Section header. |
| `10-admin-dev-approval-gates.yml` | Admin/Dev → Approval gates Section → expand each row. |
| `11-admin-dev-spend-gates.yml` | Admin/Dev → AI spend gates Section → expand each row. |
| `12-admin-dev-research-offload.yml` | Admin/Dev → Deep Research offload Section → expand each row. |
| `99-teardown.yml` | Sign out (optional) so the next run starts cold. |

## iOS simulator suite

Run with `audit-system/run-audit.sh --platform ios --suite ios`.
These flows are simulator evidence only; they can find bugs but cannot
clear installed-device gates.

| File | Captures |
|---|---|
| `ios/00-ios-launch-refresh.yml` | Launch, Home before refresh, Home after refresh. |
| `ios/01-ios-home-readiness.yml` | Home and readiness entry point. |
| `ios/02-ios-health-apple-health.yml` | Health, Apple Health status, Manage Sources, after refresh. |
| `ios/03-ios-readiness-states.yml` | Readiness card labels including provisional/stale/error if present. |
| `ios/04-ios-journal.yml` | Journal and journal refresh state. |
| `ios/05-ios-admin-dev-queues.yml` | Admin/Dev before/after refresh and Overnight Prompt Queue. |
| `ios/06-ios-control-queue.yml` | Control/queue tab and after-refresh state if available. |

Each flow runs `takeScreenshot` after the relevant tap. The wrapper
script renames the captures `<flow-step>.png`, writes `manifest.json`,
`agent-audit-manifest.json`, and `agent-handoff.md`.

## Anti-rules

- Maestro flows MUST NOT drive a sign-in form with a real Apple ID
  or Aaron's Supabase account. Use a dedicated test account whose
  data stays inside QA.
- Health-data screens captured ONLY with explicit test-account
  consent. Never against Aaron's real account.
- `apps/mobile/audit-flows/` content stays under 50 lines per
  YAML — anything larger should be a new flow.
- The wrapper script must not auto-share bundles. Aaron is the
  courier when externalising audits; bundle stays in
  `artifacts/app-audit/maestro/<ts>/`.
- The wrapper must fail-soft when Maestro is missing — print the
  brew install command and exit 1 cleanly, never crash.

## Cross-references

- `docs/IN_APP_AUDIT_AUTOMATION_SPEC.md` § 3 — the v3 audit tier.
- `docs/AUDIT_SCREENSHOTS.md` — v1.5 simulator/emulator driver.
- `docs/IPHONE_MIRRORING_QA_WORKFLOW.md` — real-iPhone capture.
- `docs/AUDIT_SCRCPY_ANDROID.md` — real-Android capture via
  scrcpy mirroring.
- `docs/ADMINDEV_INSTALLED_PROOF_GAP.md` — the proof checklist
  these screenshots feed.
