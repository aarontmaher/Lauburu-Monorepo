# Home Screen Widget Scaffold

Planned-first widget for fast daily grappling context. This document
defines the shared app-side data contract before adding native
WidgetKit / Android widget targets.

## Data Adapter

Canonical adapter:

```ts
buildHomeWidgetContext({ platform, state })
```

Source file: `apps/mobile/src/services/home-widget-context.ts`.

The adapter consumes `AppAthleteState` only. It does not read
Developer MCP, Admin/Dev, terminal, release, build, or audit state.

## Widget Content

Small widget should render:

- readiness label, e.g. `Provisional mid`, `Readiness stale`,
  `Readiness needs data`;
- next action: `Open timer`, `Review recovery`, `Start journal`,
  `Connect health`, or `View readiness`;
- native health source: `Apple Health` on iOS, `Health Connect` on
  Android;
- compact truth chips: `provisional`, `stale`, `missing`, `fresh`;
- quick actions: Journal, Timer, Readiness.

Readiness score is `null` unless the context is fresh. Current
AppAthleteState seed mode keeps widget readiness provisional, so the
widget must not display a strong numeric readiness claim.

## iOS Plan

- Add a WidgetKit extension target in the native iOS project.
- Share `HomeWidgetContext` JSON through an App Group container, e.g.
  `group.com.lauburu.grapplingmap`.
- Mobile app writes the latest context after health/training/journal
  state changes and asks WidgetKit to reload timelines.
- Widget deep links:
  - `lauburu://journal`
  - `lauburu://timer`
  - `lauburu://readiness`

## Android Plan

- Add an Android AppWidget provider (Glance if the project can absorb
  the dependency, otherwise RemoteViews).
- Share the same `HomeWidgetContext` JSON through app-private storage
  exposed to the widget process.
- Schedule refresh on app resume, after sync, and via WorkManager with
  conservative cadence.
- Widget pending intents deep link to journal, timer, and health tabs.

## Safety Rules

- Product-safe data only.
- No Developer MCP, Admin/Dev, release, terminal, or audit state.
- Missing or stale native health source forces stale/missing
  readiness labels.
- Simulator/emulator or repo-only evidence must never be phrased as
  installed-device verification.
- Native widget implementation requires a new app build, but this
  scaffold does not run or claim one.
