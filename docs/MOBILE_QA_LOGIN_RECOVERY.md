# Mobile QA login + stale-session recovery

Quick reference for Aaron / Agent running simulator or
TestFlight QA on the mobile app. Updated 2026-05-08.

This doc is a runbook, not a spec. It pairs with
`apps/mobile/src/store/auth-store.ts` (the auth store with
explicit stale-session recovery added in the same commit as
this doc).

## 0. Why login could block QA

Aaron's previous QA attempt hit "Refresh Token Not Found" /
similar Supabase auth errors. These happen when the **locally
stored refresh token** has been consumed or invalidated server-
side, but the local SDK keeps trying to use it. Symptoms:

- App boots into `loading` and never reaches the Health tab.
- Toasts / console show `Refresh Token Not Found` or
  `invalid_grant`.
- Network calls fail with 401 even though the user "looks"
  signed in.
- Sign-in attempts succeed but the next launch goes back to
  the broken state.

The fix that landed alongside this doc detects these errors
and **automatically clears the bad local session**, dropping
the app to `guest` so a fresh sign-in works.

## 1. What auto-recovery does now

`auth-store.ts` now does three things differently:

1. `initialize()` catches stale-refresh-token errors, calls
   `supabase.auth.signOut({ scope: 'local' })` to wipe the
   bad token, and falls through to `guest`.
2. `onAuthStateChange()` handles `TOKEN_REFRESHED` events
   that arrive with a `null` session (which means the refresh
   itself failed) — drops cleanly to `guest`.
3. `getAccessToken()` detects stale-refresh errors mid-call,
   clears the local session, and returns null instead of
   looping.

In all three paths, the app reaches `guest` and the user can
sign in again. **Per-user cached data is preserved** —
`clearStaleAuthSession()` is auth-only; the per-user Zustand
caches (`clear-user-data.ts`) only run on explicit
`signOut()`.

## 2. QA simulator login flow (iOS / Android)

### 2.1 First-time / fresh simulator

1. Boot the simulator, install the app via `npx expo run:ios`
   or `npx expo run:android`.
2. App opens to the sign-in surface (because the auth store
   is `guest`).
3. Sign in with Aaron's Supabase account email +
   password. (Apple Sign-In / Google Sign-In also work on
   appropriate platforms.)
4. App transitions to `member`; tabs become reachable.

### 2.2 If you hit a stale-token error

Two paths, both safe:

**Path A — wait for auto-recovery (preferred).** The
auto-recovery in `auth-store.ts` clears the bad token within
~1 second of the error firing. Pull to refresh / restart the
app once; on relaunch you should land on the sign-in screen.

**Path B — manual reset (full nuclear).** Erases everything;
useful only if Path A doesn't fix it:

```
iOS Simulator:
  Device menu → Erase All Content and Settings
  → reinstall the app via npx expo run:ios

Android emulator:
  AVD Manager → ⋮ → Wipe Data → Cold Boot
  → reinstall the app via npx expo run:android
```

### 2.3 TestFlight install (Aaron's iPhone)

1. Open TestFlight on the iPhone.
2. Tap the Lauburu app → Install (or Update) → Open.
3. App opens to sign-in if no valid session; sign in with
   Aaron's account.
4. If a stale-token error occurs, Path A above is the same
   on TestFlight builds — the auto-recovery code ships in
   the bundle. No iOS-side reset needed.
5. **No "Continue as guest"** UI exists today; signed-in
   access is required for member-scoped screens.

### 2.4 Google / Apple Sign-In QA edges

- **Apple Sign-In**: iOS only. Native module shipped; tap
  the Apple button → consent → app receives the OIDC token
  → store flips to `member`.
- **Google Sign-In**: tap the Google button → expo-auth-
  session opens the OAuth web flow → app exchanges the id
  token via `signInWithGoogleIdToken`.
- **If either fails** with "Sign-In not available on this
  build", the native module isn't linked in the build. That
  is a build-config issue, not an auth issue; not addressed
  here.

## 3. What screens are reachable per auth state

| Auth state | Reachable screens | Notes |
|---|---|---|
| `loading` | none — splash / spinner | brief; if it sticks, see § 2.2 |
| `guest` | sign-in / sign-up forms; `requestPasswordReset` | no `(tabs)` access |
| `member` (any user) | full `(tabs)`: Home / Health / Train / Map / Reference / Settings | per-user data scoped via Supabase RLS |
| `member` + email allowlisted | adds `admin-dev` route + admin-gated UI sections (e.g. `HealthActionsPanel` source diagnostics) | matches `isAdminEmail` allowlist embedded in the app + (via FS-019) the Worker |
| `member` + `__DEV__` + `useDevUnlockStore.unlocked === true` | adds dev-only affordances (workflow-dispatch button, source diagnostics) | production / TestFlight bundles never reach this state because `__DEV__ === false` there |

## 4. Production auth safety

- **No hardcoded credentials.** No test passwords, no admin
  bypass, no service-role key in mobile code.
- **Stale-session recovery is auth-only.** Per-user caches are
  only cleared on explicit `signOut()`.
- **Admin gating unchanged.** The `isAdminEmail` allowlist
  + (post-FS-019) Worker-side JWT email check are the
  authoritative gates.
- **No public write controls.** Workflow-dispatch button is
  `__DEV__`-gated post-`32601e2`; production / TestFlight
  bundles do not render it.
- **Public users cannot gain admin access.** The admin gate
  is email-based; non-allowlisted emails see only the public
  / member screens.

## 5. What this change does NOT do

- Does NOT add a guest-mode for member-scoped screens.
- Does NOT bypass auth in production.
- Does NOT clear per-user cached data on stale-session
  recovery (only the Supabase session itself).
- Does NOT change the route-guard model — there is no
  explicit guard today; screens render with optional `user`
  and the auth store flips to `guest` when the session is
  invalid.

## 6. QA gate clearance

Running this QA flow on actual devices does NOT
automatically clear the installed-device QA gate. After the
audit, Aaron / Agent must run:

```bash
npm run bridge:agent-qa
# answer interactively or pass a JSON file
```

with `status: pass` (or `partial` / `fail` per real findings)
+ `platform: both` (or `android` / `ios`) + truthful results
per surface. The bridge:snapshot then propagates the verdict
to the canonical store.

## 7. Cross-references

- `apps/mobile/src/store/auth-store.ts` — the auth store with
  stale-session recovery.
- `apps/mobile/src/store/clear-user-data.ts` — per-user
  cache clear on explicit signOut.
- `apps/mobile/src/store/supabase.ts` — Supabase client
  (uses expo-secure-store via `secureStorage`).
- `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` (FS-019) —
  upcoming JWT-based admin auth that replaces the shared
  bearer token in `admin-dev.tsx`'s workflow-dispatch path.
- `scripts/bridge-agent-qa.mjs` — Agent QA verdict recorder.
- `data/agent-status/lanes/agent_qa_result.json` — current
  release-gate state.
