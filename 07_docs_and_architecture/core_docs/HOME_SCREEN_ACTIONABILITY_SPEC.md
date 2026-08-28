# Home screen actionability spec — P1

Status: spec, awaiting Aaron approval before implementation.
Repo-only. **No EAS / TestFlight / Play / production release.**

The home screen is currently information-rich (readiness band,
Today's Coach, WHOOP / Apple Health / nutrition chips) but the
"what should I do right now" affordance is implicit — users
have to read multiple cards and synthesise an action
themselves. This spec defines the contract for promoting one
clear actionable next step to the top of the home tab.

## 1. Anti-rules (non-negotiable)

These come from the existing Operating Rules and the readiness
truth spec. The actionable home screen MUST NOT violate any of
them.

- **No medical advice.** No "you should rest", "skip training
  today", "you are overtrained", "you are recovered". The only
  action labels allowed are functional: "Log fuel", "Open
  today's plan", "Sync Health Connect", "Manage sources".
- **No causation language.** "Your sleep last night caused…",
  "Because your HRV is low…" are banned per
  `docs/OPERATING_RULES.md` rule 9 + `docs/HEALTH_CONNECTIVITY_TRUTH_SPEC.md`.
- **Provisional readiness only** — every action that quotes a
  readiness number MUST also surface the confidence level
  (`provisional` / `low confidence` / `medium` / `high`) using
  the existing `ConfidenceBadge` primitive.
- **No fabricated next-action.** When no high-leverage action
  is computable (e.g. all sources are stale, readiness is
  provisional, no plan for today), the slot renders the literal
  string `'Nothing scheduled — when ready, train or log a
  session.'` rather than inventing a directive.
- **No EAS / TestFlight / Play / production release** triggered
  from the home screen. Any "build" / "deploy" surfaces stay
  on Admin/Dev (admin-only).

## 2. Top-of-screen actionable slot — contract

Sits ABOVE the readiness band (which stays as the second
visible card so users still see their score on every open).

### Computed inputs

| Field | Source | Anti-rule |
|---|---|---|
| `topAction.label` | Pure helper (see § 4) | ≤ 32 chars; functional verb-noun only ("Log fuel", "Open plan", "Sync Health Connect") |
| `topAction.detail` | Same helper | ≤ 90 chars; one sentence; never directive ("…to fill today's record" not "…or you'll be unrecovered") |
| `topAction.routeOrAction` | A `keyof ROUTES` or a callback | Must NOT navigate outside the app or trigger an EAS / Play / TestFlight surface |
| `topAction.confidence` | `ConfidenceLevel` from `_helpers.ts` | Mirrors the readiness compute layer — never overrides it |
| `topAction.dismissible` | boolean | When dismissed, the slot collapses for the rest of the day; resets on UTC midnight |

### Selection precedence (highest → lowest)

1. **Health-source setup blocker.** Any `SourceChip` rendering
   `'setup required'` for a source the user has previously
   connected is a P1 actionable — relink. Label:
   `'Reconnect <source>'`. Detail: the meta line from the
   Manage Sources sheet.
2. **Today's session not opened yet.** When the user has a
   training session scheduled for today (per
   `useTrainingScheduleStore`) and has not opened the plan
   tab in the last 12 hours: action `'Open today's plan'`,
   route `/(tabs)/train`.
3. **Fuel not logged before noon.** When local time is past
   noon and no nutrition entry exists for today: action
   `'Log fuel'`, route `/(tabs)/feedback` (or the dedicated
   nutrition entry screen if added).
4. **Pending coaching follow-up.** Existing
   `PendingFollowupBanner` already surfaces this — if active,
   it WINS over fuel/log items because the user already
   asked for it. Action: open the follow-up draft.
5. **No high-leverage action.** Render the literal copy
   `'Nothing scheduled — when ready, train or log a session.'`
   with no CTA button.

The selection helper MUST return null when EVERY check produces
a stale or provisional input — never invent a recommendation
from incomplete data.

## 3. UI rendering contract

- Use the existing `InsightCard` primitive (already shipped in
  commit `58c821a`) with:
  - `title` = `topAction.label`
  - `body` = `topAction.detail`
  - `accentColor` = the theme's accent green ONLY when
    `confidence === 'high'`; the slate-provisional colour
    otherwise.
  - `trailing` = a single primary `Pressable` whose label
    matches the action verb. No secondary buttons in the slot
    — the primary action is by definition singular.
- The slot has a fixed maximum height (≈ 96 dp) so it cannot
  push the readiness band off the first viewport.
- When `topAction === null`, render the slot empty (do NOT
  show a placeholder card — empty state is the readiness
  band moving up to first position).

## 4. Pure selection helper — `selectTopAction`

Lives at `apps/mobile/src/services/home-top-action.ts` (to be
created when Aaron approves the implementation batch).

```ts
export interface TopActionInput {
  sources: ReadonlyArray<{ id: string; sourceState: TruthLabel }>;
  todaySessionScheduled: boolean;
  lastPlanOpenAtMs: number | null;
  nowMs: number;
  fuelLoggedToday: boolean;
  pendingFollowupCount: number;
  readinessConfidence: ConfidenceLevel | null;
}

export interface TopActionOutput {
  label: string;
  detail: string;
  routeOrAction: string;
  confidence: ConfidenceLevel;
  dismissible: boolean;
}

export function selectTopAction(input: TopActionInput): TopActionOutput | null;
```

Pure: no React, no native imports, no clock side effects (clock
is injected via `nowMs`). Tested with the same fixture pattern
used by `lane-progress-summary.ts` /
`source-status-mapper.ts`.

## 5. Test contract

`cloudflare-worker/test/test-home-top-action-selection.ts` (to
land alongside the implementation). MUST cover:

- Each precedence rule (1..4) wins over the lower-numbered
  rules under the matching input.
- Rule 1 (setup-required blocker) wins over an active session
  scheduled for today (a missing source is more actionable
  than starting a session blind).
- All-stale / all-provisional inputs return `null`.
- Banned label strings (anything matching the medical-advice
  pattern from
  `cloudflare-worker/test/test-fs021-lactate-entry.ts`) are
  refused at the helper output (defence in depth).
- Confidence: a high-confidence readiness paired with a
  setup-required blocker still emits `confidence: 'high'`
  (the blocker is functional, not health-claimy).

## 6. Out of scope (explicit non-goals)

- No push notifications from the home screen — those live
  behind rule 21 (human approval gate) + rule 20 (all-idle
  notification).
- No coaching language, no AI calls. The selection helper is
  deterministic.
- No backend writes from the home screen — taps route to
  existing screens which own their own writeback.
- No EAS / build / deploy surfaces.

## 7. Cross-references

- `docs/OPERATING_RULES.md` § rule 9 (provisional health),
  rule 11 (MCP-first), rule 14 (parallel priorities),
  rule 24 ("Rule 1 — no idle lanes" — the lane-side
  equivalent of this user-side spec).
- `apps/mobile/src/components/primitives/InsightCard.tsx` —
  the rendering primitive.
- `apps/mobile/src/components/primitives/_helpers.ts` —
  `ConfidenceLevel` enum.
- `apps/mobile/src/components/primitives/SourceChip.tsx` —
  `'setup required'` source-state matching for precedence rule
  #1.
- `apps/mobile/app/(tabs)/index.tsx` — existing home-screen
  surface where the slot mounts.
