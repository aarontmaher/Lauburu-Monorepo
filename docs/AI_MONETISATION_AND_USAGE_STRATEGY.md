# AI monetisation and usage strategy — design only

Authoring rule: nothing in this document changes runtime behaviour.
No Stripe products are created, no IAP entitlements are wired, no
paid LLM calls are made. The intent is to fix the shape of how paid
LLM usage is metered, billed, and capped so that when implementation
begins the choices are already made and the wiring is reviewable.

Companion to `docs/AI_PROVIDER_STRATEGY.md` (which fixes the
provider boundary). This doc fixes the **money** boundary.

Updated 2026-05-05.

## Why this doc exists now

Tester auto-update is end-to-end on iOS and one-Play-Console-pass
away on Android. Before the first paid LLM call lands, the
monetisation shape needs to be settled so:
- credits/tokens are tracked from day one (no retroactive accounting),
- safety caps exist before a runaway prompt loop costs real money,
- tier boundaries are clear so paid-tier features don't leak to free.

Implementation is gated. See `docs/AI_PROVIDER_STRATEGY.md` for the
"only when X, Y, Z are true" triggers. This doc adds the equivalent
billing triggers below.

## Tier shape (proposed)

Three tiers. Names are placeholders until store-listing copy lands.

### `free` — current default

- All deterministic features: Lauburu Readiness, Grappler Readiness,
  multi-window trends, structured Coach answers, all training and
  health imports.
- Coach answers are templated (no LLM narrative paragraph).
- No long-term reasoning calls.
- Health imports unlimited (cost is on the user's device, not on us).

Free tier is the baseline. It must remain genuinely useful — not a
nag-screen for upgrades. If the deterministic answer is empty for a
free user, the answer is "we don't have enough data yet", not "you
need to upgrade".

### `member` — monthly subscription

- Everything in `free`.
- Daily Coach answer is augmented with a single short LLM narrative
  paragraph (`chat` tier model, mid-cost).
- Athlete memory candidates auto-promoted on a slower cadence.
- Higher per-day question cap than free (free has a soft cap to
  prevent abuse; member's cap is generous enough that a normal user
  never sees it).
- Includes a small monthly bucket of `deep` calls (long-history
  trend questions). Bucket size is an explicit number, e.g. 20 deep
  calls/month, NOT "unlimited".

### `member_plus` — pay-as-you-go credits on top of member

- Member tier required (no standalone PAYG).
- Credits buy additional `deep` calls beyond the monthly bucket, plus
  any future heavy features (e.g. one-shot training-block design,
  multi-month review packets).
- Credits never expire month-to-month within the active subscription;
  forfeit on cancel.
- Refunds: only via store-native refund channels (App Store / Play),
  never via custom refund code.

## Billing channel

App Store / Play Store IAP only. No web checkout, no Stripe direct.
Reasons:

1. iOS reviewers reject web-checkout for digital goods inside the app.
2. IAP gives us tax handling, refunds, and family-share for free.
3. Store-managed subscriptions remove a whole class of fraud and
   chargeback work.

Server-side: an `entitlements` row keyed on the user's Supabase user
id, source-of-truth fields fed by App Store Server Notifications V2
and Google Play Real-time Developer Notifications. The mobile app
does NOT decide entitlement — it asks the backend.

PAYG credit packs are also IAP consumable products. Backend ledgers
the credit balance; mobile renders it.

## Per-feature usage buckets

The provider is metered per task class (matches
`docs/AI_PROVIDER_STRATEGY.md`):

| Bucket | Provider method | What it powers | Cost class |
|---|---|---|---|
| `deep` | `provider.deep` | Long-history trend questions, multi-window synthesis, "compare cardio vs strength weeks", training-block design | high |
| `chat` | `provider.chat` | Daily Coach narrative paragraph, daily summaries, structured-card augmentation | medium |
| `classify` | `provider.classify` | Question domain detection, feedback triage, deletion-request flagging, memory-candidate extraction | low |

Each bucket has its own cap and accounting:

- **Per-user per-day token cap.** Hard ceiling in the backend. Once
  hit, further requests fall back to the deterministic path.
- **Per-user per-month credit cap** (member tier). Once hit on
  `deep`, the user sees "this answer used your monthly deep budget;
  buy a credit pack or wait until next cycle". `chat` keeps running.
- **Per-account per-day GLOBAL cap.** Site-wide kill-switch in case
  of abuse or runaway loop — disables `deep` for all users for the
  rest of the calendar day, alerts owner.
- **Per-request token cap.** Hard ceiling on prompt + response size
  per call. Prevents a single pathological question from burning a
  month of budget.

## Pricing math (placeholder, NOT to be quoted to users)

Goal: each tier's expected monthly LLM cost stays well below the
subscription price, with margin for store fees, infra, and headroom.

Reference cost assumptions (rough, must be re-measured at integration
time — see `docs/AI_PROVIDER_STRATEGY.md`):
- `chat` average call: ~3k input + ~600 output tokens
- `deep` average call: ~12k input + ~1.5k output tokens
- `classify` average call: ~500 input + ~100 output tokens

Per-tier expected monthly volume (placeholder, validate after a
real cohort exists):
- Free: 0 LLM calls (deterministic only).
- Member: ~30 chat/month (1/day with skips), ~20 deep/month
  (the bucket).
- Member+: same as member + whatever PAYG credits buy.

Margin rule: tier subscription price ≥ 3× expected per-user LLM cost
at the cap, after store fees. If a price doesn't clear that bar, the
cap shrinks before the price moves.

## Cost guardrails (must exist before first paid call)

1. **Per-user per-day token cap** — backend-enforced.
2. **Per-account global daily cap** — backend-enforced kill-switch.
3. **Per-request token cap** — refuse oversize prompts before the
   provider call.
4. **Trend-keyword detection picks the cheapest viable tier.** The
   `isTrendQuestion()` classifier in `build-coach-answer` already
   exists; reuse it to keep `deep` reserved for genuine long-history
   asks.
5. **No retry on 429.** Token-rate or budget rejections short-circuit
   to the deterministic path. Do not loop, do not back off into more
   spend.
6. **Logging policy** (per `AI_PROVIDER_STRATEGY.md`): token counts
   and latency only, never bodies. Cost telemetry must be privacy-
   safe.

## Tier-store integration (mobile side)

Mobile already has a `tier-store` (`apps/mobile/src/store/tier-store.ts`).
Today it's a stub. The contract for the LLM rollout:

- `tier-store` reads server-authoritative entitlements from
  `/api/me/entitlements` (route to be added) on app launch and on
  resume.
- Components NEVER hard-code tier checks. They ask the store for
  capability flags: `canUseLlmCoach`, `canUseDeepTrendsLlm`,
  `creditBalance`. The store maps tier → capabilities; UI depends on
  capabilities, not tier names. This keeps tier renames local.
- "Upgrade" CTAs only appear where the user is actively trying to
  use a paid capability. Never on the home screen, never as a
  background nag.

## When the user runs out

Hard caps must degrade gracefully:

- Daily token cap hit → next Coach call returns the deterministic
  answer with a one-line note "Daily AI budget reached; full
  narrative resumes tomorrow." No upgrade prompt — they're already
  paying.
- Monthly `deep` bucket exhausted on `member` → "Long-history
  question used your monthly deep budget. Buy a credit pack or wait
  until {{cycle_reset}}." Single CTA to credit-pack purchase.
- Global kill-switch active → "AI Coach narrative paused; structured
  answers still working." No CTA — the user can't fix this.

## What this doc does NOT cover

- Specific prices (set at integration time once unit cost is
  measured against a real cohort).
- Specific store product IDs (created in App Store Connect and Play
  Console at integration time, not before).
- Anonymous / aggregated cross-user LLM calls (separate
  consent-gated track per `AI_PROVIDER_STRATEGY.md`).
- Coach memory architecture beyond "memory candidates ride on the
  same artifacts boundary as everything else".
- Refund flows beyond "store-native only".

## Triggers to begin implementation

In addition to the AI provider triggers (`docs/AI_PROVIDER_STRATEGY.md`):

1. App Store and Play subscription products created in their
   respective consoles, in DRAFT, with the agreed tier names.
2. Server-side `entitlements` table designed and migrated (Supabase
   RLS aligned with the user's own row).
3. App Store Server Notifications V2 + Play RTDN webhook endpoints
   stubbed and signature-verified, even before any product is
   purchasable.
4. An explicit "go" prompt that names the implementation batch (e.g.
   "Wire member-tier IAP and entitlements behind a feature flag,
   no `member_plus` yet").

Until all four AND the AI provider triggers are met, this doc is
specification, not a backlog ticket.
