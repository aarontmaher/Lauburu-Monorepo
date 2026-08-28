# UI primitives integration guide

How to slot the eight design primitives shipped in
`apps/mobile/src/components/primitives/` into existing screens
without faking live data, breaking truthfulness rules, or
requiring a wholesale screen refactor.

This is the **integration guide**. Tokens live in
`apps/mobile/src/theme/index.ts`; primitives live in
`apps/mobile/src/components/primitives/`; pure helpers + tests
live alongside them.

## 1. Why integrate gradually

The premium dark-blue concept is the long-term direction; the
short-term anti-rule is "do not fake live data, do not claim
real-time readiness without supporting evidence." A wholesale
screen refactor risks both. The eight primitives below are
**additive** — they sit alongside existing styled rows and can
be slotted in row-by-row, tile-by-tile.

A new screen MUST NOT mix premium and legacy tokens. Pick one
and migrate the whole screen, or stay legacy until the screen
has been audited. The primitives carry their own minimal
StyleSheet so they render correctly even on a screen that has
not yet adopted the theme.

## 2. Primitives → screen slot map

| Primitive | Where to slot | Anti-rule |
|---|---|---|
| `StatusPill` | Generic status indicator anywhere a colored chip is needed. | Tone MUST come from a domain-aware mapper, not a literal — call `mapTruthLabelToTone` / `mapConfidenceToTone` from `_helpers.ts`. |
| `SourceChip` | Per-source rows in **HealthActionsPanel** `SourceSheetRow` (Health → Manage Sources sheet). | Pass only the canonical eight `TruthLabel` strings; never invent new phrasings. |
| `ConfidenceBadge` | Header of any metric / readiness card that has a confidence signal. | A `'high'` badge MUST NOT appear alongside a `seed/provisional` source chip; the readiness compute layer enforces this upstream. |
| `MetricCard` | Health tab top-of-screen tiles for HRV / RHR / sleep / strain. Replaces the existing inline `<View>` + manual `<Text>` blocks. | Caller passes pre-formatted `value` strings; missing values are the literal `'—'`. The card itself does no fallback formatting. |
| `FactorRow` | Inside the Grappling Readiness card to break down per-factor contribution. | Provisional/missing factors render as `'—'` in the value slot; the row never invents zeros or guesses. |
| `InsightCard` | The Coach card on the Health tab; the Recommendation feedback card on Feedback tab. | Body MUST be sanitised upstream — no medical advice, no causation language. |
| `ReadinessGauge` | The Readiness card on the Health tab. | Today's implementation is a static ring (no partial fill). Score `null` / non-finite renders as `'—'` with the provisional ring tone. When `react-native-svg` is added, the gauge upgrades to a partial-arc fill in a follow-up commit. |
| `TrendSparkline` | Compact per-metric trend below `MetricCard` values; daily-readiness shifts strip on the Readiness card. | Null entries render as 10%-tall placeholder bars in a faint tone — missing data must be visible, not invisible. |

## 3. Recommended migration order

1. **Manage Sources sheet** (lowest risk; the existing
   `SourceSheetRow` already computes a status text + status
   colour). Replace the inline `<Text>` status with
   `<SourceChip state={...} />`. Map the existing internal
   status enum to a `TruthLabel` first; never invent labels.
2. **Health tab top tiles** (MetricCard). Replace one tile at
   a time, starting with HRV / RHR (least conditional UI).
   Keep the existing fetch / availability code paths
   unchanged; only the rendering changes.
3. **Readiness card** (ReadinessGauge + FactorRow). Today the
   readiness compute returns a confidence level + per-factor
   contributions; route those into `score`, `confidence`, and
   the `FactorRow` list. Provisional readings render as
   `'—'` with the slate provisional ring.
4. **Coach card** (InsightCard). Title + body slot in
   directly; preserve the existing sanitised text upstream.
5. **AdminDev rows** (StatusPill). The lane heartbeat chip,
   the release-gate boolean tile, and the approval-gate
   row already use Pill-shaped chips inline; swap to
   `StatusPill` to reduce style drift. AdminDev intentionally
   stays functional rather than premium (per the prompt's
   anti-rule for admin-dev styling).

Each step is a separate commit. Anti-rule: do NOT bundle the
five steps together — installed-device QA should observe
ONE Health tab visual change at a time, not five.

## 4. Truthful readiness UI states

These are the canonical UI states the Readiness card
displays. The mapper from compute output → state lives in
the readiness service (`packages/shared/src/backend/services/
readiness/grappler-readiness.ts`); the card itself is pure
presentation.

| State | UI behaviour |
|---|---|
| **Seed / provisional** | `ReadinessGauge` with `confidence='provisional'`. Score may render as a number but the ring is slate, the badge says "provisional", and the FactorRow values use `seed/provisional` chips. |
| **Low confidence** | Score renders, ring is the band colour, badge says "low confidence". Caller MUST list at least one missing factor or the badge says "low confidence — coverage". |
| **Medium confidence** | Score renders, ring is the band colour, badge says "medium confidence". |
| **High confidence** | Score renders, ring is the band colour (only `'high'` band uses the accent green), badge says "high confidence". MUST be the only state where the readiness number is the visual headline. |
| **Missing data** | Score = null → `ReadinessGauge` renders `'—'` in the slate provisional ring. FactorRows render with `'—'` values + `missing` chips. The card MUST display a one-line reason: e.g. "No sleep data in the last 24h." |
| **Stale data** | Score renders but with a `stale` chip on every affected FactorRow + a top-of-card banner saying "Last reading > 12h ago — refresh sources to update." |
| **Post-training update** | Score recomputes after a Train session lands. The card flashes a brief `live` chip below the gauge for ~5 seconds, then settles back to the canonical confidence badge. |
| **Premium "Live Readiness Shifts"** (planned) | Reserved for a future Pro feature — daily intra-day shifts strip below the gauge. Today the strip is documented in this guide and rendered via `TrendSparkline` only on dev builds; production renders a "Pro feature — coming with paid tiers" placeholder. |

Anti-rules across all states:

- The **accent green** ring is reserved for `high` band + `high
  confidence`. Any other combination uses the band colour at
  reduced saturation OR the slate provisional colour.
- The card NEVER claims "your readiness is X" without showing
  the confidence badge at the same time.
- The card NEVER hides a `seed/provisional` chip; if any
  contributing source is provisional, the card says so.

## 5. UI/UX redesign backlog

Tracked in `docs/APP_DEVELOPMENTS.md` § Forever Improve. This
guide is the integration handbook for the primitives that
support the redesign; the prioritised backlog of which screens
get the redesign first lives in that doc.

Short index of what's deferred until later batches (each one
gated on Aaron approval + the existing rule-6 build-cost
guard):

- Bottom navigation refresh (deep-blue surface, larger touch
  targets, accent-green active indicator)
- Home tab card layout polish (use `MetricCard` for the
  primary tiles; collapse marketing copy)
- Map / Reference / Syllabus visual polish (pure card density
  + typography pass)
- Per-factor icons for the FactorRow component (requires an
  icon set — tracked separately)
- Partial-fill arc for the ReadinessGauge (requires
  `react-native-svg` install)

## 6. Anti-rules across the whole redesign

- No EAS build to ship just the primitives — they're pure
  React Native and ride into the next Aaron-approved bundled
  release.
- No premium colour applied to AdminDev rows that report
  adverse system state (drift / stale / no_writeback). Those
  rows MUST stay in the warning / danger tones from the
  legacy palette so they remain readable.
- No fake live data anywhere. Provisional readings render
  with the provisional ring; missing data shows `'—'` and
  surfaces the missing chip.
- No primitive may import from `apps/mobile/app/admin-dev.tsx`
  (or any other screen). Primitives are leaf components.
- No `react-native-svg` use until the dep is added in an
  explicit Aaron-approved EAS build.

## 7. Cross-references

- `apps/mobile/src/theme/index.ts` — tokens.
- `apps/mobile/src/components/primitives/` — the eight
  components + pure helpers.
- `cloudflare-worker/test/test-ui-primitives-helpers.ts` —
  pure-helper contract test.
- `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md` § 3 — the
  canonical six truth labels SourceChip wraps.
- `docs/MOBILE_NATIVE_CONTROL_CENTRE_SPEC.md` — the
  fresh/stale chip + safe write actions contract.
- `docs/GRAPPLER_READINESS_BUILD_PLAN.md` — provisional
  readiness compute + UI principles.
- `docs/PRODUCT_BRAIN_OVERNIGHT_ARCHITECTURE.md` § 6 — AI
  economics + premium tier model the partial-fill gauge
  unlocks.
- `docs/APP_DEVELOPMENTS.md` § Forever Improve — long-form
  redesign backlog.
