# AI provider strategy — design only

Authoring rule: nothing in this document changes runtime behaviour
yet. No paid API calls are wired. No provider choice is exposed to
users. The intent is to establish the architecture so that when paid
LLM calls are added later, the wiring is already correct and the
boundary between cached artifacts and live model calls is well
defined.

Updated 2026-05-05.

## Why this doc exists now

Tester auto-update on iOS is wired end-to-end. Android tester
auto-update is wired up to "upload as DRAFT" — full auto-promote
arrives once Aaron does the one-time Play listing pass and flips
`releaseStatus` to `'completed'`. Implementation should NOT begin
until Android full auto-promote is confirmed.

When that lands, the next safe build-out is the AI side. This doc
captures the design so the implementation is a thin, reviewable
batch.

## Provider order

1. **OpenAI only at start.** Single dependency, single env var, single
   billing path. All real LLM calls in production go through this
   provider until cost and reliability are characterised.
2. **Claude (Anthropic) and Gemini behind the same interface.** Add
   later only when there's a concrete reason (price/quality/latency,
   per-task tuning). Don't ship multi-provider as a feature; it's a
   resilience and cost knob.
3. **No user-facing provider choice** at any point in the next two
   release cycles. Provider is a backend implementation detail.

## Provider interface

A single shared interface, with one method per task class:

```ts
// packages/shared/src/backend/services/ai/provider.ts (future)
export interface AiProvider {
  /** "deep" — research synthesis, multi-window trend analysis,
   *  complex reasoning. Cap usage. Higher latency, higher cost. */
  deep(input: DeepInput): Promise<DeepOutput>;

  /** "chat" — daily Coach answers, daily summaries. Bounded prompt
   *  size; structured artifacts only. */
  chat(input: ChatInput): Promise<ChatOutput>;

  /** "classify" — short-context routing/extraction (feedback type,
   *  question domain, simple yes/no). Smallest model. */
  classify(input: ClassifyInput): Promise<ClassifyOutput>;
}
```

The first concrete implementation, `OpenAiProvider`, will pin:
- `deep` → GPT-5.5 (or whatever the current top reasoning model is
  on the OpenAI namespace at integration time). Used for "analyse my
  long-term trends", "what changed since 2023", "compare cardio vs
  strength weeks".
- `chat` → mid-tier model. Used for the standard `/coach/ask` daily
  flow.
- `classify` → cheapest available. Used for question
  domain detection, feedback triage, deletion-request flagging.

Each call site picks a method based on what it actually needs — the
provider does not auto-choose a tier.

## What the model receives

Strict separation:
- The model **never** sees raw provider data (raw WHOOP records,
  individual HealthKit samples, raw CSV rows).
- The model **does** see structured cached artifacts:
  - normalised daily metrics (already a deterministic boundary)
  - per-window trend summaries (7 / 14 / 30 / 90 / 180 / 365 / all-time)
  - long-term baseline summary (mean / sd / p10 / p50 / p90)
  - Lauburu Readiness output
  - Grappler Readiness output (when implemented)
  - athlete memory candidates
  - feedback labels and triage outcomes

Boundary phrased as a pipeline:

```
raw source
  → normalised daily metrics (deterministic)
  → interpreted artifacts (deterministic, cached)
  → athlete memory (slow-changing, manually promotable)
  → AI provider call (read-only over the artifacts)
```

This keeps the LLM cost bounded by artifact size, not by how many
days of raw data the user has imported.

## What's already in place (no AI calls live yet)

- Multi-window trends bundle on `/coach/ask` aiContext:
  `trends_short_7d / 14d`, `trends_medium_30d`, `trends_long_90d /
  180d / 365d`, `trends_all_time`, `data_coverage`,
  `long_term_baseline`, `memory_candidates`, `context_size`.
- Lauburu Readiness compute:
  `packages/shared/src/backend/services/readiness/lauburu-readiness.ts`.
- Grappler Readiness compute:
  `packages/shared/src/backend/services/readiness/grappler-readiness.ts`.
- Build-coach-answer module: composes structured answer cards from
  the artifacts above. Today these run **without an LLM** —
  deterministic templated output. Adding an LLM provider is a swap
  of the answer composer, not a re-architecture.

## Implementation order (when unblocked)

1. **`packages/shared/src/backend/services/ai/provider.ts`**: types
   and interface only. No concrete provider yet.
2. **`OpenAiProvider`** behind `process.env.OPENAI_API_KEY`. Lives
   on the chat-app server only — never on the mobile app.
3. **Integration into `build-coach-answer`**: an optional `provider`
   parameter. When omitted, the existing deterministic path runs
   (preserves current behaviour, keeps a no-LLM fallback for cost
   spikes / outages). When provided, the LLM produces a single
   short narrative paragraph appended to the existing structured
   sections.
4. **Tier-store integration**: paid tiers gain access to longer LLM
   answers. Free tier sees the deterministic templated answer
   (current state) — never a "you need to upgrade" empty state.
5. **Cost guards**: per-day per-user token cap, dropped to deep tier
   only when the request explicitly asks for "long-term" / "all
   history" / etc. (the trend-keyword detection already exists in
   `build-coach-answer`).

## What stays no-API

The owner-side workflow (Admin/Dev panel, prompt library, status
fetch, GitHub Actions dispatch, EAS submit, release sync) does not
need any LLM provider. It stays no-API regardless of whether paid
LLM is wired for end users.

## Secrets

When `OpenAiProvider` is added, the secret model is:
- `OPENAI_API_KEY` lives on Railway env only. Never in the mobile
  app, never on EAS env, never in GitHub Actions secrets.
- The mobile app calls `/coach/ask` as it does now. The chat-app
  backend is the only thing that touches OpenAI.
- Logging policy: log token counts and request latency, never
  request bodies and never response bodies (those contain user
  health context). Already aligned with the `aiContext.context_size`
  field.

## What this doc does NOT cover

- Specific model name pins (will land in code at integration time —
  pinning here would go stale).
- Pricing budgets (depend on tester volume — measure once a real
  cohort exists).
- Streaming UX (later — first land non-streaming responses).
- Multi-provider fallback / cost-based routing (deferred until at
  least two providers are actually integrated).
- Anonymous cross-user / aggregate trends (separate consent-gated
  privacy track; outside the scope of provider choice).

## Triggers to begin implementation

Implement only when ALL three are true:
1. Android full auto-promote is proven (one workflow dispatch lands
   a COMPLETED Internal Testing release with no Play Console click).
2. iOS Build 15+ has shipped via TestFlight with the standing UX
   bundle (so we have a stable mobile baseline before introducing
   LLM variability into Coach answers).
3. There's an explicit "go" prompt that names the implementation
   batch (e.g. "Wire OpenAiProvider behind a feature flag, deep tier
   only").
