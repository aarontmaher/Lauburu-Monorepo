# Nutrition tracking plan

How nutrition fits into the app — context only, never a coaching
input. Documented here so the implementation doesn't drift into
medical claim territory and so the priority stays below the
Apple Health / Health Connect lane until that one is stable.

Updated 2026-05-06.

## Priority

Below #1 (Apple Health on iOS), #2 (Health Connect on Android),
and #4 (cautious Grappler Readiness prototype). Nutrition does NOT
gate readiness; it does NOT block any other lane. It's
**evidence/context for trends**, not a daily-readiness signal.

## What lives today

- `apps/mobile/src/store/nutrition-store.ts` — daily totals,
  history, targets.
- `apps/mobile/src/components/NutritionCard.tsx` — Health-tab
  surface.
- `apps/mobile/src/services/health.ios.ts` `fetchDietaryDailyTotals`
  — Apple Health dietary read on iOS.
- `apps/mobile/src/services/ai-photo-nutrition.ts` — photo-based
  meal estimation scaffold.
- `apps/mobile/src/components/BarcodeScanner.tsx` — UPC barcode
  → catalog lookup.
- Backend: `chat-app/src/server/routes/internal.ts`
  `/ingest/nutrition/daily` — server-side nutrition daily ingest
  for the AI context bundle.
- Backend: `chat-app/src/server/routes/integrations.ts`
  `/cronometer/{status,import}` — scaffold (UI not wired).

## What we capture

Fields that matter for trend context (NOT for readiness):

- **Calories** (kcal/day).
- **Macros**: protein (g), carbs (g), fat (g).
- **Hydration**: water (ml).
- **Meal timing**: first meal, last meal, meal count per day.
- **Carb timing around training**: user-entered/imported context
  only, not an automatic readiness claim.
- **Daily Dozen-style checklist completion**: optional manual habit
  checklist per FS-021; not assumed to have an official API/export.
- **Weight**: body weight on a slow cadence (weekly, monthly).
- **Goals**: target weight, target macro split.

Out of scope:

- Per-meal photos as authoritative — photo nutrition is heuristic.
- Detailed micronutrients — Cronometer / specialised apps cover
  this; Lauburu doesn't compete with them.
- Real-time meal alerting — not a notification surface.

## What nutrition NEVER does

1. **Does NOT feed Lauburu Readiness or Grappler Readiness as a
   primary input.** Energy availability matters physiologically,
   but consumer logging error rates (off by ±20–30% routinely)
   mean a "calorie deficit detected" signal would be wrong far
   too often to drive coaching. False negatives ("you're
   under-fuelled") would damage trust faster than they'd help.
2. **Does NOT generate medical advice.** No "you have a deficiency
   in X", no "you need supplement Y", no "your eating disorder…".
   The app surfaces facts; users interpret with their own clinician.
3. **Does NOT auto-import without user opt-in.** Cronometer,
   MyFitnessPal, Apple Health dietary reads — every import is an
   explicit per-source opt-in.
4. **Does NOT label nutrition data "live" unless it's the latest
   logged value.** Stale dietary days surface with a "Last logged:
   {date}" label.

## What nutrition DOES do

- **Trend context for Coach answers.** When a user asks "how was
  my training week", nutrition history (last 14–60 days) is a
  fact in the context bundle alongside training and sleep.
  Coach can say "protein has been below target on 4 of last 7
  training days" — a factual sentence, not advice.
- **Daily totals on Health tab.** The NutritionCard surfaces
  today's running totals + macro distribution + a "log" CTA.
- **Pre-session fuelling check.** A separate small surface (when
  built) on Train tab can ask "have you eaten in the last 2
  hours?" before a hard session. Manual user input, no auto-
  inference.

## Implementation priority within the nutrition lane

1. Confirm `fetchDietaryDailyTotals` works on iOS post-Build 16
   (Apple Health dietary read). The merge path in
   `ai-chat.tsx` already calls it before each Coach question.
2. Add a Health Connect dietary read where the Android schema
   supports it (limited today; some OEMs publish, most don't).
3. Cronometer UI wire-up (the backend route exists; mobile UI
   doesn't surface it). Defer until a Cronometer cohort actually
   exists.
4. Photo-based meal estimation — cautious, behind a clear
   "estimate" label. Heuristic; never claimed as accurate.
5. Per-meal log refinement — beyond MVP; tracks meal timing for
   trend analysis.
6. FS-021 Daily Dozen-style checklist — manual first, optional CSV
   later. Completion may be compared with training/recovery context
   using "associated with" language only.

## UI rules

- Show today's calorie/macro running totals on Health tab.
- Show a "Last logged: {time}" stamp when no fresh log in last
  4h.
- Empty-state copy: "No nutrition logged today. Tap to add a
  meal." Do NOT say "you haven't eaten" — the app cannot infer
  that.
- Goals are user-set; the app does not auto-prescribe a target
  unless the user explicitly opts into a goal-setting flow.
- All nutrition values render with their unit ("180 g protein"
  / "2,400 kcal") — never bare numbers.

## Privacy

Per `RAILWAY_BACKEND_AUDIT.md`:

- Daily nutrition totals persist in Supabase (`normalized_daily_
  metrics` schema may carry `nutrition_kcal` etc — verify before
  expanding).
- Per-meal photos persist on the device only unless user
  explicitly uploads (no current upload path).
- Cronometer / MyFitnessPal credentials NEVER in the app — OAuth
  through the backend per existing pattern, like WHOOP / Polar.

## Out of scope

- Eating disorder detection / intervention — out of scope, full
  stop. The app does not have the clinical training to do this
  responsibly.
- Hydration reminders / push notifications — defer; opt-in only
  if ever built.
- Body composition (lean mass / fat mass) — covered separately
  in `DEXA_BLOOD_TEST_UPLOAD_PLAN.md`.
- Coffee / alcohol / supplement tracking — defer; not core to
  grappling performance modelling.
