# Source Authority Hierarchy

## Purpose
Defines which data sources are authoritative for which claims. Prevents the app from treating all inputs equally or allowing AI-generated content to override measured data.

## What Belongs
- Authority rankings per data domain (recovery, sleep, strain, technique, coaching)
- Fallback chains when primary sources are unavailable
- Rules for resolving conflicts between sources

## What Does NOT Belong
- Implementation details of specific integrations (those go in integration docs)
- API schemas or endpoint references
- User-facing copy or UI text

## Truth Status
Canonical. This document is the single source of truth for authority decisions.

## Stability
Stable. Changes only when a new data source is added or an existing source changes reliability.

## Update Cadence
On integration change only.

## Key Rules

### Authority Tiers (highest to lowest)

1. **WHOOP** — Authoritative for: recovery score, HRV, sleep performance, strain.
   - Device-measured, continuous, validated sensor data.
   - Always preferred when available.

2. **HealthKit** — Fallback for: sleep, heart rate, activity.
   - Used only when WHOOP data is unavailable or incomplete for a given metric.
   - Never overrides WHOOP when both are present.

3. **Manual entries** — Self-reported data (e.g., perceived soreness, notes, session logs).
   - Treated as subjective. Labeled as self-reported in any context where it is used.
   - Can supplement but never contradict device-measured data.

4. **Local coaching engine** — Deterministic rules applied to authoritative inputs.
   - Produces recommendations, not measurements.
   - Rules are transparent and auditable. No black-box logic.

5. **Shared memory from MCP** — Reviewed-only knowledge.
   - Content has been human-reviewed before entering shared KB.
   - Trusted for app philosophy and product context, not for athlete-specific claims.

6. **AI-generated content** — Never authoritative without review.
   - All AI outputs are advisory. They do not become truth until a human or a higher-tier source confirms them.
   - Must be labeled as AI-generated when surfaced to the user.

### Conflict Resolution
- Higher tier always wins.
- If WHOOP says recovery is 35% and a manual entry says "feeling great," both are shown but WHOOP drives the coaching recommendation.
- AI may reference lower-tier data but must not present it as equivalent to device-measured data.
