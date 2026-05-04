# Health metric apps and devices — integration audit

Purpose: ground every wearable/app integration claim against what the
code actually does today. The product principle is unchanged: **app-
owned Lauburu Readiness and Grappler Readiness are the truth;
wearables are supporting evidence**. This doc makes "supporting
evidence" honest.

Authoring rule: do not overclaim. If a field is read into the app but
not surfaced to the user, mark it as "imported, not surfaced". If a
device is listed in marketing but not actually wired, mark it as
"NOT live". Missing data must stay missing — never synthesise.

Updated 2026-05-05.

## Summary table

| Source | Code path | Live today | Role in Lauburu Readiness | Role in Grappler Readiness | Priority |
|---|---|---|---|---|---|
| Apple Health (iOS) | `health.ios.ts` | ✅ | Primary HRV/RHR/sleep/steps source | Autonomic + sleep + load buckets | Keep — already deepest |
| Health Connect (Android) | `health.android.ts` | ✅ | Same as Apple, Android equivalent | Same as Apple, Android equivalent | Keep — parity is the goal |
| WHOOP (direct OAuth) | `whoop-store.ts`, integrations route | ✅ | Source-recovery signal (weight 0.20) | Autonomic + load `raw_source_scores` | Keep — already deepest non-Apple |
| Polar export (CSV/TCX) | `parse-polar-export.ts` | ✅ (manual file import) | Workout/HR fallback | Load bucket fallback | Keep, low-priority |
| Garmin | none | ❌ NOT live | n/a | n/a | Defer; high effort, low cohort |
| Oura | none | ❌ NOT live | n/a | n/a | Defer; small cohort overlap |
| Cronometer | none | ❌ NOT live; nutrition card is manual entry | n/a | n/a | Defer; nutrition isn't a readiness input today |
| Manual check-in | `NextDayCheckin` | ✅ (subset) | Subjective only — not a readiness signal yet | Subjective bucket (placeholder, null today) | Extend — cheapest path to closing Grappler Readiness gaps |
| Phone PPG (camera HR) | none | ❌ NOT live | n/a | n/a | Defer; quality unreliable for HRV |

"Live today" = code reads a real value from the source and stores it
in the app's normalised daily metrics. Storage without surface still
counts as live (the LLM can use it via cached artifacts) but is
flagged below.

## Per-source detail

### Apple Health (iOS) — `apps/mobile/src/services/health.ios.ts`

**Data provided (fields actually read):** sleep duration + stages,
HRV (SDNN), resting HR, heart rate (continuous), steps, active
energy, workouts (type, start, duration, energy), distance.

**Currently surfaced to the user:** all of the above on the Health
tab via `AppleHealthCard`. Trend windows on `/coach/ask` carry HRV,
RHR, sleep_hours, steps, active_energy as primary metrics.

**Imported but not yet surfaced:** workout type granularity beyond
"workout count" — we know whether it was Functional Strength
Training vs Traditional Strength Training, but we don't show the
distinction. Acceptable; the LLM does see it via artifacts.

**Missing fields we could add:** SpO2, respiratory rate, VO2 max
estimate (Apple-published), menstrual cycle data (privacy-gated and
out of scope until a separate consent flow is designed).

**UI/UX risk:** Apple Health permission UX is "all or nothing per
metric"; users sometimes deny one metric and the card shows
"Partial". Already mitigated by per-metric coverage in the card.

**Grappling wearability:** Apple Watch survives most rolling but is
abuse-prone. We do not depend on Watch wear during a session — the
session itself is logged in-app; Watch HR if present is bonus.

**Role in Lauburu Readiness:** primary feeder for HRV (z, weight
0.25), RHR (0.15), sleep_hours (0.30). High coverage on this source
is what makes the score "high confidence".

**Role in Grappler Readiness:** autonomic bucket (HRV/RHR), sleep
bucket (sleep_hours/efficiency proxy), load bucket (active energy +
steps as cardio load proxy until grappling-specific load lands).

**Integration priority:** keep deepest. No new work needed before
the next paired build.

### Health Connect (Android) — `apps/mobile/src/services/health.android.ts`

**Data provided:** heart rate, HRV (SDNN where available — Samsung
Galaxy Watch publishes; Pixel/Fitbit publishes only mean RR),
resting HR, sleep (with stages on Galaxy Watch / Fitbit), steps,
active calories, exercise sessions, history (READ_HEALTH_DATA_HISTORY
permission added).

**Currently surfaced:** same Health-tab UI as iOS via
`SamsungHealthCard` (label kept generic for non-Samsung devices via
the same component; the title is "Health Connect" to a Pixel user).

**Imported but not yet surfaced:** exercise sessions are imported
without grappling-type detection (Health Connect doesn't expose a
"BJJ" exercise type — we'd map it via the user's own session log).

**Missing fields:** SpO2 (some Galaxy Watches publish, currently
unread), skin temperature delta (Pixel Watch 2+, unread).

**UI/UX risk:** Health Connect permissions are listed as a long
flat list; users sometimes deny HRV thinking it's redundant with
heart rate. Already partly mitigated by the per-permission coverage
display.

**Grappling wearability:** depends on the watch. Galaxy Watch 6+
survives most rolls; Pixel Watch is fragile. We give no advice on
which watch to wear — that's not our call.

**Role in Lauburu / Grappler Readiness:** parity with Apple Health
on Android. Same weights, same buckets.

**Integration priority:** keep parity with iOS. If Apple-side adds
a new metric, Android should follow within one batch where Health
Connect supports it.

### WHOOP (direct OAuth) — `whoop-store.ts` + `integrations.ts`

**Data provided:** recovery score (0–100), sleep performance, sleep
stages + duration, HRV (RMSSD), resting HR, day strain, workouts
(type, start, end, average HR, max HR, kilojoules), cycle metadata
(start time → "WHOOP day" definition), profile, body measurements
(if user has them set).

**Currently surfaced:** WHOOP card on Health tab (when connected),
last-3-day domain freshness banner accounting for morning-after
scoring. Recovery score feeds `source_recovery` in Lauburu Readiness.

**Imported but not yet surfaced:** WHOOP journal entries (we don't
read these — they're outside the OAuth scope we requested).
Workout strain is logged but the per-workout strain isn't shown
discretely on the card; it's aggregated into day strain.

**Missing fields:** SpO2 (paid Whoop tier; out of scope), skin
temp deviation (out of scope).

**UI/UX risk:** WHOOP scores recovery the morning **after** the
sleep ends. The first-time UX showing "Partial" because today's
cycle has only strain was a real bug — fixed by walking last 3 days
of dayMap. Don't regress.

**Grappling wearability:** WHOOP strap is the gold standard for
mat survival — soft-band, no rigid case, reasonable BJJ tolerance.

**Role in Lauburu Readiness:** `source_recovery` signal (weight
0.20). Independent of HRV/RHR/sleep_hours which are Apple/HC-fed —
so a user with both gets two cross-checking sources.

**Role in Grappler Readiness:** `raw_source_scores.whoop_recovery`
and `raw_source_scores.whoop_strain` carried unmodified into
artifacts. The bucket compute does NOT trust WHOOP recovery as a
single bucket; it is one input among the autonomic-bucket signals.

**Integration priority:** keep. No new scope before the AI provider
lands.

### Polar export (CSV/TCX) — `parse-polar-export.ts`

**Data provided:** session-level workout records: start, duration,
sport, total HR (avg, max), zones, calorie estimate.

**Currently surfaced:** imported sessions appear in the load bucket
context for Grappler Readiness and as workouts in trends. There is
NO ongoing live-sync — this is a manual file import.

**Imported but not yet surfaced:** PolarFlow's training-load metric
(Polar's own ACWR-like number) is parsed but our compute prefers
its own ACWR; we ignore Polar's value.

**Missing fields:** R-R intervals (Polar exports them in some TCX
flavours; we don't currently parse them — would unlock independent
HRV calc).

**UI/UX risk:** users find file export awkward; the import UX is
intentionally tucked away under a disclosure. Don't promote it.

**Grappling wearability:** Polar OH1/Verity Sense armband is
mat-survivable; Polar chest strap is not (it slides during rolls
and the buckle scrapes). We do not advise on hardware.

**Role in Lauburu / Grappler Readiness:** workout-level fallback
when the user has no Apple/HC/WHOOP coverage. Low contribution; do
not weight heavily.

**Integration priority:** keep, low. Don't add live API integration
until a real cohort asks for it.

### Garmin

**Data provided (if integrated):** would be the deepest single
source for serious endurance athletes — Body Battery, training
status, training load, HRV status, sleep, all-day stress.

**Currently live:** NOT live. No code path. Marketing must not list
Garmin as supported.

**Missing fields:** all of them.

**UI/UX risk:** Garmin's API tier (Health API) requires a sign-off
process and per-user Garmin Connect OAuth. Material engineering
work.

**Grappling wearability:** Forerunner/Fenix is bulky and fragile in
gi training; some grapplers wear the small `Lily` or `Vivosmart` —
neither is universal.

**Role in Readiness:** would be a strong autonomic + sleep + load
contributor on parity with WHOOP if integrated.

**Integration priority:** **defer**. High engineering cost; small
overlap with grappling cohort. Revisit only if cohort signals
demand.

### Oura

**Data provided (if integrated):** ring-based sleep, HRV
(rMSSD), RHR, body temp deviation, readiness score.

**Currently live:** NOT live. Marketing must not list Oura as
supported.

**Grappling wearability:** rings + grappling = bad. The ring is
a tap-out hazard and gets stripped of finish from gi friction
within weeks. Grapplers wearing Oura typically remove it for class.

**Role in Readiness:** sleep + autonomic contributor on parity
with WHOOP / Apple Watch.

**Integration priority:** **defer**. Cohort overlap is small
specifically because of the wearability problem above.

### Cronometer / nutrition

**Currently live:** NOT live as an integration. The Nutrition card
on Health tab is **manual entry** + a barcode scanner that resolves
to an in-app catalog. There is no Cronometer / MyFitnessPal sync.

**Role in Readiness:** **none today.** Nutrition is not a Lauburu
or Grappler Readiness input. Energy availability matters
physiologically but we deliberately do not infer "you're under-
fuelled" from a calorie deficit because the false-positive rate
on consumer logging is high enough to make this advice harmful.

**Integration priority:** **defer.** If integrated, the design
should be: import for context, never as a readiness signal.

### Manual check-in — `NextDayCheckin`

**Data provided:** subjective wake-feel, soreness, mood, training
load impression.

**Currently surfaced:** day-level subjective signals on the Health
tab and in trends.

**Role in Lauburu Readiness:** none — Lauburu is intentionally
objective-only.

**Role in Grappler Readiness:** the subjective bucket and parts of
the grappling bucket. Today both buckets are placeholders (return
null) because the check-in fields needed (rolling intensity, gi vs
no-gi minutes, drilling vs live, perceived exertion) don't exist
yet. **This is the cheapest path to making Grappler Readiness fully
non-null** — extend the form before adding new wearable
integrations.

**Integration priority:** **highest non-blocking work** in the
health space. Path: Grappler Readiness Batch B (extend
NextDayCheckin), then Batch C (extend TrainingSession with
grappling-load fields), then Batch D (bucket-ring UI).

### Phone PPG (camera-on-finger HRV)

**Currently live:** NOT live. No code path. Considered, rejected
for now.

**Why deferred:** consumer phone PPG produces HR reliably but HRV
estimates are noisy enough that a daily reading would add variance
without improving signal. The watch-based HRV we already have is
better.

**Integration priority:** **defer indefinitely** unless a watch-
free cohort emerges that genuinely can't get HRV any other way.

## Cross-cutting UI/UX rules

These hold across every source:

1. **Missing data stays missing.** Empty trend window → "not enough
   data for {{window}}". Never fall back to a different window
   silently. Never synthesise.
2. **Per-source freshness must reflect domain reality.** WHOOP
   recovery scores morning-after; HealthKit sleep posts after wake;
   workouts post on session end. UI banners must match — see the
   `whoop_direct` last-3-days fix.
3. **Wearable claims in marketing match this audit exactly.**
   Anything not green-checked above does not appear in store
   listings, website copy, or the Settings → "Connected sources"
   list.
4. **Permission denial is silent on subsequent launches.** If the
   user denied a metric, the card must NOT re-prompt on every open;
   it must show "denied — re-enable in Settings" with a link.
5. **Per-metric provenance.** When a value is shown in a Coach
   answer or readiness compute, the source is identifiable in the
   underlying artifact (already true via the trend `source_breakdown`
   field). UI doesn't need to render it on every card, but the LLM
   has it.

## What's feeding readiness today vs tomorrow

Lauburu Readiness — fully populated already (HRV / RHR / sleep_hours
/ source_recovery / acute_chronic_ratio).

Grappler Readiness — three of five buckets live (autonomic, sleep,
load); two return null until check-in/session schema is extended:

| Bucket | Live? | Blocker |
|---|---|---|
| autonomic | ✅ | — |
| sleep | ✅ | — |
| load | ✅ | — |
| grappling | ❌ | TrainingSession lacks gi/no-gi, rolling-vs-drilling, perceived-exertion |
| subjective | ❌ | NextDayCheckin lacks soreness sliders + intensity recall |

**Recommendation:** before any new device integration, ship Grappler
Readiness Batches B/C/D so the existing audit is internally
consistent (we can't claim a wearable feeds the grappling bucket
when the grappling bucket itself doesn't compute).

## What this doc does NOT cover

- Specific permission copy (lives in `app.json` `infoPlist` and is
  reviewed against current values when copy changes).
- Privacy policy detail (separate doc / live page).
- Data-deletion mechanics (already live at
  `https://www.lauburugrapplingmap.com/account-deletion/` and in
  Settings → Request account/data deletion).
- Chest-strap HR live-stream during HIIT (separate FTMS / Polar OH1
  Bluetooth path on the Train tab; that's a real-time concern, not
  a daily-readiness concern).
