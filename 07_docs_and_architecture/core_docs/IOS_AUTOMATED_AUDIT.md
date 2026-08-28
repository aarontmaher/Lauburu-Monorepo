# iOS Automated Audit Path

This is a repeatable simulator-first audit path for Grappling Map. It is public-safe UI evidence only.

## Maestro Simulator Audit

Run:

```sh
audit-system/run-audit.sh --platform ios --suite ios
```

Optional single flow:

```sh
audit-system/run-audit.sh --platform ios --suite ios --flow 02-ios-health-apple-health
```

Output:

```text
artifacts/app-audit/maestro/ios/ios-build-<build>/<timestamp>/
  *.png
  manifest.json
  agent-audit-manifest.json
  agent-handoff.md
```

The manifest lists the flows, captured screenshots, failed flows, platform, build identity, repo SHA, and the installed-device gate rule. `agent-handoff.md` is the public-safe handoff format for Agent review.

## Screens Covered

- Launch.
- Home before refresh.
- Home after refresh.
- Home readiness entry point.
- Health tab.
- Apple Health status.
- Manage Sources.
- Health after refresh.
- Readiness card labels for provisional/stale/error states when present.
- Journal.
- Journal after refresh.
- Admin/Dev before refresh.
- Admin/Dev after refresh.
- Overnight Prompt Queue.
- Control/queue tab when available.

## Gate Rule

Simulator evidence can find bugs, stale labels, missing copy, broken navigation, and Admin/Dev disagreement. It cannot clear installed-device gates and must not be described as installed-device verified.

Real iPhone evidence still requires iPhone Mirroring or TestFlight installed on a physical iPhone, plus Apple Health device checks.

## XCUITest Plan

Use XCUITest for deeper native coverage after the Maestro path is stable:

1. Add a native iOS test target in the generated iOS workspace after prebuild.
2. Launch the app by bundle identifier `com.lauburu.grapplingmap`.
3. Add accessibility identifiers for primary audit anchors: Home, Readiness, Health, Manage Sources, Apple Health status, Journal, Admin/Dev, MCP freshness, Overnight Prompt Queue.
4. Capture XCTest attachments for the same screen list as the Maestro suite.
5. Assert presence of truthful states without relying on real Apple Health data in simulator.
6. Keep the XCUITest artifact manifest compatible with `agent-audit-manifest.json`.
7. Treat simulator XCUITest as repo-only evidence; physical iPhone Apple Health verification remains separate.
