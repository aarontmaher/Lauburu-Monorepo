/**
 * Contract tests for scripts/prompt-dispatcher-helpers.mjs.
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-prompt-dispatcher-helpers.ts
 */

import * as assert from 'node:assert/strict';
// @ts-expect-error — helpers are .mjs (no .d.ts); Node loader resolves at runtime.
import {
  classifyLocalBridgeSnapshot,
  generatePromptQueueFromActionLedger,
  isLaneIdle,
  markPromptDispatched,
  normalizeQueueItems,
  selectNextPrompt,
  unsafePromptReason,
} from '../../scripts/prompt-dispatcher-helpers.mjs';

const lanes = [
  { laneId: 'codex', status: 'idle', terminalStatus: 'idle' },
  { laneId: 'claude', status: 'working', terminalStatus: 'working' },
];

assert.equal(isLaneIdle(lanes[0]), true, 'codex idle lane is dispatchable');
assert.equal(isLaneIdle(lanes[1]), false, 'working claude lane is not dispatchable');

assert.equal(
  classifyLocalBridgeSnapshot({ generatedAt: '2026-05-09T00:00:00.000Z' }, { nowMs: Date.parse('2026-05-09T00:00:10.000Z'), maxAgeMs: 60_000 }).fresh,
  true,
  'fresh bridge snapshot accepted',
);
{
  const stale = classifyLocalBridgeSnapshot({ generatedAt: '2026-05-09T00:00:00.000Z' }, { nowMs: Date.parse('2026-05-09T00:02:00.000Z'), maxAgeMs: 60_000 });
  assert.equal(stale.fresh, false, 'stale bridge snapshot blocks dispatch');
  assert.match(stale.recovery, /terminal:auto/, 'stale bridge snapshot gives terminal:auto recovery');
}
assert.equal(classifyLocalBridgeSnapshot(null).fresh, false, 'missing bridge snapshot blocks dispatch');

assert.equal(
  unsafePromptReason('Lane: Codex — run EAS build and upload to Play'),
  'prompt contains blocked term: \\beas\\b',
  'unsafe EAS/build/upload prompt is blocked',
);
assert.equal(unsafePromptReason('Lane: Codex — repo-only docs and tests.\nNo release/build/upload actions.'), null);
assert.equal(unsafePromptReason('Repo-only scope note; no EAS build, no deploy, and no release action.'), null);
assert.equal(unsafePromptReason('Resume repo-only work after the health/release gate no longer owns the top priority.'), null);
assert.equal(unsafePromptReason('MCP/action-ledger item: p1p2-after-health-release-gate'), null);
assert.equal(unsafePromptReason('Lane: Codex — repo-only docs and tests. Public-safe only.'), null);

const queue = normalizeQueueItems({
  prompts: [
    {
      id: 'missing-approval',
      targetLane: 'codex',
      status: 'queued',
      approved: false,
      publicSafe: true,
      promptText: 'Lane: Codex — repo-only docs and tests.',
    },
    {
      id: 'safe-p2',
      targetLane: 'codex',
      priority: 'P2',
      status: 'queued',
      approved: true,
      publicSafe: true,
      createdAt: '2026-05-09T00:00:02Z',
      promptText: 'Lane: Codex — repo-only tooling test cleanup. Public-safe only.',
    },
    {
      id: 'safe-p1',
      targetLane: 'codex',
      priority: 'P1',
      status: 'ready',
      approved: true,
      publicSafe: true,
      createdAt: '2026-05-09T00:00:01Z',
      promptText: 'Lane: Codex — repo-only prompt dispatcher docs. Public-safe only.',
    },
    {
      id: 'unsafe-build',
      targetLane: 'codex',
      priority: 'P0',
      status: 'queued',
      approved: true,
      publicSafe: true,
      promptText: 'Lane: Codex — build and upload Android.',
    },
    {
      id: 'busy-claude',
      targetLane: 'claude',
      priority: 'P0',
      status: 'queued',
      approved: true,
      publicSafe: true,
      promptText: 'Lane: Claude — repo-only docs audit. Public-safe only.',
    },
  ],
});

assert.equal(queue.length, 5, 'normalizes five prompt rows');

const selected = selectNextPrompt({ queueInput: queue, lanes });
assert.equal(selected.selected?.id, 'safe-p1', 'selects highest-priority safe prompt for idle lane');
assert.equal(selected.decisions.find((d: any) => d.item.id === 'missing-approval')?.reason, 'not approved');
assert.match(selected.decisions.find((d: any) => d.item.id === 'unsafe-build')?.reason, /blocked term/);
assert.equal(selected.decisions.find((d: any) => d.item.id === 'busy-claude')?.reason, 'target lane claude is not idle');

const none = selectNextPrompt({
  queueInput: [{ id: 'nope', targetLane: 'codex', approved: true, publicSafe: true, promptText: 'build now' }],
  lanes,
});
assert.equal(none.selected, null, 'unsafe-only queue selects nothing');

const generated = generatePromptQueueFromActionLedger({
  currentPriorityOrder: [{ id: 'gate-health', title: 'Health gate', status: 'active' }],
  pendingActions: [
    {
      id: 'manual-v21-upload',
      owner: 'Aaron',
      targetWorkerOrPerson: 'Aaron',
      lane: 'Android internal QA build',
      actionText: 'Upload v21 AAB to Play Internal, install on Samsung, confirm versionCode 21, then run 10-screenshot Health Connect QA.',
      triggerCondition: 'v21 build is available.',
      status: 'pending',
      priority: 'P0',
      createdAt: '2026-05-09T00:00:00Z',
    },
    {
      id: 'codex-safe',
      owner: 'Codex',
      targetWorkerOrPerson: 'Codex',
      lane: 'MCP automation',
      actionText: 'Inspect repo-only automation docs and tests.',
      triggerCondition: 'Codex lane idle.',
      status: 'pending',
      priority: 'P1',
      createdAt: '2026-05-09T00:00:01Z',
    },
  ],
}, {}, { generatedAt: '2026-05-09T00:00:02Z' });

assert.equal(generated.topPriority.title, 'Health gate', 'generated queue carries top priority');
assert.equal(generated.prompts.find((p: any) => p.id === 'ledger-manual-v21-upload')?.status, 'manual_required', 'Play upload remains manual required');
assert.equal(generated.prompts.find((p: any) => p.id === 'ledger-codex-safe')?.status, 'queued', 'safe Codex action becomes queued');

const staleGenerated = generatePromptQueueFromActionLedger({
  pendingActions: [
    {
      id: 'codex-stale',
      owner: 'Codex',
      targetWorkerOrPerson: 'Codex',
      lane: 'Dispatcher queue freshness audit',
      actionText: 'Inspect repo-only automation docs and tests.',
      status: 'superseded',
      priority: 'P1',
      createdAt: '2026-05-09T00:00:01Z',
    },
    {
      id: 'codex-active',
      owner: 'Codex',
      targetWorkerOrPerson: 'Codex',
      lane: 'Already active lane item',
      actionText: 'Continue repo-only review already in progress.',
      status: 'active',
      priority: 'P1',
      createdAt: '2026-05-09T00:00:02Z',
    },
    {
      id: 'manual-stale-v20',
      owner: 'Aaron',
      targetWorkerOrPerson: 'Aaron',
      lane: 'Android internal QA build',
      actionText: 'Manually upload Android versionCode 20 AAB to Play Console Internal Testing.',
      status: 'superseded',
      priority: 'P0',
      createdAt: '2026-05-09T00:00:00Z',
    },
  ],
}, {}, { generatedAt: '2026-05-09T00:00:03Z' });
assert.equal(staleGenerated.prompts.find((p: any) => p.id === 'ledger-codex-stale')?.status, 'stale', 'superseded ledger entry becomes stale');
assert.equal(staleGenerated.prompts.find((p: any) => p.id === 'ledger-codex-stale')?.approved, false, 'stale ledger entry is not approved');
assert.equal(staleGenerated.prompts.find((p: any) => p.id === 'ledger-codex-active')?.status, 'active', 'active ledger entry is not newly queued');
assert.equal(staleGenerated.prompts.find((p: any) => p.id === 'ledger-codex-active')?.approved, false, 'active ledger entry is not approved for dispatch');
assert.equal(staleGenerated.prompts.find((p: any) => p.id === 'ledger-manual-stale-v20')?.status, 'stale', 'superseded manual entry is stale, not manual required');
assert.equal(staleGenerated.prompts.find((p: any) => p.id === 'ledger-manual-stale-v20')?.manualRequired, true, 'superseded manual entry still records manual ownership');

const dispatchedQueue = markPromptDispatched(generated, { id: 'ledger-codex-safe' }, '2026-05-09T00:00:03Z');
assert.equal(dispatchedQueue.prompts.find((p: any) => p.id === 'ledger-codex-safe')?.status, 'dispatched', 'markPromptDispatched marks status');
assert.equal(
  selectNextPrompt({ queueInput: dispatchedQueue, lanes: [{ laneId: 'codex', status: 'idle', terminalStatus: 'idle' }] }).selected,
  null,
  'already dispatched prompt is not selected again',
);

console.log('prompt-dispatcher helpers contract test passed.');
