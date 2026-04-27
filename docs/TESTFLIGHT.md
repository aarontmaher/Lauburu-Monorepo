# iOS TestFlight — Friends Beta

Target: invite ~10 friends. Build with EAS, distribute through Apple TestFlight (external group). No Xcode Cloud.

## One-time Apple setup

All already approved / exists:

- Apple Developer membership: active
- Apple Team exists
- Bundle ID `com.lauburu.grapplingmap` registered
- App ID + HealthKit capability: enabled

Still required in **App Store Connect** (https://appstoreconnect.apple.com → Apps):

1. **Create the app record** if it does not exist:
   - Platform: iOS
   - Bundle ID: `com.lauburu.grapplingmap` (select existing)
   - SKU: `lauburu-grappling-map`
   - Primary language: English (US)
2. **TestFlight → Test Information:**
   - Beta App Description — one paragraph. Mention grappling + health tracking + AI coaching.
   - Feedback Email: `aaron.t.maher@gmail.com`
   - Marketing URL / Privacy Policy URL — privacy URL is required for external testing.
3. **TestFlight → What to Test** — updated per build:
   - "Health tab → Connect Apple Health (iOS sheet appears, grant any metrics). Then Sync Apple Health. Expect Connected / Connected — no recent data / Partial states on the Apple Health card."
   - "Health tab → Connect WHOOP (Safari OAuth, return to app). Sync WHOOP. Readiness unlocks when recovery + HRV + strain + sleep all present."
   - "Flag icon (bottom-left) → file a bug or suggestion with a screenshot. Settings → Tester tools → Recent feedback to review what's been sent."
4. **Export compliance:**
   - `ITSAppUsesNonExemptEncryption` = false is already in `app.json` → Apple will auto-mark as exempt, no manual form each build.
5. **HealthKit review note** (app review will ask):
   - "Lauburu reads sleep, heart rate, HRV, steps, energy, and workouts from Apple Health so the AI Coach can tailor recovery and training suggestions to the user's grappling sessions. Data stays in the user's account; no third-party sharing."
6. **External Testing group:**
   - Name: `Friends Beta`
   - Add up to 10 testers by email OR enable a **public link** (easier — send one URL).
   - External tests require **Beta App Review** for the first build. Review is usually a day.

## Build + submit (EAS)

From `apps/mobile/`:

```
# 1. Prerequisite — log in once.
npx eas-cli login

# 2. Ensure the iOS capability is set on App Store Connect side.
#    EAS will prompt for an Apple App-Specific Password or session.

# 3. Production iOS build (goes to TestFlight after submit).
npx eas-cli build --profile production --platform ios

# 4. Submit the resulting build to App Store Connect → TestFlight.
npx eas-cli submit --platform ios

# 5. In App Store Connect → TestFlight, assign the build to the
#    "Friends Beta" external group. Submit for Beta App Review (first
#    build only). Subsequent builds in the same major version can skip
#    review if they don't add new features/permissions.
```

## Build number policy

`apps/mobile/app.json` → `expo.ios.buildNumber`. Bump on every TestFlight build (Apple requires monotonic increase per `version`). Current: **7** (preview). Bump to **8** for the first production build targeted at TestFlight.

If you bump `expo.version` (marketing version), reset `buildNumber` to `1` for the first build of the new version.

## Internal vs External testers

- **Internal**: users in App Store Connect (paid role). No review. Up to 100.
- **External**: anyone with an email / public link. First build per version needs Beta App Review (~24h). Up to 10,000.

For Aaron's 10 friends: **external** group is the right pick.

## OTA updates (EAS Update)

For JS-only fixes between TestFlight builds:

```
# Publish an Update to the production channel — reaches TestFlight users.
npx eas-cli update --branch production --message "Describe the fix"
```

Don't OTA-update native config changes (new permissions, new native modules). Those require a fresh build + TestFlight submit.

## Preview profile (ad-hoc / internal)

`preview` profile in `eas.json` is for internal distribution (not TestFlight). Use it for Aaron's own device testing:

```
npx eas-cli build --profile preview --platform ios
```

## Troubleshooting

- **Apple Health permission row stays "not determined" after Connect**: open iOS Settings → Health → Data Access & Devices → Lauburu → "Turn On All" for desired metrics. Then return to the app and tap Refresh.
- **TestFlight build rejected for "missing usage description"**: check `app.json` → `expo.ios.infoPlist`. `NSHealthShareUsageDescription`, `NSHealthUpdateUsageDescription`, `NSCameraUsageDescription`, and `NSPhotoLibraryUsageDescription` are all set.
- **Tester can't install the build**: they must install the **TestFlight** app from the App Store first, then open the invite link or enter the redemption code.

## Known-good build state

- Bundle ID: `com.lauburu.grapplingmap`
- HealthKit entitlement: on
- HealthKit background delivery entitlement: on
- `UIRequiredDeviceCapabilities`: `["arm64", "healthkit"]`
- Camera + photo library usage strings: set
- `ITSAppUsesNonExemptEncryption`: false

## Do NOT

- Do not configure Xcode Cloud — we use EAS.
- Do not ship internal tokens / secrets in the mobile bundle (backend URL + anon Supabase key only).
- Do not disable HealthKit background delivery unless you drop that feature.
- Do not rebuild Android unless an Android-native config changed.
