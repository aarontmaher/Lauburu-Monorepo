/**
 * Contract tests for scripts/prompt-dispatcher-helpers.mjs.
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-prompt-dispatcher-helpers.ts
 */

import * as assert from 'node:assert/strict';
// @ts-expect-error — helpers are .mjs (no .d.ts); Node loader resolves at runtime.
import {
  isLaneIdle,
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
  unsafePromptReason('Lane: Codex — run EAS build and upload to Play'),
  'prompt contains blocked term: \\beas\\b',
  'unsafe EAS/build/upload prompt is blocked',
);
assert.equal(unsafePromptReason('Lane: Codex — repo-only docs and tests.\nNo release/build/upload actions.'), null);
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

console.log('prompt-dispatcher helpers contract test passed.');
