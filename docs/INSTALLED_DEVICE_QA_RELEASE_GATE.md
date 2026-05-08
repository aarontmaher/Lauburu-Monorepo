# Installed-device QA release gate

Status: active gate. This is QA-only, not public release approval.

## Current build QA state

- iOS: build 19 submitted to TestFlight Team (Expo), Apple
  processing. Current EAS build reference from handoff:
  `9b11aeb1`.
- Android: versionCode 18 build finished. Current EAS build reference
  from handoff: `36340071`.
- Android AAB local handoff path:
  `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab`.
- Android Play/Internal submit is blocked on Aaron/Google credential
  flow or manual Play Console upload.

The local AAB path is okay in admin/local docs. Do not expose artifact
URLs, Google credentials, or private upload details on public MCP
surfaces.

## Next human action — Android manual upload

1. Open Play Console.
2. Select Lauburu Grappling Map.
3. Go to Testing -> Internal testing.
4. Create a new release.
5. Upload:
   `~/Downloads/lauburu-android-versionCode18-commit0932c63.aab`
6. Complete the Play Console review screens for the internal release.
7. Start rollout to Internal Testing only.
8. Wait for Play processing.
9. Install/update from Play Internal on the Android device.
10. Run installed-device QA and record results with
    `npm run bridge:agent-qa`.

## Next human action — iPhone TestFlight

1. Wait for Apple processing to finish for build 19.
2. Open TestFlight on iPhone.
3. Install/update Lauburu Grappling Map build 19.
4. Run installed-device QA.
5. Record results with `npm run bridge:agent-qa`.

## Gate rule

Repo-only, simulator-only, or processing-only evidence does not clear
installed-device gates. A pass must include exact installed iOS build
number and/or Android versionCode tested on a real device.
