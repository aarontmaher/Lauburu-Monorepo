# Simulator QA Audit Harness

Purpose: give Aaron or Agent a repeatable local evidence path for simulator QA before installed-device TestFlight / Android Internal QA. Simulator QA is always partial; it does not clear installed-device release gates.

## iOS Simulator

1. Start Metro if it is not already running:

   ```bash
   cd apps/mobile && npx expo start --dev-client
   ```

2. Boot an iOS Simulator and run the app:

   ```bash
   cd apps/mobile && npx expo run:ios
   ```

3. From the repo root, run:

   ```bash
   npm run qa:simulator
   ```

The harness:

- runs strict route smoke checks;
- checks whether Metro is reachable;
- captures a booted iOS Simulator screenshot when available;
- writes local evidence under `tmp/qa-screenshots/YYYYMMDD-HHMM/`;
- writes `agent-qa-simulator.json`;
- writes an Agent handoff prompt;
- keeps release gates blocked because simulator QA is not installed-device QA.

To record the result into MCP/shared state:

```bash
npm run bridge:agent-qa -- tmp/qa-screenshots/<run>/agent-qa-simulator.json
npm run bridge:snapshot
```

## Android Emulator

Android automation is checklist-first for now because Health Connect behavior depends on emulator image support and native permissions.

1. Start an emulator from Android Studio Device Manager, or:

   ```bash
   emulator -list-avds
   emulator -avd <name>
   ```

2. Start Metro:

   ```bash
   cd apps/mobile && npx expo start --dev-client
   ```

3. Run the app:

   ```bash
   cd apps/mobile && npx expo run:android
   ```

4. Navigate:

- Home.
- Create account.
- Sign in.
- Health -> Manage health sources.
- Grappling Readiness.
- Admin/Control Centre only if Aaron is signed in as admin.

5. Capture screenshots:

   ```bash
   adb exec-out screencap -p > tmp/qa-screenshots/<run>/android-health.png
   ```

6. Add screenshot refs to the generated QA JSON and ingest:

   ```bash
   npm run bridge:agent-qa -- tmp/qa-screenshots/<run>/agent-qa-simulator.json
   npm run bridge:snapshot
   ```

Do not mark Android Health Connect as passed from emulator unless the emulator actually shows the native Health Connect permission and sync behavior.

## Agent Result Rules

- `status: partial` for simulator-only QA.
- `status: pass` only for a real installed-device gate on the matching build/platform.
- `releaseGate.newTestFlightAllowed` stays `false` for simulator QA.
- `releaseGate.newAndroidBuildAllowed` stays `false` for simulator QA.
- No private health/journal data, secrets, tokens, raw logs, or sensitive screenshots in MCP evidence.
