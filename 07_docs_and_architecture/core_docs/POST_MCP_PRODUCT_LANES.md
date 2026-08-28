# Post-MCP product lanes — what comes after the control centre stabilises

Once the MCP / Admin-Dev iPhone control centre is live and Aaron
can read project status from his phone without screenshots, the
next two product lanes line up. This doc sets the boundaries —
what each lane does, what it MUST NOT do, and what gates each
one before it can ship.

This doc is **spec only**. No app code or health source logic
changes from this commit.

Companion to:
- `docs/APP_DEVELOPMENTS.md` (active priority order; these are
  Priorities 2 and 4 in that doc)
- `docs/HEALTH_SOURCE_IMPLEMENTATION_AUDIT.md`
- `docs/HEALTH_METRIC_APPS_DEVICES_AUDIT.md`
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md`
- `docs/GRAPPLER_READINESS_BUILD_PLAN.md`
- `docs/CONTROL_CENTRE_MVP_SPEC.md` (the lane this gates on)

Updated 2026-05-07.

## Gate

Both lanes below are **gated** on the MCP / Admin-Dev iPhone
control centre being demonstrably useful from Aaron's phone.
Concretely: every check in `CONTROL_CENTRE_MVP_SPEC.md` § 6
"Phone test checklist" passes on a tester device. Until that
gate is true, work in this doc stays **spec only** — no UI,
no health-source surface changes, no readiness UI surface
changes.

## Lane A — Health / data source reliability

The first product lane after MCP/AdminDev. Apple Health on iOS
and Health Connect on Android are the two sources that two real
testers (Aaron + girlfriend) actually use day-to-day. Reliability
of those two paths is the Lane-A goal. Everything else is
secondary.

### Hard guardrails (preserved verbatim from APP_DEVELOPMENTS.md)

- **Apple Health is iOS-only.** Health Connect is
  Android-only. No cross-platform claims, no fake fallback.
- **Missing data stays missing.** No fabricated zeros, no
  invented connections, no smoothing over gaps.
- **No paid-tier gating** for the two primary platform
  sources. Already un-gated, commit `d4827ba`.
- **No new wearable integrations** until Lane A is reliable
  end-to-end. WHOOP / Polar / Garmin / Oura stay optional under
  "More sources" disclosure.

### Definition of "reliable" for Lane A

Aaron and girlfriend both achieve the following on their daily
device, with no app workaround required:

1. Open the Health tab → see a platform-specific source card
   (Apple Health on iOS, Health Connect on Android, never the
   wrong one).
2. The card states explicitly when a metric is missing rather
   than rendering 0 or hiding the row.
3. Sleep, recovery proxy (HRV / RHR), strain proxy (active
   energy / steps) update at least once per day after the
   user opens their respective vendor app.
4. Permission prompts only appear when permissions are not yet
   granted. After acceptance, no further prompts on subsequent
   opens for the same metrics.
5. WHOOP / Polar errors (if the user has those connected)
   surface a friendly error UI, not raw backend JSON. (Already
   landed via `friendlyDirectSyncError()` in commit `a036fd5`,
   shipping in the next paired tester build.)

### Out of scope for Lane A

- WHOOP / Polar OAuth migration off Railway disk. Tracked in
  `APP_DEVELOPMENTS.md` Priority 4 as a separate item; not
  blocking Lane A's iPhone+Android primary path.
- Nutrition tracking. Has its own plan
  (`NUTRITION_TRACKING_PLAN.md`).
- DEXA / blood-test uploads. Has its own plan
  (`DEXA_BLOOD_TEST_UPLOAD_PLAN.md`).
- Any health-source UI behind the Grappler Readiness prototype
  (Lane B, gated below).

### How Lane A surfaces in the iPhone control centre

Lane A does NOT add new fields to the Control Centre snapshot.
The control centre is for project / coder / build state. The
Health tab is the user-facing surface for Lane A. The two stay
separate so:

- A health regression doesn't make the dev surface look broken.
- A control-centre regression doesn't hide health data from
  testers.

When Aaron looks at his iPhone in the morning:

1. Admin/Dev tab tells him project state (Lane A's progress
   shows up as a backlog candidate / approved item, not as a
   live metric).
2. Health tab tells him whether his sources connected
   overnight. This is unchanged by Lane A — the priority is
   making the existing surface honest, not building new
   structure.

## Lane B — Grappler Readiness Batches B / C / D

The cautious provisional readiness prototype documented in
`GRAPPLER_READINESS_PROTOTYPE_PLAN.md`. **Gated** behind Lane A
being reliable: a readiness UI on top of unreliable health data
is worse than no readiness UI.

### Hard guardrails (preserved)

- **No Grappler Readiness UI ships until Batches B / C / D
  land.** Doc-only until the gate is open.
- **App-owned, not vendor-mirrored.** The reading is computed
  from the normalised metrics layer, not a passthrough of WHOOP
  recovery / Garmin Body Battery / Oura readiness.
- **Provisional by default.** Every reading carries a
  `provisional` label until Aaron has verified the prototype
  matches his subjective readiness across multiple training
  weeks. Confidence stays low/medium even when data is rich.
- **Missing direct WHOOP-native fields stay explicit.** When
  WHOOP raw isn't present, the UI says so — never substitutes
  a Lauburu-computed value for a vendor-native one without
  labelling.
- **Raw data is evidence, not coaching truth.** External source
  values are inputs; they don't become claims like "you're
  recovered" or "skip training today" without explicit
  provisional language.

### Batches B / C / D scope (recap)

Per `APP_DEVELOPMENTS.md` Priority 4 and
`GRAPPLER_READINESS_PROTOTYPE_PLAN.md`:

| Batch | Schema / UI | Scope |
|---|---|---|
| B | Extend `NextDayCheckin` sliders | Add soreness, mood, perceived fatigue. Pure schema + slider UI. No backend, no readiness compute change. |
| C | Extend `TrainingSession` schema | Add gi/no-gi, drilling vs live minutes, perceived intensity. Pure schema. |
| D | Bucket-ring UI on `AthleteStateStrip` | Show all 5 buckets (autonomic, sleep, load, grappling, subjective) with provenance per bucket — provenance must include "missing" when the source isn't available. |

### Seed / provisional indicators (required)

Every readiness reading rendered to a tester must carry:

- A status chip: `provisional` (default), `confidence: low`,
  `confidence: medium`. `confidence: high` is reserved and
  never returned by the prototype until Aaron explicitly
  promotes it via doc commit.
- A provenance line per bucket naming the metric source
  (`apple_health` / `health_connect` / `whoop_oauth` /
  `polar_oauth` / `manual` / `missing`). When `missing`,
  the bucket is rendered grey with the literal label
  "no data".

### Out of scope for Lane B

- Real-time push of readiness updates. The prototype computes
  on app open; no background workers.
- Any third-party AI provider call. Readiness is deterministic
  from the normalised metrics layer (`packages/shared/src/backend/services/readiness/grappler-readiness.ts`).
  Paid AI integration is gated separately
  (`AI_PROVIDER_STRATEGY.md`).
- Feature-flag gating. Lane B ships behind owner-only access
  first; expand to all testers only after Aaron sees ≥4 weeks
  of provisional readings that match subjective experience.

## Lane interaction matrix

| Question | Lane A answers | Lane B answers |
|---|---|---|
| "Did my Apple Health sync overnight?" | yes | no — Lane A surfaces this |
| "Should I train hard today?" | no — that's Lane B's question, gated | yes (provisional) |
| "Is my HRV trend declining?" | no — raw data only | yes (provisional, with provenance) |
| "Why is my readiness 'medium' today?" | no | yes — must show bucket provenance |
| "Why is one of the source cards missing?" | yes | no — Lane B never hides the gap, surfaces "no data" |

## Anti-rules (apply to both lanes)

- **No coupling Lane A and Lane B in code.** A Lane-A
  improvement (e.g. Apple Health permission prompt UX) MUST
  NOT touch readiness compute, and vice versa.
- **No marketing-style copy.** Both lanes ship with hedge
  language ("provisional", "may be missing", "based on
  available data") in the user-facing strings.
- **No shipping Lane B before Lane A is reliable.** A red flag
  is "shipping readiness UI on a build where the tester's
  Apple Health card is intermittently invisible." That's a
  no-ship.
- **No retention of raw WHOOP / Polar payloads in any Lauburu
  table the user can't delete.** Vendor data follows the
  existing `source_connection_state` model; readiness reads
  the normalised layer.

## What unblocks each lane

Lane A unblock conditions:

1. The control centre Phase-3 mobile UI ships per
   `CONTROL_CENTRE_MVP_SPEC.md`.
2. Aaron and girlfriend both confirm Phase 6 phone-test
   checklist passes on their devices.
3. Aaron writes an `approval_active` line on the FS-006
   candidate in `docs/FEEDBACK_SUGGESTIONS.md`.

Lane B unblock conditions:

1. Lane A unblock conditions all met.
2. Lane A reliability has held for ≥2 tester-build cycles
   without a regression that hides health data.
3. Aaron explicitly approves a "Lane B Batch B kickoff"
   candidate in `docs/FEEDBACK_SUGGESTIONS.md`.

Until those conditions, this doc is the only place Lane A or
Lane B work lives. Coders MUST refuse to start either lane
without the approval lines above, even when nudged by an audit
or a tester request.
