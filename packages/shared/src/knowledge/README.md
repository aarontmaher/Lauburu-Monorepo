# Knowledge module

This module is the shared-first knowledge base for Lauburu's future non-technique AI.

It is intentionally narrow:

- `types.ts` defines the canonical knowledge document and retrieval schema
- `docs/` contains concise seeded knowledge chunks
- `load.ts` validates and normalizes those docs deterministically
- `query.ts` provides deterministic filtering for current app/backend callers

It does not provide:

- vector search
- science-paper ingestion
- pooled user-data summary generation
- live backend retrieval orchestration
- authoritative daily-cap counting
- checkout or purchase settlement

## Category boundaries

- `coaching_philosophy`: coaching stance and reasoning principles
- `non_technique_product_reasoning`: what evidence-aware/non-technique AI should mean
- `ai_policy_and_access_rules`: AI mode, gating, downgrade, and access semantics
- `monetization_rules`: included use, upgrade, pay-per-use, and access-policy framing
- `internal_product_decisions`: current product priorities and intended direction
- `app_feature_behavior`: verified app workflows and screen behavior
- `backend_truth_and_data_surfaces`: what current code/data can actually verify
- `repo_and_implementation_guidance`: safe-truth and implementation-boundary guidance

Use the narrowest category that preserves retrieval clarity. If a document spans multiple concerns, keep one primary category and use `subcategories`, `retrievalTags`, and `relatedFeatures` instead of inventing a hybrid category.

## Truth-status rules

- `implemented_truth`: verified from current repo code or an already-live shared/backend path
- `intended_direction`: product direction or policy shape that is not yet fully implemented
- `pending_backend`: expected future backend truth, not live today
- `context_only`: useful framing that should not be treated as system behavior
- `open_question`: unresolved issue or decision
- `deprecated`: keep only when retrieval still needs historical context

Keep `truthStatus`, `implementationStatus`, and `evidenceStrength` separate:

- `truthStatus` answers "how true is this right now?"
- `implementationStatus` answers "where is this wired today?"
- `evidenceStrength` answers "how strong is the supporting evidence?"

Do not mark backend-future capability as `implemented_truth` unless the repo actually contains the path that performs it.

## How to add or update docs safely

1. Add a small retrieval-friendly chunk under [`docs/`](./docs), not a long essay.
2. Verify every implementation claim against current repo code before using `implemented_truth`.
3. Prefer `product_intended` or `internal_reasoning_only` over overstating authority.
4. Use `doNotOverclaim` for known wording traps that future AI orchestration must avoid.
5. Export the doc from [`docs/index.ts`](./docs/index.ts) so there is one canonical seed list.
6. Run shared typecheck after changes.

## Future evolution

The next backend step should reuse this schema rather than replacing it:

- deterministic docs remain the canonical authored corpus
- vector indexing can attach via `vectorId` and a parallel semantic retrieval path
- science summaries can be added as reviewed `science` docs
- pooled user-pattern summaries can be added as aggregate `user_patterns` docs
- future orchestration can merge this shared corpus with private athlete memory without mixing the two stores today
