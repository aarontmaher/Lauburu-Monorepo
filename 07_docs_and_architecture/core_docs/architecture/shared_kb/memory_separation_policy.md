# Memory Separation Policy

## Purpose
Enforces separation between shared KB, private athlete memory, and raw source data. Prevents cross-contamination that would break privacy, correctness, or product reasoning.

## What Belongs
- Definitions of each memory tier
- Rules for what goes where
- Prohibited crossings

## What Does NOT Belong
- Database schemas or storage implementation details
- Retention policies or GDPR compliance procedures (those are separate concerns)
- Specific content of any memory tier

## Truth Status
Canonical. Violations of this policy are bugs.

## Stability
Stable. The tiers are structural. Rules within tiers may be refined.

## Update Cadence
When a new memory tier or data flow is introduced.

## Key Rules

### Memory Tiers

| Tier | Contains | Scope | Example |
|------|----------|-------|---------|
| **Shared KB** | Non-personal app truth | All users, all sessions | Coaching philosophy, source authority rules, product behavior docs |
| **Private Athlete Memory** | One athlete's learned model | One user, persistent | Personal baselines, injury history, training preferences, goals |
| **Raw Source** | Integration inputs | One user, ephemeral-to-stored | WHOOP API responses, HealthKit samples, manual entry payloads |
| **Chat History** | Conversation context | One session, ephemeral | Messages in the current coaching chat |

### Prohibited Crossings

1. **Never store personal baselines in Shared KB.**
   A single athlete's HRV baseline, training frequency, or injury status is private. It does not belong in app-wide knowledge.

2. **Never store app philosophy in Athlete Memory.**
   Coaching philosophy, authority hierarchy, and product behavior rules are shared KB. Putting them in athlete memory creates per-user divergence in app behavior.

3. **Never treat raw data as interpreted truth.**
   A WHOOP API response is raw. The recovery score derived from it (by WHOOP) is interpreted. The coaching recommendation derived from the score (by the app) is a further interpretation. Each layer is distinct.

4. **Never persist chat history as memory.**
   Chat is ephemeral context. If something from chat needs to be remembered, it must be explicitly promoted to athlete memory through a defined mechanism — not silently absorbed.

5. **Never let AI write directly to Shared KB.**
   AI can propose updates. A human reviews and commits. Shared KB is reviewed-only (see source_authority_hierarchy.md).

### Data Flow Direction
```
Raw Source --> Private Athlete Memory (after processing)
Raw Source --> Coaching Engine (real-time, not stored as memory)
Private Athlete Memory --> Coaching Engine (read)
Shared KB --> Coaching Engine (read)
Coaching Engine --> Chat (output, ephemeral)
Chat --> Private Athlete Memory (explicit promotion only)
```
