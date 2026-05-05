# App developments — repo-backed backlog

Single source of truth for the **active** backlog Aaron carries
between the laptop terminal, ChatGPT chats, and Apple Notes. The
in-app Admin/Dev "Backlog" card mirrors this file. When the file
changes, the next paired build picks it up — no live-fetch required
yet (the long-term shape is a backend route that serves this).

Updated 2026-05-05.

## Current #1 priority

**Grappler Readiness Batch B — extend `NextDayCheckin` with
subjective sliders (soreness, mood, perceived fatigue) so the
grappling + subjective buckets in `computeGrapplerReadiness`
stop returning null.**

Auto-update lane CLOSED 2026-05-06:

- Run `25361589282`: SUCCESS end-to-end. EAS build ✓ → Submit AAB
  to Play Internal Testing ✓ at 2026-05-05 06:59:36 UTC. Play
  accepted the COMPLETED release.
- Tester Android device received v14 via Play Store auto-update.
  No Play Console click required.
- Future paired builds dispatch routinely from Admin/Dev: bump
  `app.json android.versionCode` + `ios.buildNumber` → tap Build
  Android + upload + Build iOS + submit. No manual steps.
- Workflow URL preserved:
  https://github.com/aarontmaher/lauburu-grappling-map/actions/runs/25361589282

Earlier failure preserved for context (run `25349253529`):

- EAS build: ✅ succeeded — AAB produced
  (`https://expo.dev/artifacts/eas/to6EtkZB68rBopsR9JNYMV.aab`,
  EAS build id `ddbc98cd-fa72-49c4-ad85-e0c8d929a957`).
- Play API auth: ✅ succeeded — service account
  `lauburu-play-release-461@lauburu-play-deploy.iam.gserviceaccount.com`
  authenticated, scheduled the submission, track `internal`,
  releaseStatus `COMPLETED`.
- Play submission: ❌ rejected by Google Play with: *"The app is
  missing the required metadata to submit the app to Google Play
  Store."* (EAS submission record:
  `https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map/submissions/df5d79df-b91e-4711-ae41-053102d46324`)

What this means: the listing-pass items Aaron uploaded
(graphics + screenshots) are present, but Play's COMPLETED-release
validator requires more saved fields than DRAFT mode does. The
common gaps that produce this exact error are:

- **Data safety** questionnaire started but not Saved → "Complete"
- **Content rating** IARC questionnaire started but not finalised
- **Target audience and content** unsaved
- **Health Connect declaration** missing or unsaved
- **App access** if Play needs review credentials (only required
  for production / open testing — but check this hasn't been
  flagged on Internal Testing too)

Parallel iOS Build 15 dispatch (run `25349256198`,
`submit_to_testflight=true`): **SUCCEEDED.** Build 15 is on App
Store Connect and assigned to the internal `Team (Expo)` group.
Aaron should accept the TestFlight prompt on his device — Build
15 carries the iOS HealthKit Mac/Vision warning fix, the Admin/Dev
redesign + Primary actions, and the owner-FAB rule (Feedback FAB
hidden for the admin email).

## Current blocker

Aaron-side: open Play Console → Lauburu Grappling Map →
**Dashboard** OR **Internal testing → v14 draft** and look for any
"Complete this section" / red / amber prompt. Save each
questionnaire to "Complete". Reply *"play listing fully complete"*
when done; I will re-dispatch the Android workflow once. **Do NOT
re-dispatch yet — it will fail the same way.**

## Next action

Aaron does Play Console pass → clicks `Review release → Start
rollout` once on v13 → replies "flip releaseStatus to completed" →
I edit `eas.json` (one line) and commit.

## Can delete from notepad

These items are spec'd or live and don't need to live in Apple Notes
anymore:

- "Wire iOS auto-group assignment" — DONE, Build 14 verified.
- "Add Privacy / Account-deletion pages to website" — DONE, both
  HTTP 200 at the live URLs.
- "Document AI provider strategy" — DONE,
  `docs/AI_PROVIDER_STRATEGY.md`.
- "Document AI monetisation / cost guardrails" — DONE,
  `docs/AI_MONETISATION_AND_USAGE_STRATEGY.md`.
- "Audit which wearable claims are actually live" — DONE,
  `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md`.
- "Fix iOS HealthKit Mac/Vision warning" — DONE, shipped on
  iOS Build 15 (run `25349256198`).
- "Generate Play app icon 512×512 and feature graphic 1024×500" —
  DONE, in `docs/store-assets/google-play/`.
- "Capture two phone screenshots for Play listing" — DONE
  (Aaron-side, 2026-05-05).
- "Upload Play Console icon / feature graphic / screenshots /
  default store listing" — DONE (Chrome confirmed).
- "Privacy policy URL declared" — DONE
  (`https://www.lauburugrapplingmap.com/privacy/`).
- "Advertising ID declaration" — DONE.
- "Flip `releaseStatus` to `completed`" — DONE (eas.json +
  workflow `release_status` override input).
- "Android auto-promote proof: workflow + Play API + tester
  device" — DONE 2026-05-06. Run `25361589282` + tester Android
  device confirmed v14 via Play Store auto-update.
- "Add /admin/status backend route + signed dispatch" — DONE.
- "Hide Dev/Admin FAB from normal testers" — DONE (admin-email gate).
- "Hide Feedback FAB from owner" — DONE (this batch).

## Do not delete yet

These remain in the backlog because they are NOT yet done:

- Grappler Readiness Batch B — extend NextDayCheckin sliders
  (soreness, mood, perceived fatigue).
- Grappler Readiness Batch C — extend TrainingSession schema
  with grappling-specific fields (gi/no-gi, drilling vs live
  minutes, perceived intensity).
- Grappler Readiness Batch D — bucket-ring UI on
  AthleteStateStrip showing all 5 buckets with provenance.
- AI provider implementation — gated by triggers in
  `AI_PROVIDER_STRATEGY.md` AND
  `AI_MONETISATION_AND_USAGE_STRATEGY.md`.
- Stage-5 local Mac/tmux bridge — eight hard rules required.
- Public production release — out of scope until production
  listing pass is done (separate from the now-complete
  Internal Testing pass).
- Grappler Readiness Batches B/C/D (extend `NextDayCheckin` sliders,
  extend `TrainingSession` with grappling-load fields, bucket-ring
  UI on `AthleteStateStrip`). The audit doc explicitly recommends
  shipping these BEFORE adding any new wearable integration.
- AI provider implementation — gated. See triggers in
  `docs/AI_PROVIDER_STRATEGY.md` AND
  `docs/AI_MONETISATION_AND_USAGE_STRATEGY.md`.
- Public production release for either platform — out of scope until
  tester channels are fully auto-promote AND a separate listing pass
  for production is done.

## Next top 5

In suggested order; each is "ready when" the prior item is unblocked.

1. **Play Console listing pass + flip** (Aaron-side, then one-line
   commit).
2. **Paired tester build** (Android v14 + iOS Build 15) bundling the
   standing repo-only UX work and the iOS Mac/Vision warning fix.
   Triggered from Admin/Dev once releaseStatus is flipped.
3. **Grappler Readiness Batch B**: extend `NextDayCheckin` with
   subjective sliders (soreness, mood, perceived fatigue). Pure
   schema + UI work; no backend.
4. **Grappler Readiness Batch C**: extend `TrainingSession` schema
   with grappling-specific fields (gi/no-gi, drilling vs live
   minutes, perceived intensity).
5. **Grappler Readiness Batch D**: bucket-ring UI on
   `AthleteStateStrip` showing all 5 buckets (autonomic, sleep,
   load, grappling, subjective) with provenance.

After these five, the AI provider implementation gate opens.

## Last CHATGPT_STATUS

Latest known status block from a Claude Code run; updated by the
agent at the end of each lane. Older blocks live in chat history.

```
CHATGPT_STATUS_START
Auto-update status: iOS end-to-end auto-ship live (Build 14 reached
TestFlight Team (Expo) testers via auto-group assignment, no ASC
clicks). Android upload-to-Play DRAFT live; per-release promote
click stays manual.
Android auto-promote: NOT live yet. Gated on Play Console one-time
listing pass + flipping eas.json releaseStatus from 'draft' to
'completed'.
iOS status: Auto-assign to Team (Expo) verified working on Build 14.
Build 15+ adds the iOS HealthKit Mac/Vision warning fix.
AI API implementation: NOT started. Gated on triggers in
AI_PROVIDER_STRATEGY.md AND AI_MONETISATION_AND_USAGE_STRATEGY.md.
AI monetisation strategy: design doc landed (commit dbb4a41).
Health device/app audit: design doc landed (commit dbb4a41).
Files changed (last lane): docs/AI_MONETISATION_AND_USAGE_STRATEGY.md,
docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md.
Verified: tsc --noEmit clean.
Next: Aaron's Play Console listing pass.
CHATGPT_STATUS_END
```

## Manual steps for Aaron

The only steps that genuinely need a human + browser. Everything
else is dispatchable from Admin/Dev.

1. **Play Console listing pass** (one-time, ~30–60 min). See
   `docs/PLAY_SUBMIT_SETUP.md` §6.
2. **Click `Review release → Start rollout`** once on the v13 draft
   to verify the listing pass took.
3. **Reply "flip releaseStatus to completed"** so I edit `eas.json`
   in a single commit.
4. **Tester device install** (your own devices): TestFlight + Play
   Store auto-update once notified — no action needed beyond
   accepting the update prompt.

Everything else (typecheck, release audit, backend smoke, Android
build, Android upload, iOS build, iOS submit, OTA diagnostic) is
dispatchable in-app via the Admin/Dev workflow buttons.

## What's NOT in this file

- Long-form architecture (lives in `docs/architecture/`).
- Specific code TODOs (tracked in code, not here).
- Per-batch task breakdowns (in conversation history; this file
  carries the cross-conversation backlog only).
- The grappling.opml content (untouched, off-limits).
