/**
 * Contract tests for scripts/mcp-watcher-helpers.mjs.
 *
 * Pins the verdict shape + classifier behaviour so the
 * watcher can be relied on as the single source of truth
 * for "is MCP fresh AND does pane evidence agree".
 *
 * Run:
 *   cd cloudflare-worker && npx tsx test/test-mcp-watcher-helpers.ts
 */

import * as assert from 'node:assert/strict';
// @ts-expect-error — helpers are .mjs (no .d.ts); Node loader resolves at runtime.
import {
  classifyFreshness,
  classifyPaneText,
  detectAgentDisagreement,
  shouldAutoRefresh,
  buildFinding,
} from '../../scripts/mcp-watcher-helpers.mjs';

// -- classifyFreshness ----------------------------------------

{
  const r = classifyFreshness(null, { networkError: true });
  assert.equal(r.verdict, 'unreachable', 'network error → unreachable');
  assert.equal(r.actionable, true);
}

{
  const r = classifyFreshness(null, { httpStatus: 502 });
  assert.equal(r.verdict, 'unreachable', '502 → unreachable');
}

{
  const r = classifyFreshness({ staleReason: 'fresh' });
  assert.equal(r.verdict, 'fresh');
  assert.equal(r.actionable, false);
}

{
  const r = classifyFreshness({ staleReason: 'env_missing' });
  assert.equal(r.verdict, 'env_missing');
  assert.equal(r.actionable, true);
}

{
  const r = classifyFreshness({ staleReason: 'no_writeback' });
  assert.equal(r.verdict, 'no_writeback');
  assert.equal(r.actionable, true);
}

{
  const r = classifyFreshness({ staleReason: 'stale_writeback', ageMs: 12 * 60 * 1000 });
  assert.equal(r.verdict, 'stale_writeback');
  assert.equal(r.actionable, true);
  assert.ok(r.reason.includes('12 min'), 'reason mentions age');
}

{
  const r = classifyFreshness({ staleReason: 'something-else' });
  assert.equal(r.verdict, 'unreachable', 'unknown staleReason → unreachable');
}

// -- classifyPaneText -----------------------------------------

{
  const idle = `
some scrollback
auto mode on (shift+tab to cycle)
❯ `;
  const r = classifyPaneText(idle);
  assert.equal(r.paneStatus, 'idle');
}

{
  const busy = `
✶ Photosynthesizing… (2m 14s)
  ⎿  ◻ Bundle A: agent-audit p…

❯ `;
  const r = classifyPaneText(busy);
  assert.equal(r.paneStatus, 'busy');
}

{
  const queued = `
prompt body…
❯ Press up to edit queued messages
─── paste again to expand`;
  const r = classifyPaneText(queued);
  assert.equal(r.paneStatus, 'idle', 'queued message marker → idle');
}

{
  const r = classifyPaneText('');
  assert.equal(r.paneStatus, 'unknown');
}

// -- detectAgentDisagreement ----------------------------------

{
  const r = detectAgentDisagreement(
    { id: 'codex', status: 'working' },
    { paneStatus: 'idle', reason: 'idle marker' },
  );
  assert.equal(r.disagrees, true, 'cached working + pane idle → disagree');
  assert.equal(r.suggestedTrueStatus, 'idle');
}

{
  const r = detectAgentDisagreement(
    { id: 'codex', status: 'idle' },
    { paneStatus: 'busy', reason: 'busy marker' },
  );
  assert.equal(r.disagrees, true, 'cached idle + pane busy → disagree');
  assert.equal(r.suggestedTrueStatus, 'working');
}

{
  const r = detectAgentDisagreement(
    { id: 'codex', status: 'working' },
    { paneStatus: 'busy', reason: 'busy marker' },
  );
  assert.equal(r.disagrees, false, 'cached and pane both busy → no disagree');
}

{
  const r = detectAgentDisagreement(
    { id: 'codex', status: 'working' },
    { paneStatus: 'unknown', reason: 'no marker' },
  );
  assert.equal(r.disagrees, false, 'unknown pane → no disagreement asserted');
}

// -- shouldAutoRefresh ----------------------------------------

assert.equal(shouldAutoRefresh({ verdict: 'fresh' }), false);
assert.equal(shouldAutoRefresh({ verdict: 'env_missing' }), false);
assert.equal(shouldAutoRefresh({ verdict: 'unreachable' }), false);
assert.equal(shouldAutoRefresh({ verdict: 'no_writeback' }), true);
assert.equal(shouldAutoRefresh({ verdict: 'stale_writeback' }), true);
assert.equal(shouldAutoRefresh(null), false);

// -- buildFinding ---------------------------------------------

{
  const f = buildFinding({
    freshnessVerdict: { verdict: 'stale_writeback', actionable: true, reason: '12 min' },
    agentDisagreements: [{ disagrees: true, reason: 'cached working but pane idle', suggestedTrueStatus: 'idle' }],
    observedAt: '2026-05-09T08:42:00Z',
  });
  assert.equal(f.schemaVersion, 1);
  assert.equal(f.actionable, true);
  assert.equal(f.agentDisagreements.length, 1);
}

{
  const f = buildFinding({
    freshnessVerdict: { verdict: 'fresh', actionable: false, reason: 'within window' },
    agentDisagreements: [],
    observedAt: '2026-05-09T08:42:00Z',
  });
  assert.equal(f.actionable, false, 'fresh + no disagreements → not actionable');
}

console.log('✓ mcp-watcher-helpers contract: classifyFreshness / classifyPaneText / detectAgentDisagreement / shouldAutoRefresh / buildFinding');
console.log('mcp-watcher-helpers contract test passed.');
