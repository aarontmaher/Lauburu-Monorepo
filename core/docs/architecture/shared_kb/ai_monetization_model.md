# AI Monetization Model

## Purpose
Documents the hybrid upgrade + pay-per-use AI access model. Clarifies what is built, what is wired, and what is placeholder.

## What Belongs
- Plan structure and included AI access
- Feature bucket definitions
- Pay-per-use rules
- Current implementation status (what works vs what is stubbed)

## What Does NOT Belong
- Pricing numbers (those live in config, not docs)
- Stripe/RevenueCat integration details
- UI copy for upgrade screens

## Truth Status
Partially implemented. Policy fields are populated in code. Enforcement and checkout are not wired.

## Stability
Unstable. This is an active design area. Expect changes as the product matures and real usage data arrives.

## Update Cadence
Frequently during monetization buildout. Stabilizes once checkout is live and caps are enforced.

## Key Rules

### Plan Structure
- Each plan tier includes a daily AI access allowance.
- Allowance covers core coaching features: readiness interpretation, training recommendations, technique suggestions.
- Higher tiers include more daily interactions and access to advanced features.

### Feature Buckets
- **Core coaching** — Protected. Always available within plan limits. Includes readiness, basic recommendations, technique reference.
- **Advanced analysis** — Pay-per-use beyond plan allowance. Includes deep recovery analysis, multi-week trend interpretation, detailed training load breakdowns.
- Bucket assignment protects core coaching from being gated behind per-use charges. A free user can always get basic guidance.

### Pay-Per-Use
- Applies to `advanced_analysis` bucket only.
- Triggered when daily included allowance is exhausted.
- User is informed before a paid interaction, not after.

### Current Implementation Status
- **Daily caps:** Type definitions exist. Values are populated per plan. Enforcement is NOT active — all users currently get unlimited access.
- **`remainingDailyAllowance`:** Always returns `'not_tracked_locally'`. The field exists in the type system but is never decremented.
- **Checkout:** Not wired. No purchase flow exists. Plan assignment is hardcoded or defaulted.
- **Feature bucket routing:** Logic exists to classify requests into buckets. No gating occurs based on the classification.

### Rules for Future Implementation
1. Never gate core coaching behind payment. A user with zero budget must still get basic readiness and training guidance.
2. Pay-per-use must be opt-in per interaction, not silent billing.
3. Daily cap reset is midnight in the user's local timezone.
4. If cap tracking fails or is unavailable, default to allowing access (fail open for coaching, fail closed for billing).
