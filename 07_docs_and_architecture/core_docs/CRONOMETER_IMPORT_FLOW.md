# Cronometer import flow — spec

The single doc that describes how Cronometer data lands in
Lauburu, how Lauburu normalises it, and what the user-facing
copy says. Updated 2026-05-07 against
`CLAUDE-MCP-UNIFICATION-SPEC-04`.

This is **spec only**. No implementation gates here; those
land via `docs/FEEDBACK_SUGGESTIONS.md` candidates.

## 1. Decision: hub-first, no direct API

Cronometer writes to **Apple Health** (iOS) and **Health
Connect** (Android) when the user enables those toggles in
the Cronometer app. Lauburu reads via the platform hub. There
is no direct Cronometer API integration, no Cronometer OAuth
in Lauburu, and no `Cronometer Direct` truth label.

**Why hub-first wins here:**
- Cronometer's third-party API is rate-limited and scoped per
  partner; building it duplicates the hub path the user
  already configured.
- Beginners don't need a second connect step — they're already
  configuring Apple Health / Health Connect.
- The hub aggregates Cronometer + manual + photo-capture into
  one daily total, which is what the readiness compute and
  beginner UI want.
- Less PII flowing through Lauburu's backend.

**Decision: do NOT add a Cronometer OAuth or API-key path.**
If a user's Cronometer-to-hub sync is broken, the fix is in
Cronometer's settings, not in Lauburu.

## 2. Source matrix

| Lauburu source | Cronometer is the upstream when… | Truth label | Provenance label rendered |
|---|---|---|---|
| `apple_health` (iOS) | Cronometer iOS app → Apple Health → Lauburu | `synced from hub` | `Cronometer via Apple Health` |
| `health_connect` (Android) | Cronometer Android app → Health Connect → Lauburu | `synced from hub` | `Cronometer via Health Connect` |
| `manual` | user types meals into Lauburu's nutrition card | `live` (manual) | (no Cronometer involvement) |
| `photo_capture` | user snaps a photo → AI extracts nutrition → Lauburu | `live` (manual) | (no Cronometer involvement) |

Anti-rule: when Cronometer data arrives via the hub, the
`provenanceLabel` MUST cite the hub
(`"Cronometer via Apple Health"` /
`"Cronometer via Health Connect"`), never `"Cronometer
Direct"`, never `"Cronometer (live)"`, never `"Cronometer +
hub"`.

## 3. Normalisation rules

Cronometer's hub writes carry their own field shapes. Lauburu
normalises to one canonical row per day:

```ts
interface NutritionDailyRow {
  date: string;                       // YYYY-MM-DD, user's local
  source: 'apple_health' | 'health_connect' | 'manual' | 'photo_capture';
  provenanceLabel: string;            // "Cronometer via Apple Health" | …
  truthLabel: 'live' | 'synced from hub' | 'imported summary';
  totals: {
    kcal: number | null;
    proteinG: number | null;
    carbsG: number | null;
    fatG: number | null;
    fiberG: number | null;
    waterMl: number | null;
  };
  meals?: NutritionMealRow[];         // optional, only when hub carries breakdown
  generatedAt: string;                // ISO Z
}
```

### 3.1 Per-field rules

- **Missing values stay null.** Never zero. The reader is
  responsible for rendering missing as "no data", per the
  copy bank in `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md`.
- **Unit conversion**: Cronometer-via-Apple-Health writes
  values in metric. Carry through metric internally; convert
  to user's locale display unit at render time only.
- **Day boundary**: Lauburu uses the user's local day boundary
  (00:00 local). Hub data carrying timestamps is bucketed
  into the local day. A meal logged at 23:55 stays in that
  day; a meal at 00:05 lands in the next.
- **Duplicate detection**: when both hub and manual sources
  carry a totals row for the same date, **the hub wins**
  (Cronometer's totals already include manual entries the
  user typed into Cronometer). The manual entry is suppressed
  with a "Cronometer already covered today" hint.
- **Idempotent ingest**: each hub fetch upserts into
  `nutrition_daily` keyed by `(user_id, date)`. Lower-fidelity
  fields don't overwrite higher-fidelity ones (e.g. a
  manual-only row with `kcal=2000` doesn't overwrite a hub
  row with full breakdown).

### 3.2 Meal-level breakdown

Meal-level breakdowns are kept when the hub carries them
(Cronometer-via-Apple-Health does include them since iOS 14).
Use:

```ts
interface NutritionMealRow {
  startedAt: string;                  // ISO Z
  name: string | null;                // hub-provided meal name if any
  kcal: number | null;
  proteinG: number | null;
  carbsG: number | null;
  fatG: number | null;
  fiberG: number | null;
}
```

Beginners do not see meal-level breakdown by default. Veteran
"More sources" disclosure shows it.

## 4. UI copy

All strings live in
`docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` as the source
of truth. The Cronometer-specific subset:

### 4.1 Source label rendered next to a Cronometer row

> **Cronometer via Apple Health** &nbsp;·&nbsp; synced from hub

### 4.2 Beginner empty state (no nutrition data today)

> **No nutrition data yet today.** &nbsp; If you log meals in
> Cronometer or another nutrition app, enable the Apple Health
> (or Health Connect) write toggle in that app's settings
> and Lauburu will pick it up automatically. You can also tap
> **+ Log meal** below to add directly.

### 4.3 Beginner "everything via Cronometer" state

> Today's nutrition came from **Cronometer via Apple Health**.
> &nbsp; Showing daily totals; tap to see meal breakdown.

### 4.4 Veteran "mixed sources" line

> Today's nutrition: 1,840 kcal · 124 g protein · 215 g carbs ·
> 62 g fat. &nbsp; Sources: **Cronometer via Apple Health** (3
> meals) · **manual** (2 entries) · hub totals win where they
> overlap.

### 4.5 Hub-write toggle reminder (settings)

> Lauburu reads from your platform health hub. To send
> Cronometer data through, open **Cronometer → Settings →
> Devices & Apps → Apple Health** (or **Health Connect** on
> Android) and enable the writes you want shared. Lauburu
> picks them up automatically — no separate Cronometer
> connection needed.

### 4.6 Anti-strings (must not appear anywhere)

- ~~"Cronometer Direct"~~
- ~~"Connect to Cronometer"~~ (no direct connect path exists)
- ~~"Cronometer is offline"~~ (we don't poll Cronometer
  directly; it can't be "offline" from our perspective)
- ~~"Cronometer + manual"~~ (use "via" for hub provenance,
  use semicolons / bullets for source aggregation)
- ~~"Coaching:" / "Recommendation:" / "Goal hit!"~~ — nutrition
  is context, not coaching.

## 5. Beginner / veteran UX

| | Beginner | Veteran |
|---|---|---|
| Default nutrition card | daily total kcal + macros + targets | same + meal breakdown + per-source provenance |
| "More sources" disclosure | hidden | shows source mix (Cronometer-via-hub, manual, photo) |
| Settings hint | one-line reminder to enable Cronometer's hub write toggle | full settings deep-link + last-sync timestamp + per-meal source list |
| Empty state | "No nutrition data yet today" + tap-to-log button | same, plus per-source last-sync row |

## 6. Readiness compute eligibility

Cronometer-sourced data is **NEVER** an input to Grappler
Readiness compute. Nutrition is context only, per
`docs/NUTRITION_TRACKING_PLAN.md` and audit doc § 1.9 / 1.10.

This holds whether the data arrives via hub or via the
manual / photo paths. No "low protein → low readiness"
inference is allowed in the prototype or v1.

## 7. Privacy

- Cronometer data is per-user storage. No cross-user share, no
  aggregate telemetry includes nutrition values.
- Hub provenance metadata (the literal phrase "Cronometer via
  Apple Health") is treated as personal-data-adjacent: it
  reveals the user uses Cronometer. It MUST NOT appear in
  any `/mcp/v2` public-safe response, in
  `integrations.get_overview` aggregates, or in any
  control-centre admin response without admin auth.
- Photo-capture nutrition data follows the same rules as
  manual: per-user, never aggregated.

## 8. Anti-rules

- **No direct Cronometer API integration.** If a future
  product driver demands per-event timing or per-food
  nutrient detail beyond what the hub carries, that is a
  separate doc commit + Aaron approval, NOT a one-line code
  add.
- **No "Cronometer Direct" UI label, ever** (label reserved
  but not used; no path to enable it).
- **No fallback to a Cronometer-specific normaliser if hub
  data is absent.** If the hub didn't carry it, it didn't
  arrive. Render "no data".
- **No coaching language** on any nutrition surface.
- **No promotion of nutrition into readiness compute.** This
  is enforced at the compute layer, not at the import layer.
- **No CSV upload / export-from-Cronometer parser** unless
  explicitly added as a separate FS-XXX candidate. Hub-first
  is the only contract.

## 9. Cross-references

- `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.9 / § 1.10 /
  § 3.1.
- `docs/NUTRITION_TRACKING_PLAN.md` (the parent nutrition
  contract — totals, targets, history, anti-rules).
- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` (truth labels +
  provenance label format).
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` (all UI
  strings live there; this doc lifts only the Cronometer
  subset).
- `docs/PRIVACY.md` (per-user storage rules).
