# Home Screen Widget Scaffold

Planned-first widget for fast daily grappling context. This document
defines the shared app-side data contract before adding native
WidgetKit / Android widget targets.

## Modes

The widget family has two independent modes:

1. **User widget** — product-facing grappling context. Available to
   normal users. Reads product-safe app state only.
2. **Admin/Developer widget** — project operations summary. Hidden
   behind admin entitlement. Reads developer MCP summaries only.

The two modes use separate data adapters and separate persisted JSON
payloads. Native widget code must never merge the payloads.

## User Data Adapter

Canonical adapter:

```ts
buildHomeWidgetContext({ platform, state })
```

Source file: `apps/mobile/src/services/home-widget-context.ts`.

The adapter consumes `AppAthleteState` only. It does not read
Developer MCP, Admin/Dev, terminal, release, build, or audit state.

## User Widget Content

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

## Admin Data Adapter

Canonical adapter:

```ts
buildAdminHomeWidgetContext(input)
```

Source file:
`apps/mobile/src/services/admin-home-widget-context.ts`.

The adapter returns `null` unless `adminEntitled === true`. It accepts
only summarized MCP/control-centre fields:

- MCP freshness and last writeback age;
- Claude, Codex, Agent lane states;
- next prompt target lane only, not prompt text;
- human approval count;
- build and QA gate status;
- overnight and audit queue counts;
- deep link to `/admin-dev`.

It does not accept raw logs, raw prompts, tokens, file paths, private
worker text, or full queue details.

## Admin Widget Content

Small admin widget should render:

- MCP freshness: `fresh`, `stale`, or `missing`;
- last writeback age;
- lane strip: Claude / Codex / Agent;
- next prompt target, e.g. `Codex`;
- approval count;
- build / QA gate chips;
- overnight / audit queue counts;
- tap target opening Admin/Dev.

The admin widget is Developer MCP only and must stay hidden for
non-admin users. It can show queue summaries, never full sensitive
details.

## iOS Plan

- Add a WidgetKit extension target in the native iOS project.
- Share `HomeWidgetContext` JSON through an App Group container, e.g.
  `group.com.lauburu.grapplingmap`.
- Share `AdminHomeWidgetContext` as a separate App Group JSON file
  only after admin entitlement is active; delete it on sign-out or
  entitlement loss.
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
- Store the admin widget JSON separately and clear it when admin
  entitlement is absent.
- Schedule refresh on app resume, after sync, and via WorkManager with
  conservative cadence.
- Widget pending intents deep link to journal, timer, and health tabs.

## Safety Rules

- Product-safe data only.
- No Developer MCP, Admin/Dev, release, terminal, or audit state.
- Missing or stale native health source forces stale/missing
  readiness labels.
- User widget and Admin widget use separate adapters and storage keys.
- Admin widget requires admin entitlement and Developer MCP only.
- No secrets, raw logs, prompt text, tokens, private worker text, or
  sensitive queue details in either widget.
- Simulator/emulator or repo-only evidence must never be phrased as
  installed-device verification.
- Native widget implementation requires a new app build, but this
  scaffold does not run or claim one.
