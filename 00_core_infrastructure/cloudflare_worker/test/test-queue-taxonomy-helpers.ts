/**
 * Contract tests for scripts/queue-taxonomy-helpers.mjs.
 *
 * Pins the 4-queue taxonomy + classifier rule order + P0/P1
 * protection per docs/QUEUE_TAXONOMY_SPEC.md.
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-queue-taxonomy-helpers.ts
 */

import * as assert from 'node:assert/strict';
// @ts-expect-error — helpers are .mjs (no .d.ts).
import {
  QUEUE_KINDS,
  LANE_OWNERS,
  RISK_LEVELS,
  classifyQueueItem,
  shouldRecommendToIdleLane,
  staleThresholdHours,
  isItemStale,
  riskFromAction,
} from '../../scripts/queue-taxonomy-helpers.mjs';

// -- QUEUE_KINDS + LANE_OWNERS + RISK_LEVELS shape -----------

assert.deepEqual(
  [...QUEUE_KINDS].sort(),
  ['app_functionality', 'app_ux_ui', 'audit', 'automation_workflow', 'data_readiness_evidence', 'human_approval', 'overnight', 'release_qa_gate'].sort(),
  'eight queue kinds defined (4 original + audit + human_approval + release_qa_gate + data_readiness_evidence)',
);
assert.deepEqual(
  [...LANE_OWNERS].sort(),
  ['aaron', 'agent', 'claude', 'codex'].sort(),
  'four lane owners defined',
);
assert.deepEqual(
  [...RISK_LEVELS].sort(),
  ['high', 'irreversible', 'low', 'medium'].sort(),
  'four risk levels defined',
);

// -- classifyQueueItem: explicit tag wins --------------------

{
  const r = classifyQueueItem('[automation] keep MCP fresh');
  assert.equal(r.queue_kind, 'automation_workflow');
  assert.equal(r.lane_owner, 'claude');
  assert.equal(r.matchedRule, 'explicit_tag');
}
{
  const r = classifyQueueItem('[ux] dark theme rollout');
  assert.equal(r.queue_kind, 'app_ux_ui');
  assert.equal(r.lane_owner, 'agent');
}
{
  const r = classifyQueueItem('[functionality] FS-022 something');
  assert.equal(r.queue_kind, 'app_functionality');
  assert.equal(r.lane_owner, 'codex');
}
{
  const r = classifyQueueItem('[overnight] long synthesis run');
  assert.equal(r.queue_kind, 'overnight');
  assert.equal(r.lane_owner, null);
}
{
  const r = classifyQueueItem('[audit] FS-022 functional confirmation');
  assert.equal(r.queue_kind, 'audit');
  assert.equal(r.lane_owner, 'agent');
}
{
  const r = classifyQueueItem('[approval] EAS Android v22 build approval');
  assert.equal(r.queue_kind, 'human_approval');
  assert.equal(r.lane_owner, 'aaron');
}
{
  const r = classifyQueueItem('[release-gate] v21 build retest');
  assert.equal(r.queue_kind, 'release_qa_gate');
}
{
  const r = classifyQueueItem('[evidence] Apple Health sample ingestion');
  assert.equal(r.queue_kind, 'data_readiness_evidence');
  assert.equal(r.lane_owner, 'codex');
}

// -- classifyQueueItem: lane hint via opts -------------------

{
  const r = classifyQueueItem('arbitrary title', { laneHint: 'app_ux_ui' });
  assert.equal(r.queue_kind, 'app_ux_ui');
  assert.equal(r.matchedRule, 'lane_hint');
}

// -- classifyQueueItem: keyword matches ----------------------

{
  const r = classifyQueueItem('Improve MCP freshness writeback');
  assert.equal(r.queue_kind, 'automation_workflow');
  assert.equal(r.matchedRule, 'automation_keyword');
}
{
  const r = classifyQueueItem('Migrate Health tab to MetricCard primitive');
  assert.equal(r.queue_kind, 'app_ux_ui');
  assert.equal(r.matchedRule, 'ux_keyword');
}
{
  // After the data_readiness_evidence queue addition, "lactate entry"
  // is recognised as evidence-corpus content (correctly — the lactate
  // value is evidence, not feature code). The functionality-queue
  // route is reserved for items like "FS-021 lactate entry UI panel"
  // where the title clearly references UI / feature scope.
  const r = classifyQueueItem('FS-021 lactate entry validator');
  assert.equal(r.queue_kind, 'data_readiness_evidence');
  assert.equal(r.matchedRule, 'evidence_keyword');
}
{
  const r = classifyQueueItem('FS-021 training tab UI');
  assert.equal(r.queue_kind, 'app_functionality');
  assert.equal(r.matchedRule, 'functionality_keyword');
}
{
  const r = classifyQueueItem('Overnight athlete-memory synthesis cron');
  assert.equal(r.queue_kind, 'overnight');
  assert.equal(r.matchedRule, 'overnight_keyword');
}

// -- classifyQueueItem: rule order — automation beats ux when both keywords --

{
  // "MCP" (automation) wins over "polish" (ux) per § 3 rule order.
  const r = classifyQueueItem('MCP polish for Admin/Dev');
  assert.equal(r.queue_kind, 'automation_workflow');
}

// -- classifyQueueItem: rule order — approval > audit > automation --

{
  // "approval" wins over "audit" wins over "MCP".
  const r = classifyQueueItem('EAS build approval after MCP audit');
  assert.equal(r.queue_kind, 'human_approval', 'approval keyword wins');
}
{
  // "audit" wins over "MCP" when there is no approval keyword.
  const r = classifyQueueItem('Recurring drift check on MCP freshness');
  assert.equal(r.queue_kind, 'audit', 'audit keyword wins over automation');
}

// -- classifyQueueItem: audit-queue keyword matches ----------

{
  const r = classifyQueueItem('Spec consistency audit for FS-022');
  assert.equal(r.queue_kind, 'audit');
  assert.equal(r.matchedRule, 'audit_keyword');
}
{
  const r = classifyQueueItem('Bug report: HC permission dialog never appears');
  assert.equal(r.queue_kind, 'audit');
}
{
  const r = classifyQueueItem('Suggestion-escalation from user feedback');
  assert.equal(r.queue_kind, 'audit');
}

// -- classifyQueueItem: human_approval keyword matches -------

{
  const r = classifyQueueItem('Worker deploy approval');
  assert.equal(r.queue_kind, 'human_approval');
  assert.equal(r.matchedRule, 'approval_keyword');
}
{
  const r = classifyQueueItem('Awaiting Aaron — Play Production approval');
  assert.equal(r.queue_kind, 'human_approval');
}
{
  const r = classifyQueueItem('Pending approval: research export');
  assert.equal(r.queue_kind, 'human_approval');
}

// -- classifyQueueItem: release_qa_gate keyword matches ------

{
  const r = classifyQueueItem('Track v21 build install retest');
  assert.equal(r.queue_kind, 'release_qa_gate');
  assert.equal(r.matchedRule, 'release_gate_keyword');
}
{
  const r = classifyQueueItem('TestFlight processing for build 20');
  assert.equal(r.queue_kind, 'release_qa_gate');
}

// -- classifyQueueItem: data_readiness_evidence keyword matches --

{
  const r = classifyQueueItem('Ingest Apple Health sample for date 2026-05-09');
  assert.equal(r.queue_kind, 'data_readiness_evidence');
  assert.equal(r.matchedRule, 'evidence_keyword');
}
{
  const r = classifyQueueItem('Cached research artifact: BPC-157 mechanism');
  assert.equal(r.queue_kind, 'data_readiness_evidence');
}

// -- classifyQueueItem: fallback to automation_workflow + unclassified flag --

{
  const r = classifyQueueItem('something completely unrelated to keywords');
  assert.equal(r.queue_kind, 'automation_workflow');
  assert.equal(r.unclassified, true);
  assert.equal(r.matchedRule, 'fallback');
}

// -- shouldRecommendToIdleLane: P0 protection ----------------

{
  const item = { queue_kind: 'automation_workflow', priority: 'P0', status: 'prioritized' };
  const r = shouldRecommendToIdleLane(item, { activeP0Blocker: { id: 'hc-blocker' }, laneIdle: true });
  assert.equal(r.recommend, false, 'P0 blocker active → never recommend queue item');
  assert.match(r.reason, /P0 blocker/);
}

// -- shouldRecommendToIdleLane: P1 protection ----------------

{
  const item = { queue_kind: 'automation_workflow', priority: 'P0', status: 'prioritized' };
  const r = shouldRecommendToIdleLane(item, { activeP1Items: [{ id: 'p1-x' }], laneIdle: true });
  assert.equal(r.recommend, false, 'P1 items active → defer queue item');
}

// -- shouldRecommendToIdleLane: lane not idle ----------------

{
  const item = { queue_kind: 'automation_workflow', priority: 'P2', status: 'prioritized' };
  const r = shouldRecommendToIdleLane(item, { laneIdle: false });
  assert.equal(r.recommend, false);
}

// -- shouldRecommendToIdleLane: status gating ----------------

{
  const item = { queue_kind: 'automation_workflow', priority: 'P2', status: 'candidate' };
  const r = shouldRecommendToIdleLane(item, { laneIdle: true });
  assert.equal(r.recommend, false, 'candidate items not recommended');
}
{
  const item = { queue_kind: 'automation_workflow', priority: 'P2', status: 'in_progress' };
  const r = shouldRecommendToIdleLane(item, { laneIdle: true });
  assert.equal(r.recommend, true, 'in_progress + idle lane → recommend');
}

// -- shouldRecommendToIdleLane: overnight-only window --------

{
  const item = { queue_kind: 'overnight', priority: 'overnight_only', status: 'prioritized' };
  const r1 = shouldRecommendToIdleLane(item, { laneIdle: true, isOvernightWindow: false });
  assert.equal(r1.recommend, false, 'overnight_only + outside window → no');
  const r2 = shouldRecommendToIdleLane(item, { laneIdle: true, isOvernightWindow: true });
  assert.equal(r2.recommend, true, 'overnight_only + in window → yes');
}

// -- staleThresholdHours --------------------------------------

assert.equal(staleThresholdHours('automation_workflow'), 72);
assert.equal(staleThresholdHours('app_functionality'), 168);
assert.equal(staleThresholdHours('app_ux_ui'), 168);
assert.equal(staleThresholdHours('overnight'), 24);
assert.equal(staleThresholdHours('audit'), 168);
assert.equal(staleThresholdHours('human_approval'), 96, 'approval queue rots faster than functionality/ux');
assert.equal(staleThresholdHours('release_qa_gate'), 96, 'release gate rots in lockstep with approval');
assert.equal(staleThresholdHours('data_readiness_evidence'), 168 * 2, 'evidence has long shelf life');

// -- riskFromAction -------------------------------------------

assert.equal(riskFromAction('App Store public release'), 'irreversible');
assert.equal(riskFromAction('Play Production release'), 'irreversible');
assert.equal(riskFromAction('DROP TABLE users'), 'irreversible');
assert.equal(riskFromAction('TRUNCATE journal_events'), 'irreversible');
assert.equal(riskFromAction('Force-push to main'), 'irreversible');
assert.equal(riskFromAction('Rotate secret ATHLETE_MEMORY_API_TOKEN'), 'irreversible');

assert.equal(riskFromAction('Worker production deploy'), 'high');
assert.equal(riskFromAction('Stage 5 DNS cutover'), 'high');
assert.equal(riskFromAction('TestFlight Team release'), 'high');
assert.equal(riskFromAction('Play Internal upload'), 'high');

assert.equal(riskFromAction('Worker preview deploy'), 'medium');
assert.equal(riskFromAction('EAS Internal Testing build'), 'medium');
assert.equal(riskFromAction('npm dep upgrade'), 'medium');
assert.equal(riskFromAction('Supabase additive migration'), 'medium');

assert.equal(riskFromAction('Doc edit'), 'low');
assert.equal(riskFromAction('Read-only audit'), 'low');
assert.equal(riskFromAction('bridge:snapshot'), 'low');
assert.equal(riskFromAction('Spec addition'), 'low');
assert.equal(riskFromAction('Classifier change'), 'low');

assert.equal(riskFromAction('something unmapped'), 'medium', 'unknown action defaults to medium');

// -- isItemStale ----------------------------------------------

{
  const now = Date.now();
  const fresh = new Date(now - 12 * 3_600_000).toISOString(); // 12h ago
  assert.equal(isItemStale({ queue_kind: 'automation_workflow', lastUpdatedAt: fresh, now }), false);
  const stale = new Date(now - 80 * 3_600_000).toISOString(); // 80h ago > 72h threshold
  assert.equal(isItemStale({ queue_kind: 'automation_workflow', lastUpdatedAt: stale, now }), true);
  // Same 80h would NOT be stale for app_functionality (168h threshold).
  assert.equal(isItemStale({ queue_kind: 'app_functionality', lastUpdatedAt: stale, now }), false);
}
{
  // Missing lastUpdatedAt → treat as stale.
  assert.equal(isItemStale({ queue_kind: 'automation_workflow', lastUpdatedAt: null }), true);
}

console.log('✓ queue-taxonomy-helpers contract: 8 queues (+ audit + human_approval + release_qa_gate + data_readiness_evidence) / classifier rule order: approval > release_gate > evidence > audit > automation / P0+P1 protection / overnight-window / stale thresholds / riskFromAction');
console.log('queue-taxonomy-helpers contract test passed.');
