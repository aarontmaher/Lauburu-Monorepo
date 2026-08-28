# Lauburu AI Backend — Deploy & QA

## Deployed backend

```
https://lauburu-ai-backend-production.up.railway.app
```

## Run automated tests

```bash
cd chat-app

# Contract tests (no server needed) — 136 tests
npm run test:contracts

# Round-trip against deployed backend — 38 tests
BACKEND_URL=https://lauburu-ai-backend-production.up.railway.app \
INTERNAL_API_TOKEN=<set-from-secret-manager> \
ATHLETE_MEMORY_API_TOKEN=<set-from-secret-manager> \
npm run test:roundtrip
```

## Mobile env (already configured)

`apps/mobile/.env.development`:
```
EXPO_PUBLIC_AI_BACKEND_URL=https://lauburu-ai-backend-production.up.railway.app/v1/internal
EXPO_PUBLIC_AI_PUBLIC_URL=https://lauburu-ai-backend-production.up.railway.app/api/athlete-memory
EXPO_PUBLIC_INTERNAL_API_TOKEN=<set-from-secret-manager>
EXPO_PUBLIC_ATHLETE_MEMORY_TOKEN=<set-from-secret-manager>
EXPO_PUBLIC_ATHLETE_ID=dev-athlete
```

## Build and run mobile

**Expo Go is NOT supported.** This app uses native modules (HealthKit, camera, secure storage) that require a dev client or EAS build.

```bash
cd apps/mobile

# iOS simulator (builds native dev client)
npx expo run:ios --device "iPhone 17 Pro"

# iOS physical device (requires Apple Developer team in Xcode)
npx expo run:ios --device

# Android preview APK (via EAS cloud build)
npx eas-cli build --profile preview --platform android

# Android dev APK (via EAS cloud build)
npx eas-cli build --profile development --platform android

# After installing dev client, start Metro:
npx expo start --dev-client
```

Do NOT use `npx expo start` without `--dev-client` — it launches Expo Go which will crash on native modules.

## Redeploy backend

```bash
cd /Users/aaronmaher/LauburuGrapplingMap-mobile
railway up --detach
# Wait ~90s, then verify:
curl -s https://lauburu-ai-backend-production.up.railway.app/api/athlete-memory/tour | head -20
```

---

## Manual QA checklist

### 1. App tour (11 steps)

**How**: Launch app fresh (or Settings > Help > Replay app tour).

| Step | Title | Pass if |
|------|-------|---------|
| 1/11 | Welcome to Lauburu | Card centered, "1 of 11" visible, Next/Skip visible |
| 2/11 | Home | Body mentions recovery snapshot, Next/Back work |
| 3/11 | AI Coach | Mentions floating button, no fake readiness claims |
| 4/11 | Health Sources | Says "Cronometer is not yet connected" |
| 5/11 | Nutrition | Says "Only confirmed entries count", mentions barcode + AI photo |
| 6/11 | Train | Mentions HIIT per-set tracking |
| 7/11 | HIIT Progress | Says "Machine data not yet connected" |
| 8/11 | 3D Map | Mentions side handle for filters |
| 9/11 | Belt Syllabus | Mentions progress updates |
| 10/11 | Reference | Mentions drilling/learned |
| 11/11 | Settings | "Got it" button (not "Next"), card dismisses on tap |

**Also check:**
- [ ] AI FAB is hidden while tour is visible
- [ ] Bottom tabs visible but not blocking controls
- [ ] Skip tour dismisses permanently (relaunch shows no tour)
- [ ] Settings > Help > Replay app tour shows tour again

### 2. Health sync

| Action | Pass if |
|--------|---------|
| Open Health tab | Tab loads without crash |
| Grant HealthKit permissions | Permission dialog appears (simulator: may auto-grant) |
| Wait for sync | Today card shows data or "no data yet" |
| Coach: "What data sources are connected?" | Mentions Apple Health |
| WHOOP card | Shows seed/stale status, NOT "live readiness" |

### 3. Manual nutrition

| Action | Pass if |
|--------|---------|
| NutritionCard > Manual > enter 500 cal, 30g protein | Fields accept input |
| Save | Totals update to show 500 kcal / 30g protein |
| Coach: "What did I eat today?" | Says "500 kcal" or "30g protein" |
| Coach: "Is my nutrition log complete?" | Says "partial" (missing carbs, fat) |

### 4. Barcode confirm

| Action | Pass if |
|--------|---------|
| NutritionCard > Barcode > "Scan with camera" | Camera opens (dev client only, not Expo Go) |
| Scan a product | Product name + macros appear |
| Adjust grams > Confirm | Totals update additively |
| Type barcode text > Look up > do NOT confirm | Totals do NOT change |

### 5. AI photo estimate

| Action | Pass if |
|--------|---------|
| NutritionCard > AI photo | Manual entry form appears (not fake AI output) |
| Enter 300 cal, 20g protein | Fields accept input |
| "Add as AI photo estimate" | Totals update, evidence created with confidence: low |

### 6. HIIT session

| Action | Pass if |
|--------|---------|
| Train > HIIT > set 30s work / 30s rest / 3 rounds | Protocol form works |
| Optionally name it "Friday bike" | Label saves to library |
| Log session | Success banner shows |
| Home tab | HIIT home note appears (if <3 days old) |
| Coach: "How did my HIIT compare to last time?" | Reports watts, sets, protocol |

### 7. Cronometer status

| Action | Pass if |
|--------|---------|
| Health tab > Nutrition Sources card | Shows "Not connected" for Cronometer |
| Manual/Barcode/AI photo rows | All show "Always available" |
| Coach: "Is Cronometer connected?" | Says "not connected", offers alternatives |

### 8. Readiness gating

| Action | Pass if |
|--------|---------|
| Coach: "Am I recovered enough to sprint?" | Says "cannot clear" or "insufficient data" |
| Coach: "Should I do HIIT today?" | Does NOT say "green light" without live WHOOP |
| WHOOP card shows stale/seed | No "Live readiness" label |

### 9. Backend sync verification

```bash
# After logging nutrition + HIIT on device, check deployed backend:
curl -s "https://lauburu-ai-backend-production.up.railway.app/api/athlete-memory/dev-athlete/ai-context" \
  -H "x-athlete-memory-token: <set-from-secret-manager>" \
  -H "x-athlete-id: dev-athlete" | python3 -m json.tool | head -30
```

| Field | Pass if |
|-------|---------|
| `nutritionDailySummary.sourceState` | `"manual"` or `"estimated"` |
| `nutritionDailySummary.sourceDependencies` | Array, not empty |
| `nutritionDailySummary.allConfirmed` | `true` |
| `recentHIITWorkouts` | Array with at least 1 entry (if HIIT was logged) |
| `multiSourceHealth.cronometer.status` | `"not_connected"` |
| `multiSourceHealth.cronometer.reason` | Present, not null |

---

## Backend env vars (Railway dashboard)

| Variable | Value |
|----------|-------|
| `INTERNAL_API_TOKEN` | Set in Railway secrets |
| `ATHLETE_MEMORY_API_TOKEN` | Set in Railway secrets |
| `PORT` | Set by Railway automatically |

## Token safety

- `.env.development` and `.env.production` must be local-only and must not contain committed real tokens.
- Set real values through local env files or a secret manager, not documentation.
- All mobile sync services bail early on empty token.

## Known external blockers

| Feature | Status | Blocker |
|---------|--------|---------|
| Cronometer live sync | `not_connected` | Cronometer does not offer a public third-party API |
| AI photo vision estimation | Scaffolded | No vision model endpoint — user enters macros manually |
| Concept2 machine sync | `not_connected` | Requires Concept2 SDK / ErgData API integration |
| Bluetooth FTMS | `scaffold_only` | Requires react-native BLE module + FTMS protocol |
| Direct WHOOP live readiness | Stale/seed | WHOOP MCP sync must run; GitHub Actions cron may be paused |
| WHOOP fresh recovery/HRV/strain | Via MCP bridge | Trigger: `POST /v1/internal/whoop/trigger-sync` or wait for cron |

None of these block manual QA. The app works in seed/manual mode for all checklist items.

---

## Physical iPhone build & install

### Prerequisites

1. **Apple Developer account** — payment complete / membership appears purchased; final Xcode team visibility still needs confirmation
2. **Xcode** — with your Apple ID signed in (Xcode > Settings > Accounts)
3. **iPhone connected via USB** or on same Wi-Fi network

### Confirm Apple Developer activation

Payment complete (14 April 2026). Before building for device, confirm the paid team is visible:

1. Open **Apple Developer app** on iPhone (or developer.apple.com) — sign in with same Apple ID
2. Confirm membership shows **Active** (not "Pending" or "Enrollment Processing")
3. Open **Xcode > Settings > Accounts** — sign in with same Apple ID
4. Under your Apple ID, confirm a **paid team** appears (your name or org, not just "Personal Team")
5. If team not visible: activation can take up to 48h after payment. Check back.

### First-time device build

```bash
cd apps/mobile

# 1. Set your development team in Xcode:
#    Open ios/LauburuGrapplingMap.xcworkspace
#    Select the LauburuGrapplingMap target
#    Signing & Capabilities > Team > select your paid Apple Developer team
#    Xcode auto-creates provisioning profile for com.lauburu.grapplingmap

# 2. Build and install on device:
npx expo run:ios --device
#    Select your iPhone from the device list

# 3. Trust the developer certificate on iPhone:
#    Settings > General > VPN & Device Management > Developer App > Trust
```

### Subsequent runs

```bash
# Rebuild (if native code changed):
npx expo run:ios --device

# Hot reload only (if only JS changed):
npx expo start
# Then shake device or press 'd' to open dev menu > Reload
```

### iOS project configuration

| Setting | Value |
|---------|-------|
| Bundle ID | `com.lauburu.grapplingmap` |
| Minimum iOS | 16.0 (Expo SDK 54 default) |
| Entitlements | HealthKit read/write + background delivery |
| Camera | Barcode scanning permission |
| Required capabilities | arm64, healthkit |
| Signing | Automatic (set team in Xcode) |

### Environment for device builds

The `.env.development` already points at the deployed Railway backend:
```
EXPO_PUBLIC_AI_BACKEND_URL=https://lauburu-ai-backend-production.up.railway.app/v1/internal
EXPO_PUBLIC_AI_PUBLIC_URL=https://lauburu-ai-backend-production.up.railway.app/api/athlete-memory
```
No localhost — works on physical device without changes.

### HealthKit on physical device

1. Build installs HealthKit entitlements automatically
2. First launch: app requests HealthKit permissions
3. Grant all requested categories (heart rate, HRV, sleep, steps, calories, workouts)
4. Health tab syncs data from iPhone Health database
5. Coach: "What data sources are connected?" → mentions Apple Health
6. **Truth boundary**: Apple Health data improves context but does NOT unlock WHOOP live readiness
