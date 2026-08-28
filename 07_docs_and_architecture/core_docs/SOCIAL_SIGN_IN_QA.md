# Social Sign-In QA

Scope: mobile Settings auth form only. No release, upload, or installed-device claim is implied by this checklist.

## Required Configuration

- Supabase Auth providers enabled for Apple and Google.
- Apple Sign-In capability enabled for the iOS app identifier.
- `EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID` set for iOS Google OAuth.
- `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` set for Android Google OAuth.
- `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` set when using Expo AuthSession web fallback.
- No client secrets in the mobile app; use public OAuth client IDs only.

## Local Checks

1. Run `cd apps/mobile && npm run typecheck`.
2. Run `cd cloudflare-worker && npx tsx test/test-social-sign-in-contract.ts`.
3. In an iOS dev build with Apple Sign-In linked, open Settings and confirm the native Apple button appears.
4. In iOS and Android dev builds with Google client IDs configured, tap Continue with Google and confirm the existing Supabase session state becomes signed in.
5. Remove Google client IDs locally and confirm the Google button shows a not-configured state instead of attempting auth.
6. Cancel Apple/Google provider sheets and confirm the app stays on the auth form without a false success message.
