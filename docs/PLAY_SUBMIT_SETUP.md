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

Proof build still required: trigger one Android build + upload
from Admin/Dev (or via the workflow_dispatch UI) and confirm a
tester device receives the new versionCode without any Play Console
intervention. After that, the auto-promote path is verified.

Public production release (closed/open testing → production) is a
separate, larger pass — out of scope for this checklist.
