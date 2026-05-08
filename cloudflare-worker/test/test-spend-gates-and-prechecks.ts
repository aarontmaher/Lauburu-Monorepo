/**
 * Spend-gate + deterministic precheck contract.
 *
 * Locks in the rules in packages/shared/src/approval-gates/spend.ts
 * + spend-prechecks.ts:
 *   - makeSpendGate refuses missing or secret-shaped precheckSummary
 *   - approve / defer / cancel / complete / expire preserve
 *     spend-specific extras (triggerType, estimatedCostClass,
 *     precheckSummary, precheckRuleId)
 *   - exportSpendGatePrompt includes the precheck summary BEFORE
 *     the AI rationale and never leaks resolution metadata
 *   - precheckJournalImport flags only highly-ambiguous low-conf pastes
 *   - precheckReadinessAnomaly returns precheck_only when training /
 *     sleep / journal explains the drop
 *   - precheckHealthTrend returns precheck_only on sub-trigger or
 *     non-monotonic windows
 */

import {
  approveSpendGate,
  cancelSpendGate,
  completeSpendGate,
  deferSpendGate,
  expireSpendIfDue,
  exportSpendGatePrompt,
  isSpendGateActionable,
  makeSpendGate,
  precheckHealthTrend,
  precheckJournalImport,
  precheckReadinessAnomaly,
  type SpendGate,
} from '../../packages/shared/src/approval-gates';

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) {
    console.error(`✗ ${label}`);
    process.exit(1);
  }
}

const T0 = '2026-05-09T00:00:00Z';
const T_FUTURE = '2026-05-12T00:00:00Z';

function freshSpendGate(overrides: Partial<Parameters<typeof makeSpendGate>[0]> = {}): SpendGate {
  return makeSpendGate({
    id: 'spend-test',
    title: 'Approve AI re-read for readiness drop',
    reason: 'Today readiness dropped 18 pts; precheck found no explanatory signal. AI MAY phrase a one-line association.',
    triggerType: 'readiness_anomaly',
    estimatedCostClass: 'small',
    priority: 'P2',
    safeDefault: 'skip',
    createdAt: T0,
    expiresAt: T_FUTURE,
    precheckSummary: 'Readiness drop 18 pts vs baseline 72. Today 54. No deterministic explanatory signal.',
    precheckRuleId: 'precheck-readiness-anomaly-v1',
    ledgerActionId: null,
    actionPayload: 'Phrase a one-line association narrative for the readiness drop. Associations only; no causation.',
    ...overrides,
  });
}

// ── construction ─────────────────────────────────────────────────────

const okGate = freshSpendGate();
assert(okGate.status === 'pending', 'fresh spend gate is pending');
assert(okGate.actionType === 'mcp_write', 'underlying actionType is mcp_write');
assert(okGate.triggerType === 'readiness_anomaly', 'triggerType preserved');
assert(okGate.estimatedCostClass === 'small', 'estimatedCostClass preserved');

let threw = false;
try { freshSpendGate({ precheckSummary: '' }); } catch { threw = true; }
assert(threw, 'empty precheckSummary refused');

threw = false;
try { freshSpendGate({ precheckSummary: 'jwt eyJabcdefghij12.eyJklmnopq.qrstuvwxyz' }); } catch { threw = true; }
assert(threw, 'secret-shaped precheckSummary refused');

threw = false;
try { freshSpendGate({ safeDefault: 'notify_only' }); } catch { threw = true; }
assert(threw, 'mcp_write refuses notify_only safeDefault');

// ── transitions preserve spend extras ────────────────────────────────

const now = () => new Date('2026-05-09T01:00:00Z');

const approveResult = approveSpendGate(okGate, 'Aaron iPhone admin-dev', { now, note: 'OK to spend.' });
assert(approveResult.ok, 'pending → approved succeeds');
assert(approveResult.next.triggerType === 'readiness_anomaly', 'approve preserves triggerType');
assert(approveResult.next.estimatedCostClass === 'small', 'approve preserves estimatedCostClass');
assert(approveResult.next.precheckSummary === okGate.precheckSummary, 'approve preserves precheckSummary');
assert(approveResult.next.precheckRuleId === okGate.precheckRuleId, 'approve preserves precheckRuleId');

const deferResult = deferSpendGate(okGate, 'Aaron iPhone admin-dev', '2026-05-10T00:00:00Z', { now });
assert(deferResult.ok && deferResult.next.status === 'deferred', 'defer succeeds');
assert(deferResult.next.triggerType === 'readiness_anomaly', 'defer preserves triggerType');

const cancelResult = cancelSpendGate(okGate, 'automation:cancel', { now });
assert(cancelResult.ok && cancelResult.next.status === 'cancelled', 'cancel succeeds');
assert(cancelResult.next.precheckRuleId === 'precheck-readiness-anomaly-v1', 'cancel preserves precheckRuleId');

const completeResult = completeSpendGate(approveResult.next, 'automation:run', { now });
assert(completeResult.ok && completeResult.next.status === 'completed', 'approved → completed succeeds');
assert(completeResult.next.estimatedCostClass === 'small', 'complete preserves estimatedCostClass');

const past = () => new Date('2026-06-01T00:00:00Z');
const expireResult = expireSpendIfDue(okGate, { now: past });
assert(expireResult.ok && expireResult.next.status === 'expired', 'expireSpendIfDue fires past expiresAt');
assert(expireResult.next.triggerType === 'readiness_anomaly', 'expire preserves triggerType');

assert(isSpendGateActionable(okGate), 'pending spend gate is actionable');
assert(!isSpendGateActionable(approveResult.next), 'approved spend gate is not actionable');

// ── export prompt ────────────────────────────────────────────────────

const exported = exportSpendGatePrompt(okGate);
assert(exported.includes('Spend gate spend-test'), 'export names the gate id');
assert(exported.includes('readiness_anomaly'), 'export names the trigger');
assert(exported.includes('Precheck summary'), 'export includes the precheck heading');
const precheckIdx = exported.indexOf('Precheck summary');
const reasonIdx = exported.indexOf('Why AI was suggested');
assert(precheckIdx > 0 && reasonIdx > precheckIdx, 'precheck summary appears before AI rationale');
assert(exported.includes('safeDefault skip'), 'export reflects safeDefault');
assert(!exported.includes('Resolved'), 'export of pending gate does not include resolved metadata');

// Ensure the export of an approved gate also does not leak the
// resolution note (the export is a paste-into-ChatGPT shorthand, not
// an audit trail).
const approvedExport = exportSpendGatePrompt(approveResult.next);
assert(!approvedExport.includes('OK to spend.'), 'export does not include resolutionNote text');

// ── precheck: journal_import ─────────────────────────────────────────

const cleanImport = precheckJournalImport({
  totalRows: 12,
  needsConfirmationCount: 2,
  lowConfidenceCount: 1,
  highlyAmbiguous: false,
});
assert(cleanImport.verdict === 'precheck_only', 'clean import does not need AI');
assert(cleanImport.summary.includes('No medical advice'), 'journal precheck includes no-medical reminder');

const messyImport = precheckJournalImport({
  totalRows: 10,
  needsConfirmationCount: 8,
  lowConfidenceCount: 6,
  highlyAmbiguous: true,
});
assert(messyImport.verdict === 'requires_ai', 'highly ambiguous + many low-conf flags AI');
assert(messyImport.reasonForAi != null && messyImport.reasonForAi.includes('low-confidence'), 'reasonForAi names low-confidence');

// ── precheck: readiness_anomaly ──────────────────────────────────────

const noReadinessData = precheckReadinessAnomaly({
  todayScore: null,
  baselineScore: null,
  yesterdayStrain: 12,
  yesterdaySleepHours: 8,
  hasRelevantJournalEvent: false,
});
assert(noReadinessData.verdict === 'precheck_only', 'missing scores → precheck_only');

const smallDrop = precheckReadinessAnomaly({
  todayScore: 70,
  baselineScore: 75,
  yesterdayStrain: 10,
  yesterdaySleepHours: 8,
  hasRelevantJournalEvent: false,
});
assert(smallDrop.verdict === 'precheck_only', 'sub-trigger drop does not need AI');

const explainedDrop = precheckReadinessAnomaly({
  todayScore: 50,
  baselineScore: 70,
  yesterdayStrain: 18,
  yesterdaySleepHours: 8,
  hasRelevantJournalEvent: false,
});
assert(explainedDrop.verdict === 'precheck_only', 'big drop with high strain → precheck explains');

const unexplainedDrop = precheckReadinessAnomaly({
  todayScore: 50,
  baselineScore: 70,
  yesterdayStrain: 12,
  yesterdaySleepHours: 8,
  hasRelevantJournalEvent: false,
});
assert(unexplainedDrop.verdict === 'requires_ai', 'unexplained big drop suggests AI');
assert(unexplainedDrop.reasonForAi != null && unexplainedDrop.reasonForAi.toLowerCase().includes('multi-day pattern'), 'reasonForAi mentions multi-day pattern');

// ── precheck: health_trend ───────────────────────────────────────────

const flatTrend = precheckHealthTrend({
  metric: 'restingHr',
  windowDays: 14,
  earliestValue: 55,
  latestValue: 56,
  monotonic: true,
  significantDeltaAbs: 3,
});
assert(flatTrend.verdict === 'precheck_only', 'sub-trigger trend declines AI');

const wobbleTrend = precheckHealthTrend({
  metric: 'restingHr',
  windowDays: 14,
  earliestValue: 55,
  latestValue: 64,
  monotonic: false,
  significantDeltaAbs: 3,
});
assert(wobbleTrend.verdict === 'precheck_only', 'non-monotonic large delta declines AI');

const cleanShift = precheckHealthTrend({
  metric: 'restingHr',
  windowDays: 14,
  earliestValue: 55,
  latestValue: 64,
  monotonic: true,
  significantDeltaAbs: 3,
});
assert(cleanShift.verdict === 'requires_ai', 'monotonic large delta suggests AI');
assert(cleanShift.reasonForAi != null && cleanShift.reasonForAi.toLowerCase().includes('clinical interpretation'), 'reasonForAi forbids clinical interpretation');
assert(cleanShift.summary.toLowerCase().includes('no medical advice'), 'health trend precheck includes no-medical reminder');

console.log('spend-gates + prechecks contract test passed.');
