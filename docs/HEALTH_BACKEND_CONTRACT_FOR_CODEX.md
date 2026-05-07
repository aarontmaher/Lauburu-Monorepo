# Health backend contract — Codex build reference

Single doc consolidating the Health/Nutrition/Readiness backend
contract Codex needs to build the mobile UI against. Pulls
together scattered detail from
`HEALTH_NUTRITION_READINESS_AUDIT.md`,
`HEALTH_CONNECTIVITY_TRUTH_SPEC.md`,
`HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md`,
`WHOOP_DIRECT_SETUP.md`, `POLAR_ACCESSLINK_PLAN.md`,
`CRONOMETER_IMPORT_FLOW.md`, and
`GRAPPLER_READINESS_PROTOTYPE_PLAN.md` into one Codex-facing
reference. Updated 2026-05-07 against
`CLAUDE-WHOOP-POLAR-ANDROID-HEALTH-BACKEND-SPEC-01`.

This is a **build reference**, not a re-derivation of the
specs. Where details exist in the parent docs, this doc cites
and summarises rather than duplicates. If the parent doc
disagrees with this one, the parent doc wins.

## 1. FS-008 — WHOOP migration approval card

| Field | Value |
|---|---|
| Candidate ID | FS-008 |
| Status | candidate, awaiting Aaron approval |
| Lane | 3 (DB + secrets) |
| Spec home | `docs/WHOOP_DIRECT_SETUP.md` § M |
| Audit row | `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` § 1.4.a |
| Default recommendation | **defer** until Codex's Phase 1 mobile audit (FS-007 + FS-010) ships |

### 1.1 What Aaron approves

A single bundled commit that:

1. Creates the `whoop_tokens` Supabase table per § M.2 step 2
   (RLS-gated, pgcrypto encrypted, `auth.uid() = user_id`
   policies).
2. Adds the `POST /api/integrations/whoop/callback` route to
   the Cloudflare Worker (mirror of the Railway callback).
3. Adds the token-refresh scheduled trigger
   (`cron: "*/30 * * * *"`).
4. Updates `docs/WHOOP_DIRECT_SETUP.md` § M to record the
   commit SHA + cutover-window dates.

This is a Lane-3 batch. Coders implement; Aaron approves the
final landing per rule 7.

### 1.2 What Aaron does at migration time

| # | Step | Where |
|---|---|---|
| 1 | Paste WHOOP client secret into the Worker via `wrangler secret put WHOOP_CLIENT_SECRET` | a one-off coder session that runs the command immediately |
| 2 | Update WHOOP developer-console redirect URI from the Railway URL to the new Cloudflare URL | https://developer.whoop.com → app settings |
| 3 | Verify the connect button + sync flow on his iPhone using the next paired build | TestFlight / app on iPhone |
| 4 | Approve `approved_done` line for FS-008 once §M.3 truth-label promotion conditions hold (≥7 days clean tokens, daily readings, tester confirmation) | text reply or Admin/Dev tap |

### 1.3 What changes after migration

| Surface | Before | After |
|---|---|---|
| Truth label for WHOOP-direct readings | `setup required` | `seed/provisional` for 7 days → `live` |
| Token storage | filesystem on Railway | Supabase `whoop_tokens` row, RLS-gated |
| OAuth callback URL | `…railway.app/api/integrations/whoop/callback` | `…workers.dev/api/integrations/whoop/callback` |
| Confidence ceiling for WHOOP-derived readiness | `confidence: low` (max) until clean | `confidence: medium` (max; `high` reserved) |

### 1.4 Defer / approve decision criteria

Approve **now** only if all of these hold:
- Codex's Phase 1 mobile audit (FS-007 + FS-010) is complete or
  out-of-bundle.
- Aaron has the WHOOP client secret to hand.
- Aaron has 30 minutes for the redirect-URI update + tester
  verification.
- The Cloudflare Worker has been redeployed with the freshness
  envelope (commit `8a393b7`) — done.

Otherwise **defer**. Until approved, FS-008 stays
`(awaiting Aaron approval)` and WHOOP truth label stays
`setup required`. The WHOOP raw export path (§ 1.4.c) covers
operational continuity in the meantime.

## 2. WHOOP migration — concise step list (Codex reference)

The full plan lives in `docs/WHOOP_DIRECT_SETUP.md` § M. The
single-page version Codex needs at build time:

1. **Aaron approves FS-008** (gate; nothing below is in scope
   without this).
2. **Supabase migration** — `whoop_tokens` table per § M.2 step
   2. Coder writes the migration SQL, applies via Supabase MCP
   `apply_migration` after Aaron approval.
3. **Worker route** — `POST /api/integrations/whoop/callback`
   in `cloudflare-worker/src/worker.ts`. Validates HMAC `state`,
   exchanges code → tokens, encrypts + upserts via pgcrypto.
   No log line includes the raw token. New unit tests in
   `cloudflare-worker/test/` cover happy path + state-expired +
   token-exchange failure.
4. **WHOOP dev-console redirect URI** — Aaron updates manually.
5. **Token refresh job** — Cloudflare scheduled worker
   (`wrangler.toml` `[[triggers]] crons`). Refreshes any token
   whose `expires_at` is within 2 hours.
6. **Mobile UI** — Codex updates the WHOOP card to read from
   the new Worker route. Truth label rendered from
   `whoop_tokens.row` `seed_until` or `live_since` field; copy
   per `HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 1 + § 5.2.
7. **Cutover window** — both Railway + Cloudflare callbacks run
   in parallel for 7 days. Old Railway routes deleted only
   after 7 days clean.
8. **Truth-label promotion** — only after § M.3 conditions all
   hold. Aaron writes the `approved_done` line.

Anti-rules (lifted from § M.5): no client secret in commits/
docs/UI; no redirect URI rotation without Aaron; no
`confidence: high` from WHOOP-direct data ever.

## 3. Android Health Connect source contract

Status: `live`. Platform default for Android. Hub aggregator —
reads from any registered third-party app that writes to
Health Connect (Garmin Connect, Polar Flow, Fitbit, MyFitnessPal,
Cronometer, Concept2 ErgData, ErgZone, Strava, etc.).

### 3.1 Per-metric mapping

What Lauburu reads from Health Connect today, with the truth
label and confidence ceiling each metric carries when surfaced.
Coders MUST NOT introduce metrics not on this list without a
doc commit.

| Metric | Health Connect data type | Truth label | Confidence ceiling | Notes |
|---|---|---|---|---|
| Resting heart rate | `RestingHeartRateRecord` | `synced from hub` | medium | Provenance label includes upstream app name (e.g. "Garmin via Health Connect") |
| Heart rate (timeline) | `HeartRateRecord` | `synced from hub` | medium | Per-second samples; downsampled to 1-min for storage |
| Heart rate variability (RMSSD) | `HeartRateVariabilityRmssdRecord` | `synced from hub` | medium | If only WHOOP-direct or Polar AccessLink-direct is also live, the direct source wins for HRV per § 5 priority |
| Sleep duration | `SleepSessionRecord` | `synced from hub` | medium | Stages from `stages` field if upstream populated |
| Sleep stages | `SleepSessionRecord.stages` | `synced from hub` | low | Stage detection accuracy varies by upstream app; ceiling is `low` |
| Workouts | `ExerciseSessionRecord` | `synced from hub` | medium | Upstream app name preserved in provenance |
| Active calories | `ActiveCaloriesBurnedRecord` | `synced from hub` | low | Estimated by upstream app; ceiling is `low` |
| Total calories | `TotalCaloriesBurnedRecord` | `synced from hub` | low | Same as above |
| Steps | `StepsRecord` | `synced from hub` | medium | |
| Body weight | `WeightRecord` | `synced from hub` | medium | Quarterly cadence at most for trend graphs |
| Nutrition (kcal / macros) | `NutritionRecord` | `synced from hub` | low | Provenance label cites upstream (Cronometer, MyFitnessPal, etc.) per `CRONOMETER_IMPORT_FLOW.md` |
| Hydration | `HydrationRecord` | `synced from hub` | low | Optional; surface only if user has hydration tracking on |

### 3.2 Permissions contract

Lauburu requests `read` permissions for the metrics in § 3.1
on first launch. If the user denies any permission, the
corresponding tile renders the "no data" state from
`HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 2.1 — never a
zero. Lauburu does not write to Health Connect.

### 3.3 Provenance label format (mandatory)

For Health Connect-routed data, the user-visible provenance
line follows
`HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 1.1 format:

```
{UpstreamAppName} via Health Connect · last sync {relative time}
```

Examples:
- `Garmin Connect via Health Connect · last sync 4 min ago`
- `Cronometer via Health Connect · last sync today`
- `Polar Flow via Health Connect · last sync 12 min ago`

If the upstream app name isn't available, fall back to:

```
Health Connect · last sync {relative time}
```

Anti-rule: never label hub-routed data as the vendor (no
"Polar live" when the data came via Health Connect, no
"Cronometer Direct" ever).

### 3.4 Multi-source conflict resolution

When two upstream apps write the same metric for the same
timestamp window, Lauburu uses the **most recently written**
record. The per-metric tile shows the upstream app name from
that record. Veterans see all sources in "More sources"
disclosure per `HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md`
§ 7.4.

## 4. Polar contract — hub vs AccessLink vs BLE

Three-way decision matrix. Each row is a Polar data path; each
column is a property Codex needs to know to wire the UI
correctly.

| Path | Status | Truth label | Where data flows | When user sees it | Confidence ceiling | Notes |
|---|---|---|---|---|---|---|
| **Polar via hub** (§ 1.3 of audit) | `live` | `synced from hub` | Polar device → Polar Flow app → Apple Health (iOS) / Health Connect (Android) → Lauburu | by default for any Polar user with Polar Flow installed | medium (whatever the underlying hub allows) | Provenance label "Polar Flow via Apple Health" / "Polar Flow via Health Connect" |
| **Polar AccessLink** (§ 1.5 + `POLAR_ACCESSLINK_PLAN.md`) | `planned` (FS-012) | `Polar Direct` (reserved) | Polar device → Polar Flow → AccessLink API → Worker route → Lauburu | only after vendor approval + § 1.5 ship + 7-day seed window | medium (`high` reserved) | Mirror of WHOOP Direct architecture; secrets via `wrangler secret put POLAR_CLIENT_*` |
| **Bluetooth HR strap** (§ 1.6 + `BLUETOOTH_MVP_SPEC.md`) | `planned` (FS-013) | `Bluetooth HR sensor` (never "Polar Direct" even if device is Polar) | Polar HR strap → BLE GATT 0x180D → mobile native code → train-session log only | only during a live training session; never readiness | NEVER eligible for readiness compute | Train-session lane only |

### 4.1 What Codex must NOT do

- **No "Polar Direct" UI label** until POLAR_ACCESSLINK_PLAN
  ships AND the seed window clears AND truth label flips to
  `live`. Until then the only Polar surface is "Polar Flow via
  Apple Health" / "Polar Flow via Health Connect".
- **No collapsing the three paths into a single "Polar"
  source.** Each path has its own card, its own provenance
  line, its own truth label.
- **No relabeling hub-sourced rows as `Polar Direct`** if the
  same user is also AccessLink-connected. The truth label
  captures provenance, not the user's vendor account state.
- **No reading BLE HR sensor data into the readiness compute
  ever.** Train-session only.

### 4.2 What Codex MAY do today

- Surface "Polar Flow via Apple Health" / "Polar Flow via
  Health Connect" provenance cleanly per § 3.3 (this is the
  only operational Polar path).
- Render a `setup required` chip for AccessLink (§ 1.5)
  that's hidden behind veteran "More sources" — beginners
  don't see it because the path isn't shipped.
- Render a "Pair Bluetooth HR sensor" affordance in Train tab
  that calls the (planned) BLE Phase 1 native scaffold.

### 4.3 Cross-source priority for the readiness compute

When multiple Polar-derived sources have data for the same
date, the compute uses the highest-fidelity path:

```
Polar AccessLink (live) > Polar via hub (any) > BLE HR (NEVER)
```

BLE HR is never an input to readiness regardless of priority.

## 5. Readiness gating

**v1 ships hub-first** per `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md`
§ "Priority — v1 is hub-first" (added 2026-05-07). The
table below shows full eligibility across all phases — v1
in particular reads only from Apple Health + Health Connect;
the "After P1" column applies once direct integrations clear
their seed windows. v1 confidence ceilings cap at `low`,
even where the table allows `medium` later.

Single per-source eligibility table for the Grappler Readiness
v1 compute. Pulls together
`HEALTH_NUTRITION_READINESS_AUDIT.md` § 3.1 (per-source
matrix) + § 6.2 (acceptance) +
`HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` § 4.4 (confidence
ladder).

| Source | Today | After P1 | Maximum confidence | Notes |
|---|---|---|---|---|
| Apple Health (iOS hub) | direct input | direct input | medium | platform default; never `high` until doc-commit promotion |
| Health Connect (Android hub) | direct input | direct input | medium | same |
| Polar via hub | input through hub | input through hub | medium | counts as part of hub provenance |
| WHOOP Direct (post-§M) | NOT eligible | eligible (`low` for 7 days, then `medium`) | medium (`high` reserved) | gated on FS-008 ship + § M.3 conditions |
| WHOOP API (vendor pull) | NOT eligible | tracks Direct | medium | same OAuth tokens as Direct |
| WHOOP raw export (CSV / zip) | NOT eligible | NOT eligible | NEVER | provenance ≠ freshness; uploaded summaries don't drive readiness |
| WHOOP seed window | NOT eligible | `low` only | low | enforced by compute, not by UI |
| Polar AccessLink | NOT eligible | eligible after § 1.5 ship + seed | medium (`high` reserved) | gated on FS-012 |
| Bluetooth HR (HRS GATT 0x180D) | NEVER | NEVER | NEVER | train-session only |
| Manual check-in (NextDayCheckin) | direct input (subjective bucket) | direct input | medium | hand-entered; truth label `live` (manual) |
| Generic conditioning — hub | hub-routed (load bucket) | hub-routed | medium | provenance label per § 3.3 |
| Generic conditioning — file import | NOT eligible | NOT eligible | NEVER | provenance label `imported summary` |
| Nutrition (manual + photo + targets) | NEVER | NEVER | NEVER | context only per `NUTRITION_TRACKING_PLAN.md` |
| Cronometer (hub-routed) | NEVER | NEVER | NEVER | nutrition is not readiness |
| Blood test uploads | NEVER | NEVER | NEVER | context only |
| DEXA uploads | NEVER | NEVER | NEVER | context only |
| Journal uploads | NEVER | NEVER | NEVER | evidence only; never appears in MCP either |

### 5.1 Compute-side enforcement

Readiness gating is enforced at the compute layer (the
Grappler Readiness service that produces the bucket-ring
output), NOT at the source-import layer. A source that's
"NEVER eligible" still flows into Lauburu's storage; the
compute simply doesn't read it. This separation lets veterans
view nutrition / blood / DEXA history alongside the readiness
buckets without the compute lying about its inputs.

### 5.2 Confidence ladder enforcement

| Confidence | Returnable today | Returnable after P1 | Returnable ever |
|---|---|---|---|
| `provisional` | yes (always — floor) | yes | yes |
| `low` | yes | yes | yes |
| `medium` | no (reserved) | yes (per § 5 source eligibility) | yes |
| `high` | no | no | NEVER returned by prototype until explicit doc-commit promotion |

Anti-rule: the readiness compute MUST hard-fail (or downgrade
to `provisional`) rather than return a value labelled with a
confidence tier its source eligibility doesn't support. No
silent upgrades.

## 6. Codex handoff

Drop-in prompt for the next Codex batch. Lane: mobile health
UI. Anti-overlap: Claude does not edit the same files in the
same session.

```
PROMPT-ID: CODEX-HEALTH-CONNECTIVITY-BUILD-PHASE-1-01
TYPE: CODEX
LANE: Mobile / Health connectivity build

MCP-FIRST: call project.get_current_state.

Reference: docs/HEALTH_BACKEND_CONTRACT_FOR_CODEX.md
(this doc — single source for the Health backend contract).

Phase 1 scope (this batch):

1. Audit apps/mobile/app/(tabs)/health.tsx,
   apps/mobile/src/components/HealthActionsPanel.tsx,
   apps/mobile/src/components/IntegrationCards.tsx,
   apps/mobile/src/services/health-source-ui.ts,
   apps/mobile/src/store/polar-store.ts.

2. Map every user-visible source-label string to one of the
   six canonical truth labels per
   docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md § 1. Flag
   any drift.

3. Apply Health Connect § 3 contract: every metric tile uses
   the per-metric mapping in § 3.1; provenance line follows
   § 3.3 format ("{UpstreamApp} via Health Connect"); missing
   data renders per § 3.2 (no zeros).

4. Apply Polar § 4 contract: three paths are visually
   separate; "Polar Direct" label HIDDEN until § 4.1
   conditions all hold; BLE HR affordance lives in Train tab,
   not Health tab.

5. Apply readiness gating § 5: any UI surface that displays a
   readiness bucket value must read the confidence chip from
   the compute output, never invent one. "NEVER eligible"
   sources never feed any readiness bucket UI.

6. Patches ≤20 lines / file. NO React redesign. NO worker
   route addition. NO migration. NO native rebuild. NO
   version bump. NO EAS build.

7. Status report opens with the rule-12 three-field block
   (MCP update attempted / Bridge snapshot run / Stale reason
   if blocked) per
   docs/BACKLOG_AUTOMATION_SYSTEM.md § "Coder report
   contract — rule 12".

8. Status sequence MUST be the four-string ladder
   (Implementation-complete → Agent-confirmed → Aaron-approved
   → Built/tester-ready). Never "fully complete".

Output:
- changed files (mobile copy patches only)
- mismatched source labels found per file
- four-status compliance per FS-XXX candidate
- recommendation for Phase 2 (only when Phase 1 lands)
- explicit statement: this batch did NOT request, recommend,
  or trigger an EAS build
- rule-12 three-field block at top of report
```

## 7. Anti-rules

- **No new direct integrations promoted by this doc.** WHOOP
  Direct gates on FS-008. Polar AccessLink gates on FS-012.
  BLE gates on FS-013. Each has its own approval gate; this
  doc is a build reference, not a promotion.
- **No `confidence: high` from any source ever in v1.**
- **No coaching language anywhere.** § 5 enforces this on the
  compute output; § 3 + § 4 enforce on the source surfaces.
- **No exposing personal health data via No-Auth MCP tools.**
  `integrations.get_overview` returns counts/flags only;
  per-user metrics require admin token.
- **No collapsing the three Polar paths into a single
  surface.** § 4.1 covers this.
- **No coder-side `live` label promotion.** Truth labels move
  via the explicit promotion conditions in WHOOP § M.3 +
  Polar § O.4 + audit doc § 1.4.d.
- **No introducing a metric not in § 3.1.** New metrics need
  a doc commit + approval.

## 8. Cross-references

- `docs/HEALTH_NUTRITION_READINESS_AUDIT.md` — the parent
  audit; § 1 per-source status, § 3.1 decision matrix, § 6.1
  acceptance.
- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` — formal truth
  label definitions.
- `docs/HEALTH_PROVISIONAL_AND_MISSINGNESS_COPY.md` — every
  user-visible string.
- `docs/WHOOP_DIRECT_SETUP.md` § M — full WHOOP migration
  plan.
- `docs/POLAR_ACCESSLINK_PLAN.md` — Polar AccessLink outline.
- `docs/BLUETOOTH_MVP_SPEC.md` — BLE Train-session lane.
- `docs/CRONOMETER_IMPORT_FLOW.md` — Cronometer hub-first
  spec.
- `docs/NUTRITION_TRACKING_PLAN.md` — nutrition is context.
- `docs/GRAPPLER_READINESS_PROTOTYPE_PLAN.md` — readiness
  compute spec.
- `docs/UNIFIED_MCP_PLAN.md` § 15 — write/read contract +
  auth model the Worker routes follow.
- `docs/PHONE_ONLY_AUTOMATION_PLAN.md` § 5 — Aaron's seven
  irreducible manual steps.
- `docs/CODER_LAPTOP_COMMANDS.md` — laptop commands coders
  run during the build.
- `docs/FEEDBACK_SUGGESTIONS.md` FS-008 / FS-012 / FS-013 —
  candidate gates.
