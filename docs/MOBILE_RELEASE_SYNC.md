# Mobile release sync — what's auto vs manual today

Single source of truth for the tester release pipeline. Updated
2026-05-05.

State as of 2026-05-05:

- **iOS Build 14** is live in TestFlight via auto-group assignment
  (`groups: ["Team (Expo)"]` in `eas.json`). iOS auto-ship works
  end-to-end.
- **iOS HealthKit Mac/Vision warning fix** is on `main` (commit
  `a438070`, `UIRequiredDeviceCapabilities: ["arm64"]`). Repo-only
  until Build 15 ships.
- **iOS Build 15**: ✅ SUCCEEDED (workflow run
  `25349256198`). Build is on App Store Connect, auto-assigned to
  Team (Expo) internal group. Aaron just needs to accept the
  TestFlight update prompt on his device. Build 15 carries: iOS
  HealthKit Mac/Vision warning fix, Admin/Dev redesign + Primary
  actions, owner-FAB rule (Feedback FAB hidden for admin email).
- **Android v14** received on tester device 2026-05-06 via Play
  Store auto-update with no Play Console click. Run
  `25361589282` succeeded end-to-end (EAS build → Play submit)
  at 06:59:36 UTC after Chrome closed the Play Console
  app-content gap. Note: Play Console "Release history" UI is
  paginated and sometimes filters out releases promoted via the
  EAS-COMPLETED path versus the manual "Review release → Start
  rollout" flow — earlier screenshots showing only v11/10/8/7/5
  on page 1 reflect that pagination, not a missing v14. Ground
  truth is the tester device receiving v14, which is confirmed.
- **Android v15** dispatched 2026-05-05T15:12:56Z (run
  `25384901407`, `submit_to_play=true`) bundling the un-gated
  AppleHealthCard / Health Connect primary cards. EAS build was
  `in_progress` at last check; expected on tester devices within
  ~25 min build + 15–60 min Play rollout.
- **`eas.json` `releaseStatus`**: `'completed'`. The workflow
  `release_status` override (`completed` / `draft`) is available
  for emergency use only.
- **Auto-update path**: PROVEN end-to-end (workflow + Play API +
  tester device). Future paired builds dispatch routinely:
  bump versionCode + buildNumber → Build Android + upload + Build
  iOS + submit from Admin/Dev → testers update automatically.

## EAS build cost control rule (PINNED)

Tester / Internal Testing builds described in this doc cost EAS
build credits. Do NOT run, trigger, recommend, or prepare a new
EAS build (Android `android-aab-build.yml` or iOS
`ios-testflight-build.yml`) unless ALL FIVE hold:

1. Agent has completed a human-style app audit or targeted
   verification.
2. Agent explicitly confirms the change is worthwhile to test
   on-device.
3. The change is bundled with other meaningful mobile changes
   where possible.
4. Typecheck/tests pass first.
5. Aaron explicitly approves the build.

Default: no EAS build, no tester build, no "quick build to
check", no build for docs/backend/MCP-only changes, and no
build for tiny copy/UI tweaks unless bundled.

Use instead: mobile typecheck, unit tests, local inspection,
simulator/dev-client if already available, Admin/Dev MCP
status, and Agent audit confirmation.

Every Claude / Codex / Agent prompt that mentions build or
tester-build work must include: "Do not run EAS builds unless
Agent has confirmed a worthwhile on-device change and Aaron
approves."

Full body: `docs/ADMIN_RELEASE_AUTOMATION_PLAN.md` § Safety
gates and `docs/BACKLOG_AUTOMATION_SYSTEM.md` § EAS build
cost control rule.

## TL;DR

Tester channels work. Full auto-ship is partial.

| Step | Android (Internal Testing) | iOS (TestFlight) |
|---|---|---|
| Build (EAS) | ✅ workflow `android-aab-build.yml` | ✅ workflow `ios-testflight-build.yml` |
| Upload to store | ✅ `eas submit` (PLAY_SA_JSON) | ✅ `eas submit` (App Store Connect API key cached on EAS) |
| Tester group assignment | n/a — Internal Testing track | ✅ `eas.json submit.production.ios.groups: ["Team (Expo)"]` |
| Promote / make tester-live | ✅ automatic — verified end-to-end 2026-05-06 (run 25361589282 + tester device received v14 via Play Store auto-update with no Play Console click) | ✅ automatic — Build 14 then Build 15 reached Testing without ASC clicks |
| Tester device update | ✅ Play Store auto-update once promoted | ✅ TestFlight auto-update once Apple processing finishes |

## What "tester update channels work" means

- Android: a tester whose Google account is on the Internal Testing
  list, has accepted the opt-in URL, and has Play Store auto-update
  enabled, will receive new versions automatically once Aaron clicks
  **Review release → Start rollout** in Play Console.
- iOS: a tester in the **Team (Expo)** internal group (managed in
  App Store Connect → TestFlight → Internal Testing) will receive
  new builds automatically through the TestFlight app once Apple
  finishes processing each build (5–30 min after upload).

## What "full auto-ship" still needs (Android only)

The Play Console **per-release Review → Start rollout** click stays
manual until the app's store listing has every required Data Safety
field filled. Once those are done once, switch
`apps/mobile/eas.json` `submit.production.android.releaseStatus` from
`'draft'` to `'completed'` and the workflow will promote new releases
automatically.

Required listing fields (Aaron's one-time pass in Play Console →
Lauburu → Internal testing → open the v13 (or v14) draft → fill any
"Complete this section" prompt):

- Privacy policy URL → `https://www.lauburugrapplingmap.com/privacy/`
- Account deletion URL → `https://www.lauburugrapplingmap.com/account-deletion/`
- Content rating questionnaire (~5 min)
- Target audience and content
- Store listing (description, screenshots, feature graphic, app
  category)
- Health Connect declaration (purpose per data type) — already
  drafted in `docs/PLAY_SUBMIT_SETUP.md`
- App access (test credentials Apple/Google can use to review the
  app — only relevant when going public, NOT for Internal Testing)

After all the above are saved AND a `Review release → Start rollout`
has been clicked successfully on at least one release, flip
`releaseStatus` in `eas.json` to `'completed'`. Future
`Build Android + upload to Internal Testing` dispatches from the
Admin/Dev screen will then promote new versions automatically.

## What's already auto on iOS

iOS auto-ship is end-to-end automated as of Build 14:

```jsonc
// apps/mobile/eas.json
"submit": {
  "production": {
    "ios": {
      "appleTeamId": "DLVKNS75NJ",
      "ascAppId": "6762436447",
      "groups": ["Team (Expo)"]
    }
  }
}
```

EAS submit picks up the API key cached on EAS (Key ID `Z25FP6W2L6`,
"[Expo] EAS Submit MzKlqvB7E5"), uploads the IPA to App Store
Connect via that key, and assigns the build to **Team (Expo)** at
submit time. Apple processes the build and notifies the group's
testers; TestFlight installs the update on each device on next
launch.

If we add another internal group later (e.g. external testers, or a
"Real Testers" group separate from `Team (Expo)`), append to the
`groups` array — no code changes elsewhere.

## Daily release flow from this point

### Android tester release
1. Bump `apps/mobile/app.json android.versionCode` (e.g. 13 → 14).
2. Open Admin/Dev → tap **Build Android + upload to Internal Testing**.
3. Wait ~25 min. Workflow uploads AAB v14 to Play as a draft.
4. Open Play Console → Internal testing → open v14 draft →
   **Review release → Start rollout**. (One click, until the listing
   pass + `releaseStatus: 'completed'` switch is done.)
5. Testers update via Play Store within 15–60 min.

### iOS tester release
1. Bump `apps/mobile/app.json ios.buildNumber` (e.g. 14 → 15).
2. Open Admin/Dev → tap **Build iOS + submit to TestFlight**.
3. Wait ~25 min. Workflow builds, submits, and assigns to
   Team (Expo).
4. Apple processes the build (5–30 min). TestFlight notifies testers
   automatically.

### Paired bundle (most updates)
Bump both versionCode and buildNumber together; dispatch both
buttons in Admin/Dev. Tester apps converge on the same feature set
on both platforms within ~1 hour.

## Standing blockers

- **OTA**: still SDK-54-blocked at the EAS Update server. Don't
  rely on it. Native store updates (above) are the supported path.
- **Public production release**: out of scope until tester channels
  are stable AND the listing pass is fully done AND we have a
  privacy policy review. Keep both `track: 'internal'` and
  `releaseStatus: 'draft'` until then.

## What's `null` on backend `/admin/status` and why

Backend `/admin/status` returns:
- `playUploadConfigured: null`
- `testflightSubmitConfigured: null`

These are unknown to the backend because the actual secrets
(`PLAY_SA_JSON`, App Store Connect API key) live on GitHub Actions
and EAS server respectively — never on Railway. Both are present in
practice (verified by the green workflow runs). The Admin/Dev UI
treats `null` as "unverified — assume yes if the relevant secret is
set" rather than displaying false.

Two booleans the backend DOES return as authoritative `true`:
- `testflightGroupAssignmentConfigured: true` — read from the
  `eas.json` `submit.production.ios.groups` field at deploy time.
- `androidPlayPromoteAutomatic: false` — reflects today's
  `releaseStatus: 'draft'` setting. Will flip to `true` when Aaron
  switches it to `'completed'`.
