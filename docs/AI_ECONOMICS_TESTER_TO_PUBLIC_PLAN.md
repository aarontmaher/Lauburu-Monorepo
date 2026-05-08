# AI economics — tester-stage to public-stage plan

How AI cost flows are structured TODAY (tester / Aaron-only)
vs how they will flow at PUBLIC release. Cost-stage transition
plan that pairs with `docs/AI_SPEND_GATES_SPEC.md` (cost
classes + tiers) and `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md`
(cache reuse).

This is **doc only**. No app code. No EAS build.

## 0. Why two stages

The app's AI cost profile differs by audience:

- **Tester stage (today):** Aaron + a small tester group.
  Most AI work that's expensive should run **externally**
  (ChatGPT / Claude.ai / Gemini Aaron pastes into) so the
  app's monthly AI spend stays near zero. In-app cheap_ai
  + free_deterministic surfaces work as designed; expensive
  inference defaults to export-prompt.
- **Public stage (future):** users pay for an AI surface
  that runs in-app. Membership tiers + included credits +
  pay-as-you-go overflow per rule 22 § 4. The cache-reuse
  contract from rule 23 keeps per-user cost low even at
  scale.

This doc captures the policy + transition path. It does NOT
implement billing / Stripe / RevenueCat / etc. — those are
separate FS-XXX candidates at public-stage cutover.

## 1. Tester stage (today)

### 1.1 Default routing

Every AI request is classified per rule 22 cost class:

| Class | Tester-stage routing |
|---|---|
| `free_deterministic` | Run in-app. Always. |
| `cheap_ai` | Run in-app within tester monthly free tier (default 60 calls/h). Rate-limited; metered into the tester's `pro` tier monthly budget. |
| `expensive_ai` | Default action: **export-prompt** (rule 22 cost class 4 fallback). Aaron may explicitly choose `approve_in_app` per call. |
| `deep_research_external` | Always export-prompt (rule 22 § 1.4). Cached per rule 23 reuseKey. |

In other words: **at tester stage, the default for any
`expensive_ai` request is offload to external AI**, not
in-app spend. This keeps Aaron's monthly bill close to $0
while the app accumulates research artifacts for cache
reuse.

### 1.2 Why tester stage is offload-heavy

- Aaron is the only paying user. Burning $5–25/month on
  in-app inference vs $0 on external paste-and-import is
  pure gain.
- External AI surfaces (ChatGPT / Claude.ai) provide
  conversation context + side-by-side review that the
  in-app gate can't match.
- Imported results cache per rule 23 — same research
  artifact serves any future request with matching
  `reuseKey`. Tester-stage cache build is a long-term asset.
- Aaron's manual paste-and-import is one-tap per request —
  not a friction wall.

### 1.3 Tester-stage tier setting

In `AiSpendSettings`:
- Default `tier: 'pro'` for Aaron (his account).
- Default `defaultExportInsteadOfApprove: true` for
  `expensive_ai` (overrides rule 22's "default-defer" with
  "default-export-prompt" behaviour at tester stage).
- Pay-as-you-go: opt-in only.

For other tester accounts (girlfriend's Android, beta
testers): `tier: 'free'` by default. They get
`free_deterministic` only — sufficient for the audit-flow
testing pattern (`Maestro` + `audit-screenshots` +
`Admin/Dev` proof checklist).

### 1.4 What's NOT optimised at tester stage

- Pay-as-you-go billing flow (Stripe / RevenueCat / etc.)
  — out of scope until public stage.
- Per-user budget enforcement at the Worker layer — the
  Worker enforces rate-limits + cost classification, but
  monthly budget metering is a Supabase-side counter.
  Tester-stage counter is Aaron's only.
- Cohort / aggregate research artifacts — out of scope
  per FS-020 § 9.

## 2. Public stage (future)

### 2.1 Three-tier membership model

Per `docs/AI_SPEND_GATES_SPEC.md` § 4.1:

| Tier | Monthly | Includes | Best for |
|---|---|---|---|
| **free** | $0 | Deterministic only (no AI inference; export-prompt for any AI question). | Browsers / casual users. Full deterministic surface (FS-020 parser, FS-018 journal, MCP read tools, audit playbook capture). |
| **pro** | ~$5 / month | $5 of in-app `cheap_ai` + `expensive_ai` budget; 60 calls/h cheap rate; gates fire above threshold; PAYG opt-in. | Athletes who want in-app AI summarisation + style-evolution + AI video analysis. |
| **elite** | ~$25 / month | $25 of in-app budget; 240 calls/h cheap rate; default-approve for `expensive_ai`; PAYG default-on. | Coaches running athlete-memory synthesis across multiple students; high-throughput private coaching workflows. |

Pricing is illustrative — actual price discovery happens
at public-stage cutover; Aaron may vary by market /
geography / promotional period.

### 2.2 Pay-as-you-go overflow

When a tier hits its monthly cap, PAYG kicks in (per rule
22 § 4.2). Top-up flow: $10 minimum, $50/month hard cap
without explicit confirmation. Credits roll over within
the calendar year.

PAYG is the safety valve. Most pro / elite users won't hit
their cap; the cache-reuse contract (rule 23) keeps per-user
amortised cost low.

### 2.3 Cached artifact economics

Rule 23's research-artifact cache is the **public-stage
cost saver**. Per-user cache means:

- Same research request → cited cached artifact, no spend.
- Cohort sharing (FS-020 § 9 future): if multiple users
  ask the same generic question (e.g. "what is BPC-157?"),
  the answer is shared from a single cached artifact via
  the cohort surface. NOT in MVP.
- Tester-stage cache builds the seed corpus that public-
  stage users benefit from.

Anti-rule: cohort sharing requires opt-in + ≥50 user
threshold per FS-020 § 9. Per-user privacy floor (rule 22
§ 5) holds at public stage.

### 2.4 Free-tier deterministic surface

Free-tier users get the FULL deterministic surface:
- FS-020 journal-import parser (any source: Apple Notes /
  CSV / WHOOP / Cronometer / generic).
- FS-018 custom-journal Track-Something flow.
- Per-user pattern engine (rule 18 § 8 windowed analysis).
- Macro card + derived ratios (rule 22 § 7.2).
- Health Connect / Apple Health hub reads.
- Map exploration of `published` technique nodes.
- Verified-mastery layer (Forever Improve § Verified
  instructional mastery).
- Community contribution surface (Forever Improve §
  Community contribution / reputation).
- All `free_deterministic` MCP tools.

What free-tier users MUST upgrade or export-prompt for:
- Any `cheap_ai` or `expensive_ai` request.
- AI video analysis.
- Style-evolution synthesis.
- Athlete-memory long-form summary.
- Deep research export still works (free-tier users get
  the prompt; they paste into their own external AI).

Free is real, not a teaser — the deterministic + cache
surface is genuinely useful without paying.

## 3. Transition plan

The path from tester-only stage to public stage. Six
explicit gates.

| Gate | What's required | Owner |
|---|---|---|
| **G1. Tester-stage stable** | Aaron + tester group running for ≥30 days without cost spike (monthly AI bill ≤$5). Cache-reuse rate ≥40% (most repeat questions cite a cached artifact). | Aaron observation + bridge:snapshot writeback. |
| **G2. Approval gate UX shipped** | Rule 21 + 22 + 23 push gates fully operational on iPhone (per `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md`). Aaron approves / defers / denies from lock screen. Codex handoffs 1-5 in dependency order all shipped + verified. | Codex + Agent QA. |
| **G3. Per-user metering ready** | Supabase user_settings with `AiSpendSettings` schema + tier enforcement at Worker classify_ai_call layer. Per-user monthly counter accurate. | Codex (CODEX-FS-XXX-AI-SPEND-GATES-IMPL-01 ships this). |
| **G4. Billing integration** | Stripe / RevenueCat / similar. Tier upgrade flow + PAYG top-up flow. Receipts + invoices. | Codex; new FS-XXX. Approval-gated per rule 7 + rule 21. |
| **G5. Public-safe surface review** | Per `docs/CONNECTOR_SECURITY_MODEL.md` + rule 22 privacy floor: confirm no PII / token leak across the public-tier surface. AGENT_QA `gate: public_release_security_audit`. | Agent + Aaron approval. |
| **G6. Public release approval** | Rule 7 + rule 8 four-status sequence completed. Public release is itself an approval gate (rule 21). | Aaron explicit approval; rule 21 push gate. |

Each gate is a rule 21 approval-gated transition. Tester
→ public is NEVER auto-promoted; Aaron's explicit approval
+ AGENT_QA pass is required at each gate.

## 4. Monitoring (tester + public)

| Metric | Source | Tester target | Public target |
|---|---|---|---|
| Monthly AI bill | Supabase user_settings + Stripe | ≤$5 | Per-tier; PAYG covers spikes. |
| Cache reuse rate | research_artifacts.citationCount / research_jobs created | ≥40% | ≥60% at scale (cohort cache helps). |
| `expensive_ai` gate approval rate | gate_state_transitions where `to_state: approved` / total `expensive_ai` gates | track only | n/a |
| `deep_research_external` export rate | research_jobs `status: cached` / total | track only | n/a |
| Tier upgrade rate | user_settings.tier transitions | n/a | track when public |
| PAYG top-up frequency | payAsYouGoCreditsCents events | track only | < 1 per user / month average |
| Privacy-floor violations | redaction-test fails / logs | 0 | 0 |

These metrics are admin-token-gated; public surfaces show
counts only. No per-user identifying detail.

## 5. Anti-rules

- **No silent tier auto-upgrade.** Tier is always a
  deliberate user decision.
- **No raw user data to external AI without per-call
  approval.** Tester or public; rule 22 privacy floor
  holds.
- **No cohort sharing without opt-in + threshold.** FS-020
  § 9 territory; not in MVP.
- **No public release without Aaron's explicit gate
  approval per rule 7 + rule 8 + rule 21.**
- **No PII / token leak in any tier surface.** Same
  redaction layer as tester.
- **No deceptive free-tier framing.** Free is genuinely
  useful; not a 7-day-trial / nag-ware pattern.
- **No EAS build dispatched from this plan.** Plan informs
  build approval; doesn't trigger.

## 6. Codex handoff (already-staged dependencies)

The implementation handoffs that ship the tester→public
transition are already staged across the existing spec
docs. Listed in dependency order:

1. `CODEX-FS-XXX-AI-SPEND-GATES-IMPL-01`
   (`docs/AI_SPEND_GATES_SPEC.md` § 6) — ships tier
   classifier + per-call spend gate UX. Foundation for
   tester-stage tier defaults.
2. `CODEX-FS-XXX-DEEP-RESEARCH-OFFLOAD-IMPL-01`
   (`docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` § 7) — ships
   research_jobs + research_artifacts cache that powers
   cost-saver economics.
3. (Future) `CODEX-FS-XXX-PUBLIC-BILLING-IMPL-01` (NEW;
   not in this doc) — Stripe / RevenueCat integration for
   PAYG top-up + tier upgrade flow. Approval-gated for
   public-stage cutover.

This doc does NOT add a new handoff — it describes the
strategy the existing handoffs serve.

## 7. Cross-references

- `docs/AI_SPEND_GATES_SPEC.md` § 1 cost classes + § 4
  tier model + § 4.1 tier defaults + § 4.2 PAYG.
- `docs/DEEP_RESEARCH_OFFLOAD_SPEC.md` — research artifact
  cache + reuseKey hashing.
- `docs/HUMAN_APPROVAL_GATE_SPEC.md` — rule 21 state
  machine for tier-upgrade + billing gates.
- `docs/PUSH_APPROVAL_AUTOMATION_SPEC.md` — synthesis of
  push surfaces.
- `docs/JOURNAL_IMPORT_NORMALIZE_INSIGHTS_SPEC.md` § 9 —
  cohort aggregate territory (out of MVP).
- `docs/CONNECTOR_SECURITY_MODEL.md` — security model the
  public-stage release security audit references.
- `docs/OPERATING_RULES.md` § 7 (cost) / § 9 (provisional)
  / § 21 (gates) / § 22 (spend) / § 23 (research cache).
