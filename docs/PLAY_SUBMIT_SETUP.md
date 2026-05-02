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
