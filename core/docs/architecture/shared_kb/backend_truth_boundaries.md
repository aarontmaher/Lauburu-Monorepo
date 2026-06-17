# Backend truth boundaries

## Purpose
Maps what is real/implemented vs. typed scaffolding awaiting backend wiring. The most important shared KB document for AI prompt framing.

## What belongs here
- Explicit lists of implemented vs. planned vs. provisional capabilities
- Rules the AI must follow when framing responses

## What does NOT belong here
- Athlete-specific data
- Implementation details that change weekly

## Truth status
Implemented — verified against current repo code.

## Stability
High churn. Must be re-verified against repo every 2 weeks.

## Update cadence
Every time a feature moves from scaffold to live.

## Key rules
### Implemented today
- Tier/capability model (4 tiers, cumulative)
- AI policy resolver (deterministic, on-device)
- Coaching engine (deterministic, no model calls)
- Health pipeline (HealthKit → CoachingResponse)
- Evidence-aware AI packet (structured request via Share.share)
- Reference progress (local, schema v2)

### Typed but NOT implemented
- Daily usage tracking (remainingDailyAllowance always 'not_tracked_locally')
- Pay-per-use checkout (button is a no-op)
- Backend AI inference (MCP coaching endpoint does not exist)
- Vector search (vectorId always null)
- Science retrieval (declaration only)
- Pooled user data (declaration only)
- Server-side tier verification (local-only)

### Rules for AI prompt framing
1. Never display usage counts without a real counter
2. Never claim daily enforcement when none exists
3. Never treat Share.share() as an API call
4. Never present MCP endpoint behavior as current capability
5. Always check truthStatus on knowledge documents before use
