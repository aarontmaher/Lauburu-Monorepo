# Health source truth labels — v21 contract

This is the spec the v21 installed-device QA cycle holds the app to.
Every surface that consumes the platform-native health source (Apple
Health on iOS, Health Connect on Android) must reach the **same**
verdict on whether the source is fresh, stale, or never-connected.
Drift between surfaces is exactly the failure mode the v21 audit
runner is designed to catch.

## Single source of truth

`apps/mobile/src/services/native-health-freshness.ts` exports:

- `NATIVE_HEALTH_STALE_HOURS = 48`
- `NATIVE_HEALTH_STALE_MS = 48 * 60 * 60 * 1000`
- `isNativeHealthSyncStale(lastSyncAt, nowMs?)` → `boolean`
- `hoursSinceNativeHealthSync(lastSyncAt, nowMs?)` → `number | null`

Behaviour pinned by `cloudflare-worker/test/test-native-health-freshness.ts`:

| Input | `isNativeHealthSyncStale` | `hoursSinceNativeHealthSync` |
|---|---|---|
| `null` / `undefined` | `false` | `null` |
| Unparseable string | `false` | `null` |
| 1 h ago | `false` | `1` |
| Exactly 48 h ago | `false` | `48` |
| 48 h + 1 ms ago | `true` | `48` |
| 10 days ago | `true` | `240` |
| Future timestamp (clock skew) | `false` | `0` (clamped) |

> **No record ≠ stale.** The Manage Sources sheet renders three
> distinct labels — `Connected`, `Stale`, `synced with no recent
> data`, `Permission needed`, `Sync failed — retry` — depending on
> which combination of `lastSyncAt`, `appleHealthConnected`, and
> `nativeAnyAuthorized` holds. `is_stale` only fires when there IS
> a `lastSyncAt` and it is older than the threshold.

## Surfaces wired to the helper

| Surface | What it consumes | Test |
|---|---|---|
| `HealthActionsPanel` (Manage Sources sheet + summary line) | `isNativeHealthSyncStale(lastSyncAt)` | `test-health-connect-native-stale-label.ts` (asserts the import + that the helper is NOT redeclared locally) |
| `AppAthleteState.source_roles.native_health.{freshness_hours, is_stale, stale_threshold_hours}` | `hoursSinceNativeHealthSync` + `isNativeHealthSyncStale` + `NATIVE_HEALTH_STALE_HOURS` | `test-app-athlete-state-native-source.ts` |
| Coach AI evidence builder (`evidence-aware-ai.ts`) | reads `nativeHealthRole.is_stale` / `freshness_hours` / `stale_threshold_hours`; emits inline `· STALE (last sync Nh ago, threshold 48h)` or `· synced Nh ago` on the source-roles line | `test-evidence-aware-ai-native-source.ts` |
| Home widget (`home-widget-context.ts`) | already used `data_quality.freshness_hours.native_health` and a parallel 48 h threshold; remains unchanged this round (planned-only follow-up: import the constant from the shared helper) | `test-home-widget-context.ts` |

## Why the Coach AI line matters

Before this contract, the Coach evidence summary said:

```
Apple Health: broad_baseline · 14 days of history · covers today
```

…regardless of how stale the data was. If the user hadn't synced in
five days, the model still saw "covers today" and would reason as
though today was a live read.

Post-contract:

```
Apple Health: broad_baseline · 14 days of history · covers today · STALE (last sync 132h ago, threshold 48h)
```

The model now has the freshness signal inline and can hedge or
explicitly call out "the broad baseline source is stale; today's
state is provisional."

The signal is intentionally on the same line, not in a separate
"warnings" block — the model is more likely to use a value that's
attached directly to the claim it qualifies than one buried under a
heading.

## What this contract does NOT do

- **Does not** change the stale threshold. 48 h is locked in
  `test-native-health-freshness.ts` with explicit just-under /
  exactly-on / just-over assertions. Any change to the threshold
  has to land alongside an updated test.
- **Does not** change UI labels. The Manage Sources sheet copy
  remains `Stale` / `Connected` / `Permission needed` / etc.
- **Does not** mutate Product MCP. `is_stale` is a derived field
  on the in-memory `AppAthleteState`; nothing flows through the
  evidence-promotion path on the strength of staleness alone.
- **Does not** clear any release-qa-gate item. Even with the
  truth label correct in-app, an installed-device audit run is
  still required to clear the v21 gate per
  `audit-system/AUDIT_RUNNER.md` (in the MCP repo).

## Verifying

```sh
# Helper behaviour (real runtime, no React-Native imports):
cd cloudflare-worker && npx tsx test/test-native-health-freshness.ts

# Source-level contracts on the consumers:
npx tsx test/test-health-connect-native-stale-label.ts
npx tsx test/test-app-athlete-state-native-source.ts
npx tsx test/test-evidence-aware-ai-native-source.ts

# Whole-app type sanity:
( cd packages/shared && npx tsc --noEmit )
( cd apps/mobile && npx tsc --noEmit )
```

All five must exit 0.
