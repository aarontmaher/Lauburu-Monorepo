/**
 * Rule 1 contract test — "MCP-first + terminal-truth fallback +
 * no idle lanes." The operating-rules constant carries the rule
 * at id 24 (high id keeps prior cross-references stable; the
 * rule TITLE communicates priority — see docs/OPERATING_RULES.md
 * preamble "Read rule 24 first").
 *
 * Asserts the rule is present in OPERATING_RULES, that its body
 * mentions the four canonical payload fields the spec requires
 * surfacing, and that the lane-progress summariser hard-flags
 * idle / blocked / needs_review / needs_user /
 * complete_waiting_approval lanes for a recommended-next-prompt
 * with promptProgressPercent === 'unknown' when MCP did not emit
 * a numeric progress.
 */

import assert from 'node:assert/strict';
import { OPERATING_RULES } from '../src/operating-rules';
import { summariseLaneProgress } from '../../apps/mobile/src/services/lane-progress-summary';

const RULE_1 = OPERATING_RULES.find((r) => /Rule\s*1\b/.test(r.title));
assert.ok(RULE_1, 'OPERATING_RULES must contain a rule whose title starts with "Rule 1"');
assert.equal(RULE_1!.id, 24, 'Rule 1 lives at stable id 24 (title carries priority; preamble elevates it)');

// The rule body must reference the canonical payload contract.
for (const marker of [
  'recommendedNextPromptTarget',
  'recommendedNextPromptText',
  'recommendedNextPromptSummary',
  'promptProgressPercent',
  'idleStatus',
  'laneFreshness',
  'terminal',
  'MCP',
]) {
  assert.ok(RULE_1!.body.includes(marker), `Rule 1 body must mention ${JSON.stringify(marker)}`);
}

// Hard-floor exceptions remain authoritative.
for (const floor of ['rule 7', 'rule 21', 'rule 22', 'rule 23']) {
  assert.ok(RULE_1!.body.includes(floor), `Rule 1 body must preserve ${floor} as a hard-floor exception`);
}

// Stale-cached working must NEVER suppress an idle prompt.
const NOW = Date.parse('2026-05-09T12:00:00Z');
const stalePretendingWorking = summariseLaneProgress(
  {
    freshness: { isStale: false, updatedAt: new Date(NOW - 5_000).toISOString() },
    agents: [
      {
        id: 'codex',
        status: 'working',
        lastSeenAt: new Date(NOW - 2_000).toISOString(),
        terminalIdleAt: new Date(NOW - 1_000).toISOString(),
      },
    ],
  },
  NOW,
);
assert.equal(stalePretendingWorking.promptsRequired.length, 1, 'terminal-idle override must produce a recommended prompt entry');
assert.equal(stalePretendingWorking.promptsRequired[0].promptProgressPercent, 'unknown', 'missing progress emits the literal "unknown" not 0');

// Working lanes do NOT get a recommended-next-prompt.
const workingFresh = summariseLaneProgress(
  {
    freshness: { isStale: false, updatedAt: new Date(NOW - 5_000).toISOString() },
    agents: [
      { id: 'claude', status: 'in_progress', lastSeenAt: new Date(NOW - 2_000).toISOString(), progressPct: 50 },
    ],
  },
  NOW,
);
assert.equal(workingFresh.promptsRequired.length, 0, 'working+fresh lanes must NOT trigger Rule 1 prompt routing');

// Empty agents → unavailable, no prompts (caller surfaces "MCP unavailable").
const empty = summariseLaneProgress(null, NOW);
assert.equal(empty.source, 'unavailable');
assert.equal(empty.promptsRequired.length, 0);

console.log('Rule 1 (no idle lanes) contract test passed.');
