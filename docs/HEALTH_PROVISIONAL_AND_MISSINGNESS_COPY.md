# Health — provisional readiness + missingness copy bank

The single source of truth for user-facing strings around
**provisional readiness**, **missing data**, **stale data**,
**setup-required states**, and **truth-label provenance** in
the mobile app. Updated 2026-05-07 against
`CLAUDE-MCP-UNIFICATION-SPEC-04`.

This is **spec only**. The strings here are the canonical
versions; mobile UI changes that touch these strings MUST
copy from this doc. Codex's Phase 1 audit batch references
this doc directly.

## 0. Anchor principles

Every string in this doc honours four anchors:

1. **Honesty over reassurance.** "We don't have today's data"
   beats "Looking good!" when there's no data.
2. **Truth label visible.** Every metric value carries one of
   the six canonical labels (see § 1.1). No bare numbers.
3. **No coaching, no claims.** No "you should…", no "skip
   training today", no clinical language.
4. **Confidence is hedged.** Provisional readings sound
   provisional. Strong claims require strong data which we
   don't have yet.

## 1. The six truth labels — canonical user-visible strings

| Internal label | User-visible chip | When |
|---|---|---|
| `live` | "live" | Direct, real-time vendor data confirmed working ≥7 days. Today: only Apple Health, Health Connect, manual log, and (after § 1.4 ships) WHOOP-direct after the seed window. |
| `synced from hub` | "via Apple Health" / "via Health Connect" — never the bare phrase "synced from hub" | Polar / Cronometer / Concept2 etc. data routed through the platform health hub. |
| `imported summary` | "imported" | CSV / FIT / TCX / WHOOP-export / blood-test / DEXA upload — daily-total grain, not real-time. |
| `seed/provisional` | "seed (X day{s} of 7)" where X is the number of clean post-migration days | First 7 days after a direct connection comes online, before truth label may flip to `live`. |
| `setup required` | "needs setup" with a tap-to-connect button | Source has a code path but the user hasn't connected yet, or the vendor side is mid-migration. |
| `planned` | "planned" / surface hidden by default | Source is in the spec but no implementation has shipped. |

The chip is rendered in caption text **next to the value**,
not as a separate row. Veteran "More sources" disclosure
shows the full provenance line; beginners see the chip only.

### 1.1 Provenance line format (veteran disclosure)

```
{ProviderName} {chip text} · last sync {relative time}
```

Examples:
- `WHOOP · seed (3 days of 7) · last sync 12 min ago`
- `Polar · via Apple Health · last sync 4 min ago`
- `Concept2 ErgData · via Health Connect · last sync 1 hour ago`
- `Cronometer · via Apple Health · last sync today`
- `WHOOP export · imported · uploaded 4 days ago`

## 2. Missing-data strings

Used when a metric or bucket has **no data** for the date
the user is viewing.

### 2.1 Per-metric "no data" caption

The metric tile / chip shows the metric name and a caption:

```
{Metric Name}
no data
```

Examples:
- `RHR — no data`
- `HRV — no data`
- `Sleep duration — no data`
- `Active calories — no data`

Anti-string:
- ~~`Heart rate: 0 bpm`~~ (don't show fabricated zero)
- ~~`HRV: --`~~ (the literal "--" reads as "is broken", not as "missing")
- ~~`No HRV today (unusual)`~~ (don't editorialise; we don't know if it's unusual)

### 2.2 Whole-card empty state

When a source has zero data for the date:

> **No data from {Source} today.**
> {Source} data appears here when {trigger}. Until then, {alternative}.

Variants:
- Apple Health: "Apple Health data appears here when your iPhone or Apple Watch records it. Make sure HealthKit is enabled in **Settings → Privacy → Health → Lauburu**."
- Health Connect: "Health Connect data appears here when an installed app writes to it. Open **Health Connect → App Permissions** and confirm Lauburu has read access."
- WHOOP (via direct): "WHOOP data appears here when your strap syncs to the WHOOP cloud. The WHOOP app must be open and signed in to push the latest reading."
- WHOOP export: "Upload a WHOOP export ZIP from **Account → Export Data** in the WHOOP app to backfill historical data."
- Manual log: "Tap **+ Add session** to log today's training."

### 2.3 Per-bucket missingness (readiness compute)

Used by the bucket-ring UI when one of the 5 readiness
buckets has no usable input:

> Bucket: **{name}**
> no data
> *(provenance: missing)*

Beginners see a greyed-out arc with the literal text "no
data" below the bucket name. No fabricated bucket value, no
imputed default.

Anti-string:
- ~~`Sleep bucket: assuming 7 hours`~~ (no implicit assumptions)
- ~~`Sleep bucket: poor (estimated)`~~ (no estimates)

## 3. Stale-data strings

Used when data exists but is older than the freshness window
(currently 10 minutes for MCP-bound rows; per-source windows
vary for sleep / nutrition / etc.).

### 3.1 Per-source stale chip

```
{Source} · last sync {relative time} (stale)
```

The chip turns muted (not red — red is reserved for failure
states, not staleness).

### 3.2 Stale banner on the Health tab

> **Some sources haven't synced recently.** Open the source's
> companion app (e.g. WHOOP, Polar Flow) so it can push the
> latest reading, then pull-to-refresh here.

This banner appears only when ≥1 connected source is stale
beyond its per-source window. If everything is fresh, no
banner — silence is the correct UI here.

## 4. Provisional-readiness strings

Used by Grappler Readiness v1 (Lane B) when the compute
returns a value labelled `confidence: provisional` or
`confidence: low`.

### 4.1 Bucket-ring caption (beginner default)

> **Today's readiness: provisional.** Based on the data
> available now. We'll show stronger signals as more sources
> come online.

Anti-strings:
- ~~"You are ready to train."~~ (claim too strong)
- ~~"Skip training today."~~ (instruction; never)
- ~~"Your readiness is poor."~~ (judgement; never)
- ~~"7/10 readiness."~~ (numeric without provenance)

### 4.2 Per-bucket caption with confidence chip

```
{Bucket name}
{value | "no data"}
{confidence chip: provisional | low | medium}
```

Examples:
- `Autonomic — HRV 58 ms — provisional`
- `Sleep — 7h 12m — low`
- `Load — no data — (no chip; "missing" is its own state)`

### 4.3 Hedge-language phrases (allowed)

Use any of these when surfacing a readiness summary:
- "Based on available data, today's signal suggests…"
- "With the sources connected so far, …"
- "We'd want WHOOP / direct sources to make this stronger."
- "Provisional only — connect more sources to firm this up."

Banned phrases (never use):
- "You are…"
- "You should…"
- "Skip…"
- "Recommend…"
- "Optimal" / "suboptimal"
- "Recovered" / "not recovered" without `synced from hub` /
  `live` provenance.

### 4.4 Confidence-tier ladder (visible to veterans)

| Chip | Meaning | When |
|---|---|---|
| `provisional` | floor; assumes nothing about veracity | always at least this; default during seed window |
| `low` | enough data to compute, but provenance is partial | manual log + 1 hub source, no direct |
| `medium` | direct WHOOP / Polar source live ≥7 days clean | only after § 1.4.d / § 1.5 promotion |
| `high` | reserved | never returned by prototype until explicit doc-commit promotion |

Anti-rule: the `high` tier is documented for completeness
only; the compute MUST NOT return it today.

## 5. Setup-required strings

Used when a source's code path exists but the user hasn't
connected yet, or vendor-side setup is pending.

### 5.1 Connect-button card (beginner)

> **{Source} — needs setup**
> Connect {Source} to bring {what it adds} into Lauburu.
> [ Connect {Source} ]

Examples:
- WHOOP (post-migration): "Connect WHOOP to bring recovery,
  sleep, and strain into Lauburu."
- Polar AccessLink (post-ship): "Connect Polar to bring
  detailed HRV and training-load directly from your Polar
  device."

### 5.2 Migration-pending state (WHOOP today)

> **WHOOP setup is paused.** We're moving the WHOOP connection
> to a new backend. You'll see the connect button here once
> migration is live. Until then, you can upload a WHOOP
> export below.

This wording avoids implying WHOOP is broken (it isn't) or
that there's a user-side fix (there isn't until FS-008
ships). The export upload is the operational fallback.

### 5.3 Disconnected vs no-data distinction

When the source is connected but quiet, vs the source isn't
connected:

| State | Chip | Caption |
|---|---|---|
| Not connected | "needs setup" | (§ 5.1 connect button) |
| Connected, no data today | "live" | "No {metric} today from {Source}." |
| Connected, last sync >2 hours ago | "live · stale" | (§ 3.2 stale banner) |
| Connected, vendor returning errors | "connection error" | "Lauburu can't reach {Source} right now. Open the {Source} app to refresh." |

The `connection error` state is the only one that may use a
muted-error tone (orange dot, never red — red is reserved for
data-loss states).

## 6. Beginner vs veteran tone differences

| | Beginner | Veteran |
|---|---|---|
| Caption length | one short sentence | one sentence + provenance line |
| Vocabulary | "no data", "needs setup", "imported", "live" | adds "seed (X/7)", "via Apple Health", "stale", "low / medium / provisional" |
| Source list | Apple Health / Health Connect default visible; everything else under "More sources" | every source visible; provenance per row |
| Errors | one neutral sentence + one action | full source name + last-sync timestamp + retry button |
| Numbers | macros total only on nutrition; bucket name + chip on readiness | full per-metric breakdown + per-bucket confidence chip |

## 7. Edge cases

### 7.1 First-day user — no data anywhere

```
Welcome to Lauburu. Connect Apple Health (iPhone) or Health
Connect (Android) and your training data will appear here as
it syncs. You can start logging sessions and meals now —
those work without any external connection.
```

No coaching language. No empty bucket-rings. The Train tab
is the call-to-action.

### 7.2 Source connected but never actually used by user

After 14 days of zero data from a source the user connected,
the chip flips to `quiet` (not `stale`):

> **{Source} hasn't sent data in 14 days.** Open the {Source}
> app to make sure it's recording, or disconnect to remove
> this card.

### 7.3 WHOOP seed window mid-flight

```
WHOOP — seed (3 days of 7)
Recovery 64% · HRV 52 ms · last sync 8 min ago
We'll mark WHOOP as fully live once it has 7 clean days of
sync.
```

### 7.4 Conflicting data from two sources

If hub-routed Polar disagrees with WHOOP on RHR for the same
date:

| Beginner | Veteran |
|---|---|
| Show one number (the higher-fidelity source per source priority order) with provenance chip | Show both; "WHOOP 62 bpm · live" / "Polar 65 bpm · via Apple Health"; veteran can tap to mark which they trust for that day |

Source priority order (highest to lowest fidelity for RHR /
HRV / sleep): WHOOP-direct > Polar-direct > hub > manual.

## 8. Anti-rules

- **No "Looking good!" / "Great job!" anywhere.** The app is
  not a coach.
- **No medical / clinical language.** "Your CRP is high",
  "Sleep deprivation detected", "Possible overtraining" are
  banned.
- **No fabricated zeros or default values for missing data.**
  Always render "no data".
- **No truth-label hand-rolled in a UI string.** The six
  labels live in this doc; UI strings reference them, never
  invent new ones.
- **No localised "live" translations** until i18n ships. The
  English label is canonical; translations are a separate
  scoped task.
- **No removing the provenance chip to make a card look
  cleaner.** Chip is required.
- **No swapping `provisional` for `confident` to drive
  engagement.** Confidence ladders only go up after data
  earns them.

## 9. Cross-references

- `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` § 1, § 3.1, § 4
  (beginner vs veteran), § 5 (do-not-promote-yet).
- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` — truth-label
  formal definitions.
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` — readiness
  compute contract; copy here is the user-facing surface of
  that contract.
- `docs/CRONOMETER_IMPORT_FLOW.md` § 4 — Cronometer-specific
  subset of this doc lives there for convenience.
- `docs/MOBILE_UX_AUDIT_NEXT.md` — Codex Phase 1 mobile audit
  references this doc when proposing copy patches.
