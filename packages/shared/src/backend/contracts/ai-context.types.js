"use strict";
/**
 * AI context response — the single unified shape the API AI layer
 * consumes for athlete reasoning.
 *
 * Includes every layer the AI needs:
 *   - source health (operational truth)
 *   - latest normalized metrics (deterministic, interpretation-free)
 *   - daily refresh artifact (interpreted, athlete-relative)
 *   - weekly synthesis artifact (interpreted, weekly rollup)
 *   - baseline profile + thresholds (slow-moving stable memory)
 *   - capability summary (seed/live mode, safe_for/not_safe_for)
 *
 * The AI MUST check `capability.notSafeFor` before generating
 * readiness, recovery, or strain claims. Missing WHOOP-native
 * fields are explicitly listed — never invent them.
 */
Object.defineProperty(exports, "__esModule", { value: true });
