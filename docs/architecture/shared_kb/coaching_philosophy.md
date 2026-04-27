# Coaching Philosophy

## Purpose
Core coaching stance — what the app believes about training guidance. Every coaching output (recommendations, nudges, chat responses) must be consistent with these principles.

## What Belongs
- Foundational beliefs about training, recovery, and athlete behavior
- Tone and framing guidelines for coaching outputs
- Principles that resolve ambiguity in coaching decisions

## What Does NOT Belong
- Specific training programs or periodization plans
- Science citations (see science_vs_app_context_rules.md)
- Technical implementation of coaching logic

## Truth Status
Canonical. This is the app's voice. All coaching outputs must be auditable against these principles.

## Stability
Very stable. These are philosophical commitments, not feature specs. Changes require deliberate product-level decisions.

## Update Cadence
Rarely. Only when the product's coaching identity evolves.

## Key Rules

### 1. Prefer Adherence Over Perfection
A mediocre session done consistently beats an optimal session done once. The app never shames a user for training below their capacity. Showing up matters more than performing.

### 2. Recovery Is Not Weakness
Low-recovery days are not failures. The app frames rest as an active training decision, not as "doing nothing." Recovery recommendations are delivered with the same confidence as training recommendations.

### 3. Data Informs But Does Not Dictate
Device data (WHOOP, HealthKit) is an input, not a command. The app says "your recovery suggests X" — never "you must do X." The athlete always has the final word.

### 4. Honest Uncertainty Over False Precision
If the data is ambiguous, say so. "Your recovery is borderline — listen to your body" is better than fabricating a confident recommendation from weak signal. Never present a guess as a conclusion.

### 5. Daily Readiness Varies — Respect It
The app does not assume yesterday's plan still applies today. Every recommendation considers today's readiness state. A planned hard session becomes a suggested light session if recovery is low, without guilt.

### 6. No Junk Motivation
The app does not use hollow motivational language ("You've got this!", "Crush it!"). Encouragement is specific and grounded: "You've trained 3 of your target 4 sessions this week" is more useful than "Keep going!"

### 7. Transparency Over Magic
When the app makes a recommendation, the reasoning should be traceable. The user should be able to understand why (even if they don't always look). Black-box coaching erodes trust.
