# How to work in this repo safely

Practical guide for the Lauburu mobile app. Based on the actual codebase as of April 2026.

The mobile app is an Expo Router app backed by Zustand stores, a thin service layer, and a shared domain package at `packages/shared`. The two files most likely to cause regressions are:

- `apps/mobile/app/(tabs)/index.tsx` (~1850 lines — Home)
- `apps/mobile/app/(tabs)/reference.tsx` (~2200+ lines — Reference)

If you are changing mobile features, the main job is to keep product logic out of those files unless the change is truly screen-local.

---

## 1. Repo mental model

```
lauburu-grappling-map-mobile/        # npm workspaces root
├── apps/mobile/                     # Expo Router app (THE product)
│   ├── app/                         # Screens and routing (file-based)
│   │   ├── _layout.tsx              # Root Stack: (tabs), modal, timer
│   │   ├── (tabs)/                  # Tab navigator
│   │   │   ├── _layout.tsx          # 6 visible + 4 hidden tabs
│   │   │   ├── index.tsx            # Home (high-churn, highest risk)
│   │   │   ├── train.tsx            # Session logging
│   │   │   ├── health.tsx           # HealthKit/WHOOP/Polar display
│   │   │   ├── feedback.tsx         # Daily check-in
│   │   │   ├── map-3d.tsx           # WebView of live 3D grappling map
│   │   │   ├── settings.tsx         # Preferences, tier, schedule, consent
│   │   │   ├── reference.tsx        # Technique reference tree (hidden tab)
│   │   │   ├── suggest.tsx          # Hidden tab
│   │   │   ├── control.tsx          # Hidden tab
│   │   │   └── coaching-history.tsx # Hidden tab
│   │   ├── modal.tsx                # Generic modal route
│   │   └── timer.tsx                # Full-screen interval timer
│   ├── src/
│   │   ├── store/                   # Zustand stores (persisted via secure-storage)
│   │   ├── services/                # Stateless logic (health, AI policy, HIIT, etc.)
│   │   ├── hooks/                   # React hooks (useProgress, useGate, useProfile, etc.)
│   │   ├── components/              # Reusable components (WhoopCard, NutritionCard, etc.)
│   │   └── data/                    # Static bundled data (reference-seed, reference-techniques)
│   └── assets/                      # Fonts, images
├── packages/shared/                 # @lauburu/shared — types, constants, health pipeline, coaching
│   └── src/
│       ├── types/                   # Tier, Capability, Training, Health, Preferences, etc.
│       ├── constants/               # Config, enums
│       ├── health/                  # Normalize → derive → flags → insights → AI payload → coaching
│       └── api/                     # Supabase client, MCP client, edge functions, feedback API
└── package.json                     # Workspaces: ["packages/*", "apps/*"]
```

**Where app logic stops and shared logic begins:**
- `packages/shared` owns types, the health pipeline (normalize → derive → flags → insights → AI payload → coaching), tier/capability definitions, and the coaching rules engine. It has zero React or React Native deps.
- `apps/mobile` owns all UI, routing, state management (Zustand stores), native service bridges (HealthKit, secure storage), and app-specific services (evidence-aware AI, HIIT notes, machine connector).
- Rule of thumb: if it could run in a Node test with no React, it belongs in shared. If it touches Zustand, React hooks, native modules, or screen-specific rendering, it stays in mobile.

---

## 2. Routing and screen ownership

### Root layout (`app/_layout.tsx`)

Stack navigator with three routes:
- `(tabs)` — the main tab group (hidden header)
- `modal` — generic modal presentation
- `timer` — full-screen modal (no header, no gestures)

**Critical behavior:**
- `SplashScreen.preventAutoHideAsync()` called at module level.
- Splash hidden only when fonts loaded AND `authStatus !== 'loading'`.
- All store hydration fires in `useEffect` via `hydrateLaunchStores()` — 10 stores hydrated in parallel, failures isolated per store.
- `unstable_settings.initialRouteName` is `'(tabs)'`.

### Tabs layout (`app/(tabs)/_layout.tsx`)

Six visible tabs in order: Home, Train, Health, Check-in, Map, Settings.
Four hidden tabs (`href: null`): suggest, control, reference, coaching-history.

**What each screen owns:**

| Screen | File | Owns |
|--------|------|------|
| Home | `index.tsx` | Daily coaching brief, readiness, technique recommendation, Ask ChatGPT flow, evidence-aware AI block, WHOOP/nutrition headlines, HIIT continuity cue, coaching follow-up banner |
| Train | `train.tsx` | Session logging, HIIT protocols, machine data, segment builder |
| Health | `health.tsx` | HealthKit sync, permissions, daily metrics, flags, WHOOP/Nutrition/Polar cards |
| Check-in | `feedback.tsx` | Recommendation feedback capture, next-day check-in |
| Map | `map-3d.tsx` | WebView to lauburugrapplingmap.com with injected CSS to hide site chrome |
| Settings | `settings.tsx` | Preferences, schedule, tier display/override, consent, nutrition targets |
| Reference | `reference.tsx` | Full technique tree, search, progress tracking, deep-link focus, transition jumps, coaching-recommended target, map CTAs |
| Coaching History | `coaching-history.tsx` | Saved coaching cases review |

### How Expo Router nesting works here

- File-based routing: `app/(tabs)/index.tsx` = the Home tab at path `/`.
- Hidden tabs are still navigable via `router.push('/reference')` or `router.navigate({ pathname: '/reference', params: {...} })`.
- The map-3d tab accepts an optional `url` search param: `router.navigate({ pathname: '/(tabs)/map-3d', params: { url } })`.
- `useLocalSearchParams` reads route params. Reference uses: `focus`, `focusRole`, `focusHeading`, `focusTechnique`, `focusReason`, `focusSource`, `focusNonce`.

### Common route pitfalls in this repo

- **Tab names must match filenames exactly.** Every `<Tabs.Screen name="...">` in `_layout.tsx` must have a corresponding file in `(tabs)/`. An unmatched name crashes at runtime, not build time.
- **Hidden tabs still need `<Tabs.Screen>` entries.** If a file exists in `(tabs)/` but has no matching `<Tabs.Screen>` in the layout, Expo Router may auto-generate a tab bar entry for it or error depending on the version.
- **`router.navigate` vs `router.push`:** Home uses `router.navigate` to go to Reference (avoids stacking duplicate routes). Reference uses `router.navigate` to go to Map. Use `navigate` for tab-to-tab, `push` for modals/stacks.
- **Route params are strings.** Everything passed via `params` is serialized to strings. The `focusNonce` param exists specifically to force Reference to re-process a focus change when the same position is recommended twice.
- **Reference uses `'/(tabs)/map-3d'` (with group prefix) for map navigation.** Home uses bare `'/reference'` for Reference navigation. Both work but the styles must match what the typed router expects. Before adding a new navigation path, search for existing usages of the same target to match the format.

### How not to break tab/route wiring

1. When adding a file under `app/(tabs)/`, always add a matching `<Tabs.Screen>` in `_layout.tsx`.
2. When renaming a tab file, search all `router.push`, `router.navigate`, and `pathname:` usages first.
3. Do not use `router.push` for tab-to-tab navigation (stacks duplicate routes).
4. Do not use string paths when params are needed — use the object form with `pathname` and `params`.

---

## 3. Home and Reference risk zones

### Why Home (`index.tsx`) is high-churn and easy to worsen

Home is ~1850 lines. It contains:
- The `buildNextTechniqueRecommendation()` engine (~300 lines of scoring, seeding, and candidate ranking) — pure logic that has zero UI deps and should be a service.
- The `TodayCoachCard` component (~400 lines spanning readiness, WHOOP, nutrition, HIIT cues, Ask ChatGPT, evidence-aware AI block) — reads from 10+ stores simultaneously.
- The entire evidence-aware AI UI (mode/topic chips, policy preview, daily allowance card, feature state card, choice card, monetization hint) — growing rapidly across patches.
- Multiple helper functions duplicated from reference.tsx (`lookupPositionTechniques`, `normalizeHeading`, `techniquesForHeading`).

**What belongs in Home vs. should be extracted:**
- Scoring/recommendation logic → service (`src/services/`). It uses only progress data and reference seed data.
- Evidence-aware AI UI → component (`src/components/`) if it exceeds ~100 lines of JSX.
- Duplicated reference helpers → shared utility in `src/data/` or `src/services/`.
- Store reads → always use individual field selectors (`useXStore((s) => s.field)`), never `useXStore()` with no selector.

### Why Reference (`reference.tsx`) is high-risk

Reference is ~2200+ lines. It manages:
- The full collapsible technique tree (sections → positions → roles → headings → techniques).
- Per-item progress tracking (drilling/learned/tracking) via the progress store.
- Search with highlight (position-level and per-row matching index built at module load).
- Transition jumps between positions (cross-tree navigation with filter escapes).
- Coaching focus deep-link consumption (from Home's "Open Reference" CTA).
- Export/import of progress data.
- "Open in 3D map" deep-links into the map-3d tab.

**What changes belong there vs. pushed into helpers/services/store/shared:**
- New rendering of existing tree data → OK in reference.tsx.
- New progress-tracking features → `reference-progress-store.ts`.
- New search logic → extract to a utility; the search index is already module-level.
- New coaching recommendation logic → belongs in a service, fed to Reference via route params.
- New deep-link patterns → must match what the source screen (usually Home) passes as params.
- New transition/graph logic → `src/data/` if it's about the data shape.

### How the Home → Coaching → Reference pipeline currently works

1. Home's `TodayCoachCard` computes `buildDailyCoachingBrief()` (from `@lauburu/shared`) using WHOOP, HealthKit, sessions, preferences, nutrition.
2. Home's `buildNextTechniqueRecommendation()` scores candidate techniques from the user's progress graph (seeded by drilling/learned/tracking entries, boosted by recency, weighted by goal and heading priority).
3. The "Open Reference →" button navigates to `/reference` with params: `focus`, `focusRole`, `focusHeading`, `focusTechnique`, `focusReason`, `focusSource`, `focusNonce`.
4. Reference's `useLocalSearchParams` reads those params. The screen auto-expands the target position, scrolls to it, and highlights the recommended technique.
5. Reference uses `consumedRouteFocusRef` and the `focusNonce` to avoid re-processing the same focus on re-renders.
6. From Reference, the user can tap "Open in 3D map" which calls `router.navigate({ pathname: '/(tabs)/map-3d', params: { url } })`.

### How not to reintroduce stale route/focus/cue bugs

- **Always include `focusNonce: Date.now().toString()`** when navigating to Reference with a coaching focus. Without it, navigating to the same position twice does nothing because the params haven't changed.
- **Never store focus state in the progress store.** Focus is ephemeral route state consumed once. Progress is persistent.
- **Don't reset `consumedRouteFocusRef` on unmount.** It prevents duplicate processing; resetting it causes the focus to fire again when the tab re-mounts.
- **Don't add new params to Reference without updating the `useLocalSearchParams` type.** Expo Router will silently ignore untyped params.
- **Cross-tree transition jumps use `focusTarget` state + `filterEscapeNote`.** If the jump destination is hidden by search or the built-out filter, the jump clears those filters and shows an escape note. Modifying one state without understanding the others reintroduces lost-focus bugs.

---

## 4. State, persistence, and hydration

### Store inventory

All stores live in `apps/mobile/src/store/` and use Zustand. Persistence is through `secure-storage.ts`.

| Store | Storage key | What it persists |
|-------|-------------|-----------------|
| `auth-store` | Supabase session (via `secureStorage` adapter) | Auth session tokens |
| `training-store` | `training_sessions_v1` | Logged training sessions |
| `nutrition-store` | `nutrition_v1` | Today's fuel, targets, history |
| `coaching-cases-store` | `coaching_cases_v1` | Saved coaching Q&A cases + pending drafts |
| `hiit-protocols-store` | `hiit_protocols_v1` | Named HIIT protocol library |
| `reference-progress-store` | `reference_progress_v1` | Per-technique drilling/learned/tracking, notes, timestamps (schema v2 wrapper) |
| `preferences-store` | `coaching_preferences_v1` | Goal, tone, recovery conservatism, weekly schedule |
| `feedback-store` | `feedback_v1` | Recommendation feedbacks, check-ins, queued examples |
| `consent-store` | `consent_v1` | Data-use consent flags |
| `tier-store` | `tier_state_v1` | Real tier + dev override |
| `health-store` | `health_sync_meta_v1` | **Only sync metadata** (lastSyncAt, lastPersistedAt). Raw health data, derived features, AI payloads, coaching responses are NOT persisted. |
| `whoop-store` | Not persisted | WHOOP day data fetched fresh every launch |
| `polar-store` | Not persisted | Polar data |
| `machine-store` | Not persisted | Bluetooth machine metrics |
| `timer-store` | Not persisted | Interval timer state |

### How persistence works

1. `secure-storage.ts` provides `readStoredJson<T>(key)` / `writeStoredJson(key, value)` / `removeStoredJson(key)` wrappers around a three-tier fallback: expo-secure-store (Keychain/Keystore) → expo-file-system → in-memory `Map`.
2. Each store has a `hydrate()` method that reads from storage and a `persistSafely()` helper that writes. Mutations call `persistSafely` fire-and-forget inside `set()`.
3. All 10 persistable stores are hydrated in parallel at app launch in `_layout.tsx`'s `hydrateLaunchStores()`. Failure in any one does not block the others.

### Common persistence pitfalls in this codebase

- **Health data is intentionally NOT persisted.** Showing stale readiness on cold start is worse than "Tap to sync". Only the sync-metadata timestamps are persisted. The comment block in `health-store.ts` (lines 64-75) explains this explicitly.
- **The tier store persists both the real tier and the dev override.** If you read `tier` directly you get the real billing tier. Use `effectiveTier()` to respect the dev override. Policy logic must always use `effectiveTier()`.
- **`persistSafely` is fire-and-forget.** It never throws and never blocks the UI. A persist failure is silent — the user sees the change in-memory but it won't survive app kill. This is by design.
- **Schema migrations must be backwards-compatible.** The reference-progress-store bumped from schema v1 (flat progress map) to v2 (wrapped `{ schema, progress, notes, updated_at }`). Hydration falls back to v1 shape. Always handle the previous shape.
- **Empty state = remove storage key entirely.** Multiple stores call `removeStoredJson` when the persisted blob is empty (e.g. training sessions = [], tier = free with no override). Don't leave empty JSON blobs in storage.
- **Circular imports are real.** `training-store.ts` uses a lazy `setTimeout(() => require('./feedback-store'))` to avoid a top-level circular import with feedback-store. If you add cross-store dependencies, check for cycles.

### How to add a new persisted store safely

1. Create the store in `src/store/` with Zustand `create()`.
2. Add a `STORAGE_KEY` constant (versioned: `'my_feature_v1'`).
3. Add `hydrate()` that calls `readStoredJson()` and a `sanitize()` that validates the stored shape and falls back to defaults.
4. Add `persistSafely()` that calls `writeStoredJson()` — fire-and-forget inside `set()`.
5. **Import the store's `hydrate` in `app/_layout.tsx` and add it to the `hydrateLaunchStores()` array.**

Step 5 is the one most likely to be forgotten. If you skip it, the store works in-memory but resets to defaults on every cold start, creating a false "saved" UX where the user thinks data persisted but it didn't.

### Where launch hydration is easy to forget

The hydration list in `_layout.tsx` (lines 78-89) is manually maintained. There is no automatic discovery. If you create a new store with persistence, you must add its `hydrate` to the list AND add the selector to the `useEffect` dependency array (lines 90-102). Missing either one means silent data loss on cold start.

---

## 5. Services and policy layer

### What belongs in `apps/mobile/src/services/`

Stateless logic that transforms inputs into outputs. No Zustand, no React hooks, no persistence.

| Service | Purpose |
|---------|---------|
| `evidence-aware-ai.ts` | AI request policy resolution, evidence-aware packet builder, daily feature summary |
| `health.ts` / `health.ios.ts` / `health.android.ts` | Native HealthKit/Health Connect bridge (lazy-loaded via `health-store.ts`) |
| `hiit-home-note.ts` | Builds HIIT continuity cue for the Home card |
| `machine-connector.ts` | Bluetooth machine data protocol |
| `bike-connect.ts` | Bike/rowing machine connector |
| `expo-detect.ts` | Detects Expo Go vs dev build |
| `openfoodfacts.ts` | Food barcode lookup |

### Where AI/coaching policy logic should go

**All AI policy logic belongs in `src/services/evidence-aware-ai.ts`**, not in screen files. The service exports:
- `resolveAiRequestPolicy()` (private) — deterministic policy resolver: (mode, tier, topic, downgrade preference) → full `AiRequestPolicy` with 27 fields covering status, access resolution, budget class, daily allowance state, feature buckets, monetization path, pay-per-use eligibility, and upgrade hints.
- `previewAiRequestPolicy()` (public) — wrapper for UI pre-resolution before the user taps.
- `buildEvidenceAwareAiRequestPacket()` (public) — assembles the full structured request for the share sheet.
- `buildDailyAiFeatureSummary()` (public) — text summary lines for the daily AI card.

### Where evidence-aware / pricing-cap / daily-cap / feature-bucket logic belongs

This all belongs in `evidence-aware-ai.ts`. The service already defines:
- `AiFeatureBucket`: `'core_coaching' | 'habit_recovery' | 'advanced_analysis'`
- `AiDailyUsageClass`: `'daily_standard' | 'daily_evidence' | 'daily_premium'`
- `AiDailyAllowanceState`: `'available_today' | 'limited_today' | 'fallback_today' | 'unavailable_today'`
- `AiRemainingDailyAllowance`: `'not_tracked_locally' | 'available' | 'limited' | 'exhausted'`
- `AiAccessResolution`: `'included' | 'downgraded' | 'upgrade_required' | 'pay_per_use_available' | 'purchase_required' | 'blocked'`

If you add a `DailyAiUsageTracker` (persisted local counter with date-scoped reset), it should live in a new store (`src/store/ai-usage-store.ts`) and be checked by `resolveAiRequestPolicy()`. Do not put counting logic in screens.

### Current honest state of the AI policy layer

The policy layer is **app-side scaffolding only**. No backend enforcement exists:
- `remainingDailyAllowance` is always `'not_tracked_locally'` — every response, every branch.
- `dailyAllowanceState` values are derived from plan-tier gating, not from usage counting. A user making 100 premium requests in one day sees the same `'limited_today'` on request 1 and request 100.
- `payPerUseAllowed` resolves correctly but the "Use pay-per-use" button sets a note saying checkout isn't wired.
- `purchaseOfferType` values (`'one_off_ai_top_up'`, `'premium_analysis_pass'`) are contract signals for a future checkout flow.
- The entire evidence-aware AI flow uses `Share.share()` to send a text packet to ChatGPT/Claude. No API calls. No cost incurred. No backend contacted.

### How not to hardcode fake backend truth into UI code

- Do not display "2 remaining today" without a real tracker.
- Do not write UI copy like "capped daily and resets at local midnight" if daily enforcement doesn't exist yet.
- Do not add server-side request paths that assume the app has verified daily caps locally.
- Do not treat `Share.share()` as an API call — it costs nothing and sends nothing to our backend.
- Do not add `monetizationPath: 'pay_per_use'` branches that resolve to a real checkout when no checkout exists.
- Keep `'not_tracked_locally'` as the honest default until real counting exists.

---

## 6. Shared domain logic (`packages/shared`)

### What belongs in shared

| Directory | Owns |
|-----------|------|
| `types/` | All domain types: `Tier`, `Capability`, `TrainingSession`, `CoachingPreferences`, `DailyMetrics`, `HealthFlag`, etc. 14 type files. |
| `constants/` | Config values, enums, session type labels |
| `health/` | The full health pipeline: normalize → derive features → compute flags → build AI context → generate insights → export AI payload → generate coaching. 13 files. |
| `api/` | Supabase client, MCP client, edge functions, feedback API |

### The coaching pipeline in shared

```
Raw HealthKit/HC data
  → normalizeHealthData()     → DailyMetrics[]
  → deriveFeatures()          → DerivedFeatures
  → computeFlags()            → HealthFlag[]
  → buildAIHealthContext()    → AIHealthContext
  �� generateInsights()        → TrainingInsight[]
  → exportAIPayload()         → AIPayload
  → generateCoaching()        → CoachingResponse
```

`generateCoaching()` is the deterministic local coaching engine — no model calls, no network. The comment block in `coaching.ts` (lines 1-41) describes a future MCP endpoint that can return a richer `CoachingResponse` from the same `AIPayload`, but **that endpoint does not exist yet**. The app should always show local coaching first, optionally replace with server coaching if available.

### The tier/capability model in shared

`types/tiers.ts` is the source of truth. Four tiers (cumulative):
- `free` — zero marginal cost: local coaching, training log, health sync, preference coaching
- `low_cost` — backend cost: cloud sync, AI export, training history
- `pro` — user-funded: BYO AI, advanced reports, Cronometer/ErgZone
- `ai_premium` — our inference cost: hosted AI coaching, daily AI recommendations, advanced AI insights

`tierHasCapability(tier, cap)` and `minimumTierFor(cap)` are the gating functions. The mobile `tier-store.ts` wraps these with `can(cap)` and `effectiveTier()`. All tier checks in the app should flow through these — never add one-off screen-level gating rules.

### When to move logic from screens to shared

- If the logic uses only domain types and has no React/RN deps → shared.
- If the logic is duplicated between screens → shared or `src/data/` utility.
- Recommendation/scoring logic (`buildNextTechniqueRecommendation` in Home) uses only progress data and reference seed — should be a service or shared module.
- Tier capability checks, preference defaults, session labels → already in shared, keep them there.

### What should stay mobile-only

- Zustand stores (import `zustand`, `expo-secure-store`).
- React hooks (`useProgress`, `useGate`, `useProfile`).
- Native service bridges (HealthKit, Bluetooth, expo-detect).
- Screen-level components and routing.
- AI policy resolution (`evidence-aware-ai.ts`) — it imports from `reference-progress-store`, so it has a mobile-only dependency.

---

## 7. "If you are doing X, edit Y"

### Adding a new Home card
1. Create a function component in `app/(tabs)/index.tsx` (or extract to `src/components/` if it exceeds ~80 lines).
2. Place it in the `HomeScreen` ScrollView at the appropriate vertical position.
3. Wire store subscriptions via individual field selectors.
4. If the card needs derived data from multiple stores, create a helper in `src/services/` first, then render its output.

### Changing coaching recommendation logic
1. The recommendation engine is `buildNextTechniqueRecommendation()` in `app/(tabs)/index.tsx` (lines ~216-446).
2. It uses `POSITION_META`, `REFERENCE_TECHNIQUES`, and the progress store's `progressMap`/`updatedAtMap`.
3. If you're changing the scoring algorithm, the function has zero UI deps — it should be moved to `src/services/` but currently isn't.
4. For health-domain coaching (readiness, intensity, modes), edit `packages/shared/src/health/coaching.ts`.

### Changing the Home coaching CTA behavior
1. `handleAskChatGPT` (line ~795) and `handleEvidenceAwareAsk` (line ~828) in the `TodayCoachCard` component.
2. Both use `Share.share()` — no API calls, no cost.
3. Both call `startPendingCase()` to create a coaching-cases-store draft for the follow-up banner.
4. The follow-up banner is `PendingFollowupBanner` — renders when `coaching-cases-store` has a pending draft.

### Changing Reference rendering
1. Edit `app/(tabs)/reference.tsx`.
2. Tree structure: `ReferenceScreen` → section views → `PositionRow` → headings → technique rows / transition rows.
3. Content comes from `REFERENCE_SECTIONS` (seed) + `REFERENCE_TECHNIQUES` (extracted from web).
4. Progress pills are self-contained: one tap cycles status via `cycleProgress()` on the store.
5. Do not change progress key formats in the screen — update `reference-progress-store.ts` instead.

### Changing Reference focus/jump/deep-link behavior
1. Route params are read in `ReferenceScreen` via `useLocalSearchParams` (line ~2049).
2. `coachingFocus` state drives auto-expand + scroll to the target technique.
3. `focusTarget` state drives cross-tree transition jumps.
4. `filterEscapeNote` handles cases where a jump target was hidden by search/filters.
5. **Always pass `focusNonce: Date.now().toString()`** from the source to force re-processing.

### Adding a new persisted preference
1. If it fits an existing store (e.g. coaching preference), add it to that store's type and `sanitize` function.
2. Update the settings UI in `settings.tsx`.
3. If the preference is part of the shared coaching model, update `packages/shared/src/types/preferences.ts` and any shared defaults.
4. If it's a new domain, create a new store file (see section 4) and **add hydration to `_layout.tsx`**.

### Wiring a new AI policy field
1. Add the field to `AiRequestPolicy` in `src/services/evidence-aware-ai.ts`.
2. Populate it in **all three branches** of `resolveAiRequestPolicy()` (allowed, downgraded, blocked).
3. Update `previewAiRequestPolicy()` if the field affects pre-render display.
4. Surface in the UI via the `previewPolicy` useMemo in `TodayCoachCard`.
5. **Do not set the field to a value that claims enforcement if no enforcement exists.**

### Changing map tab behavior
1. Edit `app/(tabs)/map-3d.tsx` — it's a simple WebView wrapper (~135 lines).
2. The injected CSS (`INJECTED_CSS`) hides website chrome using stable element IDs (`#authBtn`, `#suggestBtn`, `#suggestionModal`, `#refHomePanel`, `#loadingSkeleton`, `header[role="banner"]`, `.skip-link`).
3. The `url` param lets other screens deep-link into specific positions.
4. If the website changes element IDs, the injected CSS selectors silently fail (chrome stays visible, no crash).

### Adding a new tab/route
1. Create the `.tsx` file in `app/(tabs)/`.
2. Add a `<Tabs.Screen name="filename-without-extension" ...>` in `app/(tabs)/_layout.tsx`.
3. For a visible tab: provide `title` and `tabBarIcon`.
4. For a hidden tab: set `options={{ href: null }}`.
5. For a modal/full-screen route: add the file under `app/` (outside `(tabs)/`) and register in `app/_layout.tsx`.
6. **The `name` must exactly match the filename.** Mismatch = runtime crash.
7. Search `router.push`, `router.navigate`, and `pathname:` across `apps/mobile/app/` before shipping.

### Adding a new service-backed AI/coaching surface
1. Define the request/response types in `src/services/`.
2. Build a policy resolver if the feature is tier-gated (follow `resolveAiRequestPolicy` pattern — populate all fields in all branches).
3. Surface via `Share.share()` for now (no live API calls in the current app).
4. If the feature reads progress data, import from `reference-progress-store` — but keep the import at the service level, not inside `packages/shared`.

---

## 8. Dangerous zones and anti-patterns

### Where contributors are likely to break the app

1. **`_layout.tsx` hydration list.** Forgetting to add a new store's `hydrate()` here means persisted data silently resets on every cold start. The user thinks their data saved. It didn't.
2. **`(tabs)/_layout.tsx` tab registration.** Adding a file in `(tabs)/` without a matching `<Tabs.Screen>` (or vice versa) causes runtime crashes or phantom tab bar entries.
3. **Home's `TodayCoachCard`.** It reads from 10+ stores simultaneously. Adding a new store read that triggers expensive re-renders cascades through every card.
4. **Reference's focus/jump system.** The interplay of `coachingFocus`, `focusTarget`, `consumedRouteFocusRef`, and `filterEscapeNote` is fragile. Modifying one without understanding the flow reintroduces double-focus or lost-focus bugs.
5. **Health store native import.** `health-store.ts` uses a lazy try/catch `require('../services/health')` (lines 32-37) so that Expo Go doesn't crash at import time. Adding a direct top-level import of the health service bypasses this safety boundary.

### What not to do in Home
- Don't add synchronous heavy computation in the render path. All scoring/recommendation logic should be wrapped in `useMemo`.
- Don't read entire store objects (`useXStore()` with no selector). Always select individual fields.
- Don't duplicate Reference rendering logic in Home. Home recommends; Reference renders.
- Don't add new inline components beyond ~80 lines without extracting them.
- Don't add new business rules there if they can live in `src/services/` or `packages/shared/`.

### What not to do in Reference
- Don't store UI focus state in the persisted progress store.
- Don't add new deep-link params without updating the `useLocalSearchParams` type.
- Don't reset `consumedRouteFocusRef` — it's intentionally kept across re-renders.
- Don't break the search index by changing `REFERENCE_SECTIONS` or `REFERENCE_TECHNIQUES` shapes without updating the index builder.
- Don't duplicate reference progress key semantics outside `reference-progress-store.ts`.

### Route anti-patterns
- Using `router.push` for tab-to-tab navigation (stacks duplicate routes).
- Using string paths when params are needed (use the object form).
- Omitting `focusNonce` when navigating to Reference with a coaching focus.
- Adding a file in `(tabs)/` without adding it to `_layout.tsx`.
- Changing a tab filename without searching all navigation calls.

### Persistence/hydration anti-patterns
- Persisting raw health data or coaching output (stale readiness on cold start is dangerous).
- Reading `tier` directly instead of `effectiveTier()` (misses dev override).
- Using `await` on `persistSafely` in the `set()` callback (blocks the UI update).
- Adding a new store without adding it to `hydrateLaunchStores()`.
- Bumping a storage schema without a migration path from the previous version.
- Writing persistence from screen components instead of through stores.

### AI/coaching policy anti-patterns
- Hardcoding tier checks in screen code instead of using `resolveAiRequestPolicy()` or `tierStore.can()`.
- Displaying daily usage counts when `remainingDailyAllowance` is always `'not_tracked_locally'`.
- Treating `Share.share()` as an API call — it costs nothing, sends nothing to our backend.
- Adding `monetizationPath: 'pay_per_use'` branches that resolve to a real checkout when no checkout exists.
- Writing UI copy like "3 premium requests remaining today" without a real counter behind it.
- Adding new policy fields to only one branch of `resolveAiRequestPolicy()` — all three branches (allowed, downgraded, blocked) must populate every field.

### How frontend can accidentally overclaim backend capability
- The tier system is **local-only** right now. `tier-store.ts` header comment: "Current implementation: local tier assignment only. Future: Stripe/App Store subscription status determines tier."
- The coaching engine in shared (`generateCoaching()`) is deterministic and local. The comment block describes a future MCP endpoint, but it does not exist yet.
- The evidence-aware AI flow produces a structured JSON packet shared via the system share sheet. It does not call any AI API. It does not incur any cost.
- `payPerUseAllowed` resolves correctly in the policy, but there is no payment, no checkout, and no server-side verification.
- Daily cap fields are typed and populated in every policy response, but every value is static — they reflect plan tier, not actual usage.

---

## 9. Quick decision guide

### Should this go in screen, store, service, or shared?

| Signal | Put it in |
|--------|-----------|
| Uses React hooks, renders JSX | Screen (`app/`) or component (`src/components/`) |
| Manages mutable state across renders | Zustand store (`src/store/`) |
| Pure function: inputs → outputs, no state, no React | Service (`src/services/`) |
| Domain type, constant, or logic usable outside mobile | `packages/shared` |
| Imports `zustand` or `expo-secure-store` | Store (stays in mobile) |
| Duplicated between two screens | Extract to service or shared utility |

### Should this be route state, local state, or persisted state?

| Signal | State type |
|--------|------------|
| Consumed once on navigation, then discarded (e.g. coaching focus target) | Route params |
| Lives only while a component is mounted (e.g. text input, dropdown, loading flag) | `useState` |
| Survives tab switches but not app kill (e.g. WHOOP day data, health sync results) | Zustand store, no persistence |
| Must survive app kill (e.g. training sessions, preferences, progress) | Zustand store + `secure-storage` |
| Describes when data was last synced, not what it contained | Persisted (safe) |
| Describes actual health/coaching output | NOT persisted (rebuild from source) |

### Should this be app-only policy scaffolding or backend truth?

| Signal | Answer |
|--------|--------|
| Derived deterministically from (tier, mode, topic) | App-side scaffolding — fine |
| Claims to count real usage ("3 remaining today") | Needs a real tracker (local or server) |
| Triggers a purchase or payment | Needs real backend integration |
| Gates access to an API that incurs cost | Needs server-side enforcement |
| Exists so a future server can return it instead | App-side scaffolding — label it clearly |
