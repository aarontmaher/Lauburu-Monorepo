# Evidence-aware AI definition

## Purpose
Defines what "evidence-aware" means in this app's non-technique AI.

## What belongs here
- The four evidence buckets: science, user_patterns, internal_context, app_context
- What each bucket means and what grounding it provides
- How the app declares requested grounding in AI request packets

## What does NOT belong here
- Athlete-specific data or baselines
- Raw WHOOP/health metrics
- Technique reference content

## Truth status
Implemented — the evidence-aware AI service exists in `apps/mobile/src/services/evidence-aware-ai.ts` and builds structured packets with policy metadata.

## Stability
Stable definition. Bucket names are part of the typed contract.

## Update cadence
Review quarterly or when a new evidence bucket is added.

## Key rules
- The four buckets are contract declarations, not live retrieval sources yet
- `science_required: true` does not mean science retrieval is wired
- `include_user_pattern_data: true` does not mean pooled data exists
- Local context (readiness, sessions, preferences, progress) IS real device data
- Policy resolution (tier gating, mode downgrade) IS deterministic and correct
