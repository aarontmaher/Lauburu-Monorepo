# Architecture: AI Knowledge & Memory Systems

Three clearly separated systems. Never mix them.

```
shared_kb/                    — app-wide non-personal truth
private_athlete_memory/       — one athlete's personal model
raw_source_layer/             — integration inputs, not interpreted truth
```

## Separation rules

| Data | Belongs in | Never in |
|------|-----------|----------|
| "Evidence-aware AI means X" | shared_kb | private_athlete_memory |
| "Aaron's HRV baseline is 62ms" | private_athlete_memory | shared_kb |
| "WHOOP recovery_score: 42" | raw_source_layer | private_athlete_memory (until processed) |
| "Coaching philosophy prefers adherence" | shared_kb | raw_source_layer |
| Chat history from a coaching session | nowhere (ephemeral) | shared_kb or private_athlete_memory |

## Build order

See [BUILD_ORDER.md](./BUILD_ORDER.md) for the first 15 artifacts and what each unlocks.

## Code modules

- Shared KB types + loader + query: `packages/shared/src/knowledge/`
- Private athlete memory types + builders: `packages/shared/src/athlete-memory/`
- Raw source adapter (WHOOP): `packages/shared/src/athlete-memory/whoop-adapter.ts`
