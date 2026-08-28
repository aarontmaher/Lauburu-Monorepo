import assert from 'node:assert/strict';

import { buildMcpAutomationPrompt } from '../../apps/mobile/src/services/prompt-templates';

const prompt = buildMcpAutomationPrompt({
  laneId: 'codex',
  idleStatus: 'blocked',
  recommendedNextPromptTarget: 'codex',
  recommendedNextPromptText: null,
  recommendedNextPromptSummary: 'Implement the smallest safe MCP prompt automation patch.',
  promptProgressPercent: 'unknown',
  currentPriority: 'MCP prompt automation',
  currentBlocker: 'Rule 1 shows prompt requirements but no copyable automation prompt.',
  nextAction: 'Add copy-only prompt scaffolds.',
  mcpFreshnessLabel: 'MCP live · fresh · 12s',
  releaseGateLabel: 'blocked',
  releaseGateReason: 'Installed-device QA still required.',
});

assert.match(prompt, /TYPE: MCP-AUTOMATION/, 'prompt has MCP automation type');
assert.match(prompt, /Freshness: MCP live · fresh · 12s/, 'prompt includes MCP freshness');
assert.match(prompt, /Lane: codex · idleStatus blocked · progress unknown/, 'prompt includes lane idle status');
assert.match(prompt, /Target worker: codex/, 'prompt includes target worker');
assert.match(prompt, /MCP prompt automation/, 'prompt includes priority');
assert.match(prompt, /Rule 1 shows prompt requirements/, 'prompt includes blocker');
assert.match(prompt, /Implement the smallest safe MCP prompt automation patch/, 'prompt uses MCP summary fallback task');
assert.match(prompt, /Do not start EAS, Play, TestFlight, OTA, Worker deploy, production release, or installed-device verified claims/, 'prompt locks external-action anti-rules');
assert.match(prompt, /Preserve unrelated dirty files/, 'prompt locks dirty-file safety');
assert.match(prompt, /MCP_RESULT \/ MCP_BLOCKER \/ MCP_TESTS \/ MCP_NEXT/, 'prompt asks for bridge markers');

const supplied = buildMcpAutomationPrompt({
  laneId: 'claude',
  idleStatus: 'idle',
  recommendedNextPromptTarget: 'claude',
  recommendedNextPromptText: 'Use this exact MCP-provided lane body.',
  recommendedNextPromptSummary: 'Ignored when full body exists.',
  promptProgressPercent: 55,
  currentPriority: 'Priority',
  currentBlocker: 'none',
  nextAction: 'Next',
  mcpFreshnessLabel: 'fresh',
  releaseGateLabel: 'blocked',
  releaseGateReason: 'reason',
});

assert.match(supplied, /progress 55%/, 'numeric progress is formatted');
assert.match(supplied, /MCP-PROVIDED PROMPT/, 'full text is labelled as MCP-provided');
assert.match(supplied, /Use this exact MCP-provided lane body/, 'full MCP body is preserved');
assert.doesNotMatch(supplied, /Ignored when full body exists/, 'summary does not replace full body');

console.log('prompt templates contract test passed.');
