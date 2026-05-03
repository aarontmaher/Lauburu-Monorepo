# iOS TestFlight automation — setup checklist

Goal: have `ios-testflight-build.yml` run an EAS iOS build and submit
the resulting IPA to TestFlight, replacing the manual
`eas submit --platform ios` step.

This is **not enabled yet.** The workflow already builds — only the
submit step is gated on credentials.

## 1. Apple Developer Portal — capability check

Open https://developer.apple.com/account → **Certificates, IDs &
Profiles → Identifiers** → tap `com.lauburu.grapplingmap`. Confirm:

- ✅ **Sign In with Apple** is enabled (the app config requires it).
- ✅ **HealthKit** is enabled.
- ✅ Other capabilities listed in `apps/mobile/app.json` `ios.entitlements`.

If you change capabilities here, re-run `npx eas-cli credentials
--platform ios` interactively and choose **Set up new provisioning
profile** so the EAS-cached profile matches.

## 2. App Store Connect — internal testers

App Store Connect → **TestFlight → Internal Testing**. Add testers'
Apple IDs to a tester group. Once a build finishes processing, that
group receives a TestFlight push automatically.

## 3. Pick a submit credential path

EAS supports two paths for non-interactive `eas submit --platform ios`:

| Path | Pros | Cons |
|---|---|---|
| **App Store Connect API key** | One JSON key, no 2FA prompt, works fully headless. **Recommended.** | One-time setup in App Store Connect → Users and Access → Keys. |
| Apple ID + app-specific password | Simpler if no API access | Apple may still prompt 2FA on new device fingerprints |

### A. Recommended — API key (`AppStoreConnect_Api_Key.json`)

1. App Store Connect → **Users and Access → Integrations → Keys** → **Generate API Key**.
   - Access: **App Manager** (or Admin if you also want production
     submissions later).
   - Name: `lauburu-eas-submit`.
2. Download the `.p8` file (only available once). Note the **Key ID**
   and **Issuer ID** shown on the same page.
3. Cache the credentials on EAS:
   ```
   cd ~/LauburuGrapplingMap-mobile/apps/mobile
   npx eas-cli credentials --platform ios
   ```
   Pick **production** → **App Store Connect API Key** → **Add new**.
   Provide the `.p8` content + Key ID + Issuer ID. EAS stores them
   server-side; submit no longer needs them in env.
4. EAS will pick the key up automatically when running
   `eas submit --platform ios --profile production --latest`.
5. **GitHub Actions secrets needed (after the cache is set):**
   - `EXPO_TOKEN` (already set).
   - No Apple secret needed in GitHub — EAS holds the API key.

### B. Fallback — App-specific password

Only use this if you can't use API keys.

- App Store → Account settings → **App-Specific Passwords** → generate a
  new one named `lauburu-eas-submit`.
- Add it as a GitHub Actions secret: `EXPO_APPLE_APP_SPECIFIC_PASSWORD`.
- The workflow's `submit` step already reads it.

## 4. Trigger from the Admin/Dev app

Once credentials are cached on EAS:

- Admin/Dev → **Build iOS + submit to TestFlight** → confirm dispatch.
- Backend POSTs to GitHub Actions `ios-testflight-build.yml` with
  `inputs: { submit_to_testflight: 'true' }`.
- GitHub Actions runs the build on a `macos-14` runner, then
  `eas submit --platform ios --profile production --latest`.
- TestFlight receives the IPA, processes it (~10–30 min), and pushes
  the new build to internal testers.

## 5. Required GitHub Actions secrets summary

| Secret | Required for | Notes |
|---|---|---|
| `EXPO_TOKEN` | EAS auth (build + submit) | Always required |
| `EXPO_APPLE_APP_SPECIFIC_PASSWORD` | Path B only | Skip if using API key |

App Store Connect API key lives on EAS, not GitHub.

## 6. Rule-compliance reminders

- We never email or display the user's password.
- We never store Apple credentials in the mobile app.
- TestFlight is the auto-distribution path on iOS — no OTA needed.
- The mobile app only exposes "Build iOS TestFlight" and
  "Build iOS + submit to TestFlight" buttons, both gated on backend
  status reporting `iosBuildWorkflowAvailable: true`.

## 7. Current blocker (until resolved by you)

The current EAS provisioning profile (`Updated 14 days ago`) does NOT
include `com.apple.developer.applesignin`. Until that's regenerated,
every iOS production build fails at the fastlane Xcode step. Run:

```
cd ~/LauburuGrapplingMap-mobile/apps/mobile
npx eas-cli credentials --platform ios
```

→ **production** → **Provisioning Profile → Set up new provisioning
profile**. Apple ID + 2FA. Confirm the new "Updated" timestamp is
"minutes ago".
