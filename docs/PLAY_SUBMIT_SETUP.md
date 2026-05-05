# Google Play auto-upload — setup checklist

Goal: have `android-aab-build.yml` upload the resulting AAB straight to
the Internal Testing track without anyone touching Play Console.

This is **not enabled yet.** Workflow already builds the AAB; the
upload step is documented here so we can wire it cleanly in a single
follow-up batch.

## 1. Create a Play Developer service account

1. Play Console → **Setup → API access** → **Create new service
   account** (opens Google Cloud Console).
2. In Google Cloud, create a service account, e.g.
   `play-internal-uploader@<project>.iam.gserviceaccount.com`.
3. Skip role assignments inside Google Cloud — Play handles them.
4. Add a **JSON key** for the service account; download it.
5. Back in Play Console → **API access** → **Grant access** for that
   service account, then on the **Permissions** tab give it:
   - **Releases — Manage testing track releases (Internal testing)** ✓
   - **App access — View app information** ✓
   - leave production / closed-testing **off** for safety.

## 2. Store the key as a GitHub Actions secret

GitHub repo → Settings → Secrets and variables → Actions → New repo
secret:

- Name: `PLAY_SA_JSON`
- Value: paste the entire JSON file contents (single secret).

Optional shortcut: if you'd rather keep the key shorter, base64-encode
it and store as `PLAY_SA_JSON_B64`; the workflow can decode at runtime.

## 3. Add a workflow upload step

In `.github/workflows/android-aab-build.yml`, after the EAS build step,
add (only when `submitToPlay == 'true'` and the secret is present):

```yaml
- name: Upload AAB to Play Internal Testing
  if: ${{ inputs.submitToPlay == 'true' && env.PLAY_SA_JSON != '' }}
  env:
    PLAY_SA_JSON: ${{ secrets.PLAY_SA_JSON }}
  run: |
    set -euo pipefail
    artifact_url=$(npx eas-cli build:list --platform android --limit 1 --json | jq -r '.[0].artifacts.applicationArchiveUrl // empty')
    test -n "$artifact_url" || { echo "::error::No artifact URL"; exit 1; }
    curl -sSL -o app.aab "$artifact_url"
    echo "$PLAY_SA_JSON" > sa.json
    npx --yes @expo/eas-cli@latest submit --platform android \
      --path app.aab \
      --non-interactive \
      --profile production
    rm -f sa.json
```

Add an input on the workflow:

```yaml
submitToPlay:
  description: 'true → upload AAB to Play Internal Testing after build'
  required: false
  default: 'false'
```

## 4. Required GitHub Actions secrets summary

| Secret | Purpose |
|---|---|
| `EXPO_TOKEN` | EAS auth for build / submit |
| `RAILWAY_TOKEN` | Backend deploy workflow |
| `INTERNAL_API_TOKEN` | Backend smoke workflow |
| `PLAY_SA_JSON` | Play Developer service account JSON |
| `EXPO_APPLE_APP_SPECIFIC_PASSWORD` | iOS submit (TestFlight) |

Mobile app holds **none** of these. They live only in GitHub Actions
secrets and Railway.

## 5. End-to-end flow once wired

Mobile Admin/Dev → tap "Build Android AAB" → backend
`POST /api/athlete-memory/admin/workflows/android-aab-build/dispatch`
→ GitHub Actions runs `android-aab-build.yml` → EAS builds AAB →
`eas submit` uploads to Play Internal Testing → testers receive the
update through Play Store within ~15–60 min.

No manual Play Console upload, no terminal, no Mac required.

## 6. Play Console one-time listing pass — DONE

Listing pass completed and `eas.json
submit.production.android.releaseStatus` is now `"completed"`.
Future workflow dispatches with `submit_to_play=true` create
COMPLETED Internal Testing releases — no Play Console click
required for tester roll-out per release. The listing items below
are kept for reference only.

If a future release ever needs to land as a draft (e.g. listing
re-review required after a metadata change), use the
`release_status` workflow input and pass `draft`. The override is
clamped to `internal` track only by the workflow `type: choice`
enum.

Open Play Console → Lauburu Grappling Map. Each item below is a
sidebar entry on the left; address them in this order so dependencies
resolve first.

### Required entries

1. **App content → Privacy policy**
   URL: `https://www.lauburugrapplingmap.com/privacy/`
2. **App content → Account deletion / Data safety → Account deletion**
   URL: `https://www.lauburugrapplingmap.com/account-deletion/`
   (Already verified live HTTP 200.)
3. **App content → Data safety**
   - Tap **Manage** → fill the questionnaire honestly.
   - Health Connect declaration: state purpose per data type (heart
     rate, HRV, resting HR, sleep, steps, exercise, active calories,
     historical data) — one-line each, focused on personal recovery /
     readiness / training-load context.
   - Mark "data is encrypted in transit" YES (HTTPS/TLS).
   - "Users can request data deletion" YES → link the deletion page
     above.
   - "Selling data" NO. "Sharing for advertising" NO.
4. **App content → Content rating**
   - Run the IARC questionnaire. App is utility/health-fitness —
     answer truthfully (no violence, no user-generated chat that's
     visible to others, no gambling, no tracking-targeted ads).
5. **App content → Target audience and content**
   - Target age: 13+ (the app is not designed for children under 13).
   - Mark "designed for families" NO.
6. **Store listing → Main store listing**
   - App name: `Lauburu Grappling Map`
   - Short description (≤80 chars): something like
     `Grappling map, training, AI Coach, Apple Health & WHOOP sync.`
   - Full description (≤4000 chars): describe the product (3D
     mind-map, training tracking, AI Coach, multi-source health
     integration). Don't claim medical or readiness certification.
   - **Graphics — already prepared in `docs/store-assets/google-play/`:**
     - App icon 512×512 → `docs/store-assets/google-play/app-icon-512.png`
     - Feature graphic 1024×500 → `docs/store-assets/google-play/feature-graphic-1024x500.png`
     - Phone screenshots: at least 2 portrait 9:16 (≥1080 long edge).
       NOT yet generated — capture from iOS Simulator or Android
       device per `docs/store-assets/google-play/README.md` step 4
       and save them next to the icon/graphic above before
       uploading.
7. **Store listing → App category**
   - Category: **Health & Fitness**
   - Tags: pick `Fitness`, `Workout`, `Personal training`.
   - Email: `support@lauburugrapplingmap.com`
8. **Health Connect declaration** (separate from Data safety)
   - Play Console → App content → Health Connect → fill purpose
     justification. Reuse copy in `docs/PLAY_SUBMIT_SETUP.md`.
9. **App access** (only required for public production track — skip
   for Internal Testing).
10. **News apps / Government apps**: NO.

### After all the above are saved — DONE on 2026-05-05

`eas.json` now reads:

```jsonc
"android": {
  "serviceAccountKeyPath": "./google-services-key.json",
  "track": "internal",
  "releaseStatus": "completed"
}
```

Future dispatches of `android-aab-build` with `submit_to_play=true`
create a COMPLETED Internal Testing release directly — no Play
Console click required.

Proof build dispatched 2026-05-04: workflow `android-aab-build`
run `25349253529`, ref `main`, `submit_to_play=true`. URL:
https://github.com/aarontmaher/lauburu-grappling-map/actions/runs/25349253529.

**Result: FAILED at submit step.**

- EAS build: succeeded — AAB
  `https://expo.dev/artifacts/eas/to6EtkZB68rBopsR9JNYMV.aab`,
  build id `ddbc98cd-fa72-49c4-ad85-e0c8d929a957`.
- Play API auth: succeeded — service account
  `lauburu-play-release-461@…iam.gserviceaccount.com`
  authenticated; submission scheduled with track `internal`,
  releaseStatus `COMPLETED`.
- Play API rejection: *"The app is missing the required metadata
  to submit the app to Google Play Store."* EAS submission record:
  `https://expo.dev/accounts/aaronmaher/projects/lauburu-grappling-map/submissions/df5d79df-b91e-4711-ae41-053102d46324`.

Diagnosis: Play's COMPLETED-release validator is strictly stricter
than its DRAFT acceptance. The graphics + screenshots Aaron
uploaded ARE accepted; what's still missing is one or more of the
SAVED questionnaires. Each questionnaire has its own "Save" button;
starting one without saving leaves the section in a state that
DRAFT will accept but COMPLETED will not.

Verify each of these in Play Console → Lauburu → App content (left
sidebar):

- **Privacy policy** — URL field saved.
- **App access** — saved (mark "All functionality is available
  without restrictions" if no login is required to review the
  internal-testing build).
- **Ads** — saved.
- **Content rating** — IARC questionnaire submitted (will issue a
  rating certificate within a few minutes).
- **Target audience and content** — saved (13+, not designed for
  families).
- **News apps** — declared NO.
- **Data safety** — questionnaire submitted (Submit button at the
  bottom; merely Saving the form is not the same as Submitting).
- **Health apps declaration** / **Health Connect declaration** —
  per-data-type purpose justifications saved.
- **Government apps** — declared NO if applicable.
- **Financial features** — declared NO.

When all show green/saved/complete, the next workflow dispatch with
`submit_to_play=true` and `release_status=''` (default) should land
the v14 release as COMPLETED on Internal Testing. **Do NOT
re-dispatch until every left-sidebar item shows complete.** A
re-dispatch with the same metadata gap will fail identically and
cost an EAS build credit.

Optional fast-path while diagnosing: dispatch with
`release_status=draft`. This bypasses the COMPLETED validator and
proves the rest of the upload pipeline works (which we already
know from this run — auth + submission scheduling worked, only
the COMPLETED validator rejected). Don't bother — the diagnostic
value is zero.

## 7. Current corrected state — Play metadata blocker

Updated 2026-05-05. State as Chrome works through Play Console.

What is DONE (confirmed):

- iOS TestFlight channel works. Build 14 reached TestFlight; Build
  15 submission succeeded via run `25349256198`.
- Android Internal Testing track has v11 live to internal testers
  (last manual upload).
- Play Console listing graphics done: app icon 512×512, feature
  graphic 1024×500, phone screenshots, default store listing
  saved.
- Privacy policy URL declared:
  `https://www.lauburugrapplingmap.com/privacy/`.
- Account deletion URL declared:
  `https://www.lauburugrapplingmap.com/account-deletion/`.
- Advertising ID declaration submitted.
- `apps/mobile/eas.json submit.production.android.releaseStatus`
  is `'completed'`.
- `android-aab-build.yml` accepts a `release_status` choice
  override, clamped to `''` / `completed` / `draft`.

What is NOT done — the actual current blocker:

- Play Console rejected the v14 auto-promote attempt (run
  `25349253529`) with: *"The app is missing the required metadata
  to submit the app to Google Play Store."*
- Cause: Play's COMPLETED-release validator is stricter than its
  DRAFT acceptance. Listing graphics + Privacy URL + Advertising
  ID alone are NOT enough — every left-sidebar **App content**
  questionnaire must also be **Submitted/Complete**, not just
  Saved.
- Chrome is currently handling that manual completion path.

What Aaron must NOT do until Chrome reports back:

- Do NOT re-dispatch the Android `submit_to_play=true` workflow.
  Same metadata gap = same failure = wasted EAS build credit.
- Do NOT switch `releaseStatus` back to `'draft'`. The flip is the
  intended end state; it does not need to be reverted while
  Chrome works the metadata.
- Do NOT trigger a Production track release. Production stays
  untouched.

What Aaron CAN do while Chrome works:

- Accept the TestFlight prompt for Build 15 once Apple finishes
  processing it.
- Open the existing v13/v14 draft in Play Console → Internal
  testing if Chrome wants to inspect the Play API rejection inline.

## 8. Closed testing release unblocker

If Play Console asks Aaron / Chrome to **Create closed testing
release** (the screen requires an "App bundles" upload), follow
this rule set. Closed testing is a separate track from Internal
Testing — it is **not** Production.

**Hard rules:**

- Closed testing is allowed; Production is not. Confirm the track
  name in the URL bar / sidebar before uploading anything.
- Use a valid current AAB from EAS/GitHub output. Today the latest
  valid Android AAB is the one produced by GitHub Actions run
  `25349253529` (build id
  `ddbc98cd-fa72-49c4-ad85-e0c8d929a957`, artifact at
  `https://expo.dev/artifacts/eas/to6EtkZB68rBopsR9JNYMV.aab`,
  version `0.1.0` versionCode `14`). The build itself is fine —
  Play rejected the surrounding listing metadata, not the bundle.
- Do NOT upload an empty draft AAB. Closed testing must contain a
  real, signed AAB.
- Do NOT upload an old APK. The track only accepts AAB on this
  app, and an old APK would also drag the version backwards.
- Do NOT upload an unrelated AAB. Bundle id must match
  `com.lauburu.grapplingmap`.

**Path:**

1. Open the v14 AAB URL above (or download the latest from EAS
   builds → Android → production).
2. Play Console → Lauburu → Testing → **Closed testing** → Create
   new release → upload the AAB → fill the closed-testing tester
   list (can reuse the internal-testing list) → Save → Review
   release → Send for review.
3. While Play reviews the closed-testing release, complete every
   "App content" left-sidebar item to Complete (not Saved):
   Privacy policy, App access, Ads, Content rating IARC, Target
   audience, News apps, Data safety (SUBMIT button), Health apps
   declaration / Health Connect declaration, Government apps,
   Financial features. Each questionnaire has its own commit
   step.
4. When every left-sidebar item shows Complete, reply
   *"play listing fully complete"*.
5. Only after that reply, re-dispatch the Android workflow ONCE
   with `submit_to_play=true` and `release_status=''` (default).
   Tester device should receive v14 (or the next versionCode if
   v14 has already been claimed by closed testing) within 15–60
   min, no Play Console click.

**If Chrome cannot access the AAB file directly:** Aaron may need
to download it manually from the EAS artifact URL above and
re-upload via Play Console. The link is public-readable for the
EAS organisation; no secret is exposed in the URL.

Public production release (closed/open testing → production) is a
separate, larger pass — out of scope for this checklist.
