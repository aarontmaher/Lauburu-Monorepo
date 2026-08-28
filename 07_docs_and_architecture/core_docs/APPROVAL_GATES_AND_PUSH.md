# Approval gates + iPhone push notifications

Status: scaffold-only doc. The approval-gate model is repo-ready
(commit landed in this batch); push notifications are NOT wired —
this doc lists the exact prerequisites Aaron has to satisfy before
push goes live.

## What works today

- **Pure transition machine** at
  `packages/shared/src/approval-gates/index.ts` — `makeApprovalGate`,
  `approveGate`, `deferGate`, `cancelGate`, `completeGate`,
  `expireIfDue`, plus `looksLikeSecret` to refuse secret-shaped
  text. State enum: `pending | approved | deferred | expired |
  cancelled | completed`.
- **Synthetic gate ring** at `data/approval-gates/gates.json` with
  three live entries (Android v20 Play upload, worker deploy of
  project.ping, FS-020 Agent QA).
- **Mobile store** at
  `apps/mobile/src/store/approval-gates-store.ts` — hydrates from
  secureStorage with the JSON file's contents seeded on first run;
  exposes `approve`, `defer`, `cancel`, `markCompleted`,
  `applyExpiries`. Optimistic local state changes; safeDefault
  rules enforced.
- **Admin/Dev section** at the top of
  `apps/mobile/app/admin-dev.tsx` (right after `AgentStatusSection`)
  showing each gate, an Approve / Defer 24h / Cancel button row
  per active gate, and a Copy-last-ledger-note button so Aaron can
  paste the writeback into `data/action-ledger/pending_actions.json`
  manually until the server route lands.
- **In-app banner** for "all workers need direction" (existing
  `useAdminDevNotificationStore`) keeps working alongside the new
  approval-gate UI.
- **Pure-transition test** at
  `cloudflare-worker/test/test-approval-gates-transitions.ts`
  covers construction guards, transition guards, expiry idempotency,
  and secret-shaped resolutionNote refusal.

## What does NOT work today (push)

- The mobile app does NOT depend on `expo-notifications`. Adding it
  is a native dependency change — bundles into the next EAS build,
  not the current installed v20.
- There is no Expo push token registration flow.
- There is no backend route to deliver pushes.

Until those three land, the only "notification" surfaces Aaron has
are: the in-app banner (when he opens Admin/Dev) and the
approval-gate list.

## Push setup blockers (in order)

1. **Confirm Aaron wants iPhone push at all.** Push notifications
   require Apple Developer entitlement work + Expo push project
   setup. Skip if Aaron prefers in-app + ChatGPT pings.
2. **Add `expo-notifications` to `apps/mobile/package.json`.**
   Native dependency. Triggers a new EAS build, gated on Aaron
   approval per the existing build-cost rule.
3. **Capability check** in Apple Developer Portal:
   `com.lauburu.grapplingmap` → Identifiers → enable **Push
   Notifications**. Re-run `npx eas-cli credentials --platform ios`
   after the change and let EAS regenerate the provisioning
   profile.
4. **Expo push** — register a default channel for Android
   (`Notifications.setNotificationChannelAsync`) + register for
   permission (`Notifications.requestPermissionsAsync`) in a new
   `apps/mobile/src/services/push-notifications.ts` module. The
   token (`Notifications.getExpoPushTokenAsync({ projectId: <eas
   projectId> })`) is per-device and should be stored in Supabase
   alongside the admin email — never in repo, never in MCP public
   surfaces.
5. **Backend delivery route** — a new admin-token-gated POST
   endpoint that fans out a push via `expo-server-sdk` to all
   registered admin devices. The MCP project.list_approval_gates
   tool (future) can call this when a P0 gate is created or
   30-min before expiry.
6. **Privacy** — pushes carry only the gate id and title. Body
   stays generic ("Approval gate pending — open Lauburu Admin/Dev
   to review"). Description, payload, and ledger note never leave
   the device unless the user opens the app.

When step 5 ships, the mobile store's `refresh()` becomes a real
MCP fetch (project.list_approval_gates) and gates created remotely
arrive on-device without a manual paste.

## Manual ledger writeback path (today)

When Aaron approves / defers / cancels a gate, the store emits a
ledger note string and surfaces it as a "Copy last ledger note"
button. To resume any automation that depends on the gate:

1. Tap **Copy last ledger note**.
2. Open `data/action-ledger/pending_actions.json` (laptop).
3. Paste the note into the matching `pendingAction.evidenceSummary`
   line, set `status` from `pending` to `completed` if the gate's
   `actionType` matches the lane, and bump `updatedAt`.
4. Run `npm run bridge:snapshot` so the change reaches MCP.

The store keeps the most recent 20 ledger notes locally so a
laptop-less day can be reconciled later.

## Anti-rules (apply across all gates)

- safeDefault MUST never be `proceed` or `deploy`. The current set
  is `skip | wait | rollback | notify_only` and is enforced at
  construction time.
- Push payload MUST NOT include description / actionPayload /
  resolutionNote text. Title + id only.
- Gates MUST NOT be auto-approved by automation. Only Aaron, or
  `system:expiry` applying safeDefault, may resolve a gate.
- A cancelled / expired / completed gate cannot be re-opened. Open
  a new gate with a fresh id instead.
- If a future MCP tool (`project.approve_gate`) lands, it MUST
  require admin token; ChatGPT-no-auth callers MUST be rejected
  with the soft `admin token required` error.
- The data/approval-gates/gates.json file is part of repo state
  and must NOT carry secrets, real device IDs, or build URLs that
  rotate frequently. Pin to short stable identifiers.

## Push action category (repo-ready scaffold)

The pure mapper + the lazy expo-notifications scaffold landed
ahead of the EAS build that adds the dep, so when Aaron
approves the build the wiring is already in place. Files:

- `packages/shared/src/approval-gates/push.ts` — pure helpers:
  `mapNotificationActionToGateMutation` (action id → mutation
  envelope), `APPROVAL_CATEGORY_IDENTIFIER`
  (`lauburu_approval_gate_v1`), `DEFAULT_NOTIFICATION_DEFER_HOURS`
  (24). No React Native / Expo / fs deps; testable in node.
- `apps/mobile/src/services/push-approval-notifications.ts` —
  app-side surface: re-exports the pure mapper + adds three
  lazy-loaded helpers (`registerApprovalCategory`,
  `scheduleLocalApprovalReminder`, `dispatchNotificationAction`)
  that all `require('expo-notifications')` and gracefully no-op
  when the dep is absent. Today every helper returns
  `{ ok: false, reason: 'expo-notifications not installed' }`.
- `cloudflare-worker/test/test-push-approval-action-mapping.ts`
  locks the mapper contract: 3 known action ids
  (approve / deny / defer); empty / non-string inputs → null;
  case-insensitive match; whitespace NOT trimmed (any drift
  surfaces immediately); approve / deny carry fixed reason
  strings; defer adds 24h to `now()` by default; non-positive
  `deferHours` falls back to default; `APPROVAL_CATEGORY_IDENTIFIER`
  stable.

### Action category contract (registered when expo-notifications lands)

| Action id | Button title | Options | Effect |
|---|---|---|---|
| `approve` | Approve | foreground=false | `useApprovalGatesStore.approve(gateId, 'approved via push notification action')` |
| `defer` | Defer 24h | foreground=false | `useApprovalGatesStore.defer(gateId, +24h, 'deferred via push notification action')` |
| `deny` | Deny | foreground=true (opens app), destructive=true | `useApprovalGatesStore.cancel(gateId, 'denied via push notification action')` |

`Approve` and `Defer` resolve from the lock screen without
opening the app; `Deny` opens the app to the approval centre
because cancel is destructive and benefits from a confirm
glance. Either way, the existing approval-gate centre on
Admin/Dev is the canonical fallback if the lock-screen action
fails to deliver — the gate stays `pending` and Aaron resolves
it from the in-app surface.

### iOS lock-screen behaviour (notes for the install-approving session)

- iOS delivers the user's tap to the app via
  `UNNotificationResponse.actionIdentifier`. The handler
  `dispatchNotificationAction(response)` reads
  `notification.request.content.data.gateId`, runs the pure
  mapper, and applies the resulting store mutation.
- iOS may delay action delivery if the device is locked +
  passcode required. The `Deny` action's `foreground=true`
  ensures the user sees the in-app gate state rather than a
  silent denial.
- Aaron may receive multiple reminders for the same gate (one
  per `scheduleLocalApprovalReminder` call) — the helper
  refuses to schedule when `expiresAt - leadMinutes` is in
  the past, but it's idempotent only by hash of the trigger
  date, not by gateId. Future Codex work: add a
  `cancelLocalApprovalReminder(gateId)` to fan-out cancels
  when the gate resolves; today the user just dismisses the
  duplicate.
- Action button text MUST stay short (iOS truncates
  aggressively on lock screen). `Approve`, `Defer 24h`, `Deny`
  all fit comfortably.

### Wiring once expo-notifications is added (pseudocode)

Inside the app's root layout's `useEffect(() => {}, [])`:

```ts
import * as Notifications from 'expo-notifications';
import {
  registerApprovalCategory,
  dispatchNotificationAction,
} from '@/src/services/push-approval-notifications';

useEffect(() => {
  void registerApprovalCategory();
  const sub = Notifications.addNotificationResponseReceivedListener((response) => {
    void dispatchNotificationAction(response);
  });
  return () => sub.remove();
}, []);
```

No new MCP tool, no backend route, no app-state persistence
beyond what the approval-gates store already does.

## Codex handoff (next implementation batch)

Only fires when Aaron approves the push setup AND has completed
steps 1–3 above:

> Add `expo-notifications` to apps/mobile, register an Expo push
> token in `apps/mobile/src/services/push-notifications.ts` (lazy
> import, Android-channel safe), persist token to Supabase
> `admin_devices` row (new migration). Add backend POST
> `/api/admin/notify-approval-gate` (admin-token gated) that fans
> out an Expo push with title = approval-gate title, body =
> generic "Open Lauburu Admin/Dev". MCP tool
> project.notify_approval_gate (admin-only) on /mcp/v2/admin so
> automation can fire pushes from the worker. No EAS build until
> Aaron approves; bundle this with another mobile change to keep
> build cost down. Tests: extend test-approval-gates-transitions
> with a "notify-on-approve hook" assertion.
