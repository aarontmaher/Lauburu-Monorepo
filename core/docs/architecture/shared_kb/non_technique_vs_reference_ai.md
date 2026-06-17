# Non-Technique AI vs Reference AI

## Purpose
Separates technique reference (position/technique lookup) from non-technique AI (coaching, recovery, evidence-aware reasoning). These are distinct product surfaces with different data needs and goals.

## What Belongs
- Boundary definitions between the two AI domains
- What data each domain owns and what it shares
- Product goals per domain

## What Does NOT Belong
- Prompt engineering details or model configuration
- UI layout specifications
- Monetization rules (see ai_monetization_model.md)

## Truth Status
Canonical. Defines the boundary; both sides must respect it.

## Stability
Stable. The boundary is architectural. Individual features within each domain change more frequently.

## Update Cadence
When a new AI feature is added that could blur the boundary.

## Key Rules

### Reference AI (Technique Domain)
- **Owns:** Position data, technique descriptions, transitions, submissions, sweeps, escapes.
- **Lives on:** The Reference screen.
- **Goal:** Fast, accurate lookup. "What is this position? What are my options from here?"
- **Data sources:** GrapplingMap graph data, technique metadata from MCP.
- **Does not do:** Training recommendations, recovery advice, scheduling, coaching tone.

### Non-Technique AI (Coaching Domain)
- **Owns:** Recovery interpretation, training load management, adherence tracking, scheduling, coaching guidance.
- **Lives on:** Home screen coaching surfaces, chat, readiness views.
- **Goal:** Contextual, honest guidance. "Should I train today? What should I focus on?"
- **Data sources:** WHOOP, HealthKit, manual entries, athlete memory, shared KB coaching philosophy.
- **Does not do:** Technique instruction, position identification, graph navigation.

### Shared Data (Read-Only Bridge)
- Both domains can read **readiness data** (recovery score, sleep, strain).
- Reference AI uses readiness only to inform which techniques to surface in coached recommendations (e.g., avoid high-intensity guard passing drills on low-recovery days).
- Non-technique AI uses readiness to drive all coaching logic.
- Neither domain writes to the other's data store.

### Routing Rule
- If a user question is about "what technique" or "how to do X" — Reference AI handles it.
- If a user question is about "should I," "how much," "when," or "why am I tired" — Non-Technique AI handles it.
- If ambiguous, Non-Technique AI handles it and may link to Reference for technique detail.
