/**
 * AI spend gate — a specialised approval gate that pauses on
 * "is this AI call worth the cost?". Reuses the lifecycle
 * machinery in ./index.ts so the same Approve / Defer / Cancel /
 * Complete / Expire transitions apply.
 *
 * The shape adds two fields the generic gate doesn't carry:
 *
 *   - triggerType    — what kind of automation surfaced the gate
 *                      (e.g. journal_import, readiness_anomaly,
 *                      health_trend, custom).
 *   - estimatedCostClass — an opaque enum coders set without
 *                      knowing exact pricing: 'micro' < 'small' <
 *                      'medium' < 'large' < 'xl'. Mapping to
 *                      $/cents is intentionally not in repo —
 *                      the model name and prompt size matter more,
 *                      and pricing changes upstream more often
 *                      than we want to track.
 *
 * Deterministic precheck copy lives in ./spend-prechecks.ts so
 * automation can produce a non-AI summary FIRST and only fall
 * through to a paid AI call when the precheck says the question
 * actually needs LLM reasoning.
 */

import {
  approveGate as approveBaseGate,
  cancelGate as cancelBaseGate,
  completeGate as completeBaseGate,
  deferGate as deferBaseGate,
  expireIfDue as expireBaseGate,
  isActionable as isBaseActionable,
  looksLikeSecret,
  makeApprovalGate,
  type ApprovalGate,
  type ApprovalSafeDefault,
  type ApprovalTransitionResult,
  type ApprovalPriority,
  type ApprovalStatus,
} from './index';

export type SpendTriggerType =
  | 'journal_import'
  | 'readiness_anomaly'
  | 'health_trend'
  | 'coach_question'
  | 'custom';

export type SpendCostClass = 'micro' | 'small' | 'medium' | 'large' | 'xl';

export interface SpendGate extends ApprovalGate {
  /** Always 'mcp_write' on the underlying ApprovalGate so the
   *  approval-gate machinery treats it as a write-class action. */
  triggerType: SpendTriggerType;
  estimatedCostClass: SpendCostClass;
  /** Short label of the deterministic precheck output. The agent
   *  must surface this BEFORE asking for spend approval. */
  precheckSummary: string;
  /** Optional pointer to the precheck rule id so the spend gate
   *  can be linked back to the rule that triggered it. */
  precheckRuleId: string | null;
}

export interface SpendGateInput {
  id: string;
  title: string;
  reason: string;
  triggerType: SpendTriggerType;
  estimatedCostClass: SpendCostClass;
  priority: ApprovalPriority;
  safeDefault: ApprovalSafeDefault;
  createdAt: string;
  expiresAt: string;
  precheckSummary: string;
  precheckRuleId?: string | null;
  ledgerActionId?: string | null;
  /** Optional sanitised prompt-export shorthand for "what would
   *  the AI call do if approved." ≤ 400 chars. */
  actionPayload?: string | null;
}

const PRECHECK_MAX = 400;

function trimAndCap(value: string, max: number): string {
  return value.replace(/\s+/g, ' ').trim().slice(0, max);
}

export function makeSpendGate(input: SpendGateInput): SpendGate {
  const precheckSummary = trimAndCap(input.precheckSummary, PRECHECK_MAX);
  if (!precheckSummary) {
    throw new Error('spend gate precheckSummary required — every spend gate carries a non-AI deterministic summary');
  }
  if (looksLikeSecret(precheckSummary)) {
    throw new Error('spend gate precheckSummary looks secret-shaped — refusing to construct');
  }
  const base = makeApprovalGate({
    id: input.id,
    title: input.title,
    description: input.reason,
    priority: input.priority,
    actionType: 'mcp_write',
    safeDefault: input.safeDefault,
    createdAt: input.createdAt,
    expiresAt: input.expiresAt,
    ledgerActionId: input.ledgerActionId ?? null,
    actionPayload: input.actionPayload ?? null,
  });
  return {
    ...base,
    triggerType: input.triggerType,
    estimatedCostClass: input.estimatedCostClass,
    precheckSummary,
    precheckRuleId: input.precheckRuleId ?? null,
  };
}

function preserveExtras(base: ApprovalTransitionResult, source: SpendGate): { ok: boolean; reason: string; next: SpendGate; ledgerNote: string | null } {
  // Carry only the spend-specific fields forward — never spread the
  // whole source gate or the base.next.status will be overridden.
  return {
    ok: base.ok,
    reason: base.reason,
    next: {
      ...base.next,
      triggerType: source.triggerType,
      estimatedCostClass: source.estimatedCostClass,
      precheckSummary: source.precheckSummary,
      precheckRuleId: source.precheckRuleId,
    },
    ledgerNote: base.ledgerNote,
  };
}

export function approveSpendGate(gate: SpendGate, resolver: string, options?: { now?: () => Date; note?: string | null }) {
  return preserveExtras(approveBaseGate(gate, resolver, options), gate);
}
export function deferSpendGate(gate: SpendGate, resolver: string, deferUntil: string, options?: { now?: () => Date; note?: string | null }) {
  return preserveExtras(deferBaseGate(gate, resolver, deferUntil, options), gate);
}
export function cancelSpendGate(gate: SpendGate, resolver: string, options?: { now?: () => Date; note?: string | null }) {
  return preserveExtras(cancelBaseGate(gate, resolver, options), gate);
}
export function completeSpendGate(gate: SpendGate, resolver: string, options?: { now?: () => Date; note?: string | null }) {
  return preserveExtras(completeBaseGate(gate, resolver, options), gate);
}
export function expireSpendIfDue(gate: SpendGate, options?: { now?: () => Date }) {
  return preserveExtras(expireBaseGate(gate, options), gate);
}
export function isSpendGateActionable(gate: SpendGate): boolean {
  return isBaseActionable(gate);
}

/**
 * Sanitised prompt-export shorthand. Returned to the AdminDev
 * "Export prompt" button so Aaron can paste the question into
 * ChatGPT manually, deciding whether to spend AI tokens
 * out-of-band. The export deliberately contains the precheck
 * output FIRST so a reader sees the deterministic answer before
 * the LLM-shaped question.
 */
export function exportSpendGatePrompt(gate: SpendGate): string {
  const ageHours = (() => {
    const t = new Date(gate.createdAt).getTime();
    if (!Number.isFinite(t)) return null;
    return Math.round((Date.now() - t) / 3_600_000);
  })();
  const lines: string[] = [
    `Spend gate ${gate.id} — ${gate.priority} ${gate.triggerType} (cost: ${gate.estimatedCostClass})`,
    gate.precheckRuleId ? `Precheck rule: ${gate.precheckRuleId}` : null,
    `Precheck summary (deterministic, no AI):`,
    gate.precheckSummary,
    `\nWhy AI was suggested:`,
    gate.description,
    gate.actionPayload ? `\nProposed AI action:\n${gate.actionPayload}` : null,
    ageHours != null ? `\nGate age: ~${ageHours}h. expiresAt ${gate.expiresAt} → safeDefault ${gate.safeDefault}` : null,
    `\nAnti-rules: do not paste raw user health values; do not include tokens or device IDs; pasted answer is suggestion only — installed-device QA gate still applies.`,
  ].filter((line): line is string => line != null && line.length > 0);
  return lines.join('\n');
}

export type SpendGateStatus = ApprovalStatus;
