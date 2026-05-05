# Mobile UX audit — next-up backlog

Captured 2026-05-04 from a Phase-6 audit pass. Items not patched in
this turn are listed below with priority + scope so future Code
sessions can pick them up safely without rediscovery.

---

## P1 — release truth-telling

Status: **partially patched this turn.**

Admin/Dev "Release automation" section now distinguishes:
- workflow-upload-automation works (DRAFT release / "Ready to Submit")
- per-release tester rollout is still manual (Play Console Review →
  Start rollout, ASC TestFlight → Add to internal testing group)

**Follow-up not done**: an in-app "Last release" card with the latest
EAS Build ID + tester-live state per platform, refreshing on demand.
Backend `/admin/status` doesn't yet read from EAS / App Store Connect
/ Play Developer API; that's its own batch.

## P1 — Android Internal Testing release-history UI clarification

Aaron's Play Console screenshot shows "11 (0.1.0) Available to
internal testers" on the main card but absent from Release History.
This is because Play's Release History only lists *promoted* releases;
draft releases (v12, v13 sitting in the inbox after workflow upload)
don't appear in History until promoted. v11 was the last manually
promoted one, hence the asymmetry.

**Action**: nothing repo-side. Manual one-time pass in Play Console:
open the v13 draft → Review release → Start rollout. After that it
appears in History and supersedes v11 for testers.

## P1 — iOS Build assigned to internal tester group per build

EAS submit's `--non-interactive` path uploads the IPA to App Store
Connect but does NOT auto-assign to an internal tester group. App
Store Connect surfaces the build as "Ready to Submit" which is a
misleading label for the internal-testing path — it's actually
"uploaded but not assigned to any group".

**Two future fixes**:

1. Add `--groups <group_name>` to the `eas submit` step in
   `.github/workflows/ios-testflight-build.yml`. Needs the exact
   internal tester group name from App Store Connect → TestFlight →
   Internal Testing → group title.

2. Or, accept that ASC requires per-build group assignment for
   internal builds, and document it as a one-click manual step in
   Admin/Dev. (Already described in the Admin/Dev confirm copy.)

## P2 — Health source UX patches that should ship in next paired build

Already shipped repo-side in earlier batches:
- `OtherSourcesDisclosure` rename + WhoopDirect/PolarDirect demoted
  into "More sources / Add another source".
- AppleHealthCard `Platform.OS === 'ios'`, SamsungHealthCard `===
  'android'`.
- Apple Sign-In capability + provisioning re-cached.

**Not yet shipped** (still in the backlog):
- A "Scan for health sources" entry-point on Health tab when nothing
  is connected. Today the user sees per-platform cards even before
  they grant any permission. Follow-up batch should replace the
  empty state with one prominent CTA that runs the platform's native
  permission prompt.
- Android: Health Connect deeplink to install if the app is missing
  on-device. `Linking.openURL('market://details?id=com.google.android.apps.healthdata')`
  one-line in `HealthActionsPanel`.

## P2 — Train tab session-type chips

Already shipped repo-side. Confirm in next paired build:
- Top-of-tab Grappling / HIIT / Steady state / Weights chip row
- Machine connect card only renders for HIIT / Steady state
- "Log a new session" button removed
- Weekly schedule summary card under TodayPlanCard

## P2 — Feedback form

Already shipped repo-side. Confirm in next paired build:
- Severity of bug + What happened, or what should change? + Upload
  screenshot + Send feedback only
- "You are testing as", Type pills, "For testers — tips" disclosure
  removed

## P3 — AI Coach answer card readability

Already shipped repo-side. Confirm in next paired build:
- Right-aligned question bubble, "AI Coach" tag headline
- Short + nextStep visible by default; why-bullets / missingness /
  Share full context behind `▸ View details`
- ≤2 follow-up chips
- `Keyboard.dismiss()` after send
- Composer maxHeight 160

## P3 — empty-state copy that doesn't lie

Audit pending: anywhere the UI says "Apple Health" or "WHOOP"
without checking the user actually has it. Quick wins likely in:
- Coach answer footer when source is missing
- AthleteStateStrip Band labels when score is null
- Weekly schedule card when 0 sessions planned

## P3 — Admin/Dev "open external" links

Already in `admin-dev.tsx` — Expo project, Railway dashboard,
Play Console, App Store Connect, GitHub repo, GitHub Actions.

**Follow-up**: add direct deep-link to the latest EAS Build's logs
(URL pattern `https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map/builds/<build-id>`)
once `/admin/status` exposes the most-recent build IDs.

## P4 — Apple Sign-In re-enable check

Capability now ticked on App ID + provisioning regenerated
(`8AM6L4R4Y7`, Updated 4 hours ago in build 25291380582 log). EAS
production builds now include `com.apple.developer.applesignin`. Not
verified live in TestFlight yet (Build 13 sits at "Ready to Submit"
until manual group assignment).

**Follow-up after Aaron clicks "Add to group"**: verify the Sign in
with Apple button appears in Settings → AuthForm on iOS Build 13.
The probe is `appleSignInAvailable()` in
`src/services/social-auth.ts`.

## P4 — Bottom tab order verification

Repo-side: Home → Health → Train → Check-in → Map → Settings
(`apps/mobile/app/(tabs)/_layout.tsx`). Should match Aaron's reality
on TestFlight Build 13 once tester-live.

---

---

## Standing Notes-derived UX rules (2026-05-05)

Aggregated from Aaron's running notes; record them once here so
future batches can reference the doc instead of rediscovering.
Already on `main` where marked DONE; awaits next paired build.

| Rule | State |
|---|---|
| Remove prominent "signed in as @mail" from Home | check on next paired build |
| Remove "provisional confidence high" from Home | DONE — `AthleteStateStrip` drops the line when `level === 'high'` |
| Remove "based on Apple Health/imported history" provenance from prominent Home UI | DONE — same component |
| Signed-out Home shows Sign in / Create account CTAs | DONE — `GuestBanner` |
| Feedback only needs severity + description + screenshot | DONE — `FeedbackFab` simplified |
| Tab order: Home → Health → Train → Check-in → Map → Settings | DONE — `(tabs)/_layout.tsx` |
| Weekly schedule visible in Train tab | DONE — `WeeklyScheduleSummary` |
| Machine connect only after HIIT/Steady State picked | DONE — `<TrainMachineSection />` gated on `pendingMode in ('hiit', 'zone2')` |
| AppleHealthCard iOS-only / SamsungHealthCard Android-only | DONE — Platform.OS gates |
| WHOOP/Polar tucked under "More sources" disclosure unless connected | DONE — `OtherSourcesDisclosure` |
| Owner sees Dev/Admin FAB instead of Feedback FAB | DONE — `FabsGate` ownerSurface |
| Normal tester sees Feedback FAB; signed-out sees Feedback only | DONE — same gate |
| Forgot password sends reset email; passwords never exposed in UI | DONE — `auth-store.ts` `requestPasswordReset` uses `supabase.auth.resetPasswordForEmail` |
| Sign in with Google + Sign in with Apple available | iOS Apple Sign-In wired; Google Sign-In not yet implemented (deferred) |
| "Log a new session" button removed from Train tab if redundant | DONE — Train tab session-type chip row replaces button |

All "DONE" rows are repo-only until next paired build (Android v14
+ iOS Build 15) ships. No tester-visible regressions in this batch.

---

## What's deliberately deferred (not P-numbered)

- Grappler Readiness Batches B/C/D: extending NextDayCheckin sliders,
  TrainingSession grappling-load fields, bucket-ring UI on
  AthleteStateStrip. Each is its own batch with a clear scope.
- Shopify payments scaffold: `docs/SHOPIFY_APP_PAYMENTS_PLAN.md`.
- Cross-user / aggregate trends: privacy gating not yet in place;
  anything in this area is currently honest "off" copy.
- Whoop-mcp retirement: pending verification of whoop_direct OAuth
  on a clean tester account.
