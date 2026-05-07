/**
 * Validate the local bridge artifacts under data/agent-status/lanes/
 * against the connector schema in
 * chat-app/src/server/types/connector.ts.
 *
 * Run after `./scripts/bridge-snapshot-lanes.sh`:
 *
 *   cd chat-app
 *   npx tsx src/server/scripts/test-bridge-artifacts.ts
 *
 * Exits non-zero on any shape mismatch. No network, no DB.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  CONNECTOR_SCHEMA_VERSION,
  type AgentQaGate,
  type AgentQaPlatform,
  type AgentQaResult,
  type AgentQaResultStatus,
  type AgentQaStatus,
  type CoderLaneRow,
  type CoderLanes,
  type Handoff,
  type LaneId,
  type LaneStatus,
  type TerminalSummary,
  type TerminalSummaryEntry,
  type TypecheckResult,
} from '../types/connector';

const REPO_ROOT = path.resolve(__dirname, '../../../../');
const LANES_DIR = path.join(REPO_ROOT, 'data/agent-status/lanes');

const LANE_IDS: ReadonlySet<LaneId> = new Set([
  'claude', 'codex', 'claude_chat', 'chatgpt', 'cowork',
] as const);
const LANE_STATUSES: ReadonlySet<LaneStatus> = new Set([
  'idle', 'working', 'blocked', 'needs_user', 'needs_review', 'done',
] as const);
const TYPECHECK_RESULTS: ReadonlySet<TypecheckResult> = new Set([
  'pass', 'fail', 'unknown',
] as const);
const AGENT_QA_STATUSES: ReadonlySet<AgentQaStatus> = new Set([
  'pass', 'fail', 'blocked', 'repo_only', 'partial',
] as const);
const AGENT_QA_GATES: ReadonlySet<AgentQaGate> = new Set([
  'health_connectivity', 'grappling_readiness', 'native_control_centre', 'release_gate', 'general',
] as const);
const AGENT_QA_PLATFORMS: ReadonlySet<AgentQaPlatform> = new Set([
  'android', 'ios', 'both', 'repo',
] as const);
const AGENT_QA_RESULT_STATUSES: ReadonlySet<AgentQaResultStatus> = new Set([
  'pass', 'fail', 'blocked', 'repo_only', 'partial', 'not_tested',
] as const);

function readJson<T>(file: string): T {
  if (!fs.existsSync(file)) {
    throw new Error(`Bridge artifact not found: ${file}. Run scripts/bridge-snapshot-lanes.sh first.`);
  }
  return JSON.parse(fs.readFileSync(file, 'utf8')) as T;
}

function assert(cond: unknown, label: string): asserts cond {
  if (!cond) throw new Error(`assertion failed: ${label}`);
}

function isIsoZ(s: unknown): s is string {
  return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(s);
}

function validateRow(row: CoderLaneRow, prefix: string): void {
  assert(LANE_IDS.has(row.laneId), `${prefix} laneId enum`);
  assert(LANE_STATUSES.has(row.status), `${prefix} status enum`);
  assert(row.lastSeenAt === null || isIsoZ(row.lastSeenAt), `${prefix} lastSeenAt`);
  assert(row.currentPromptId === null || typeof row.currentPromptId === 'string', `${prefix} currentPromptId`);
  assert(row.lastPromptId === null || typeof row.lastPromptId === 'string', `${prefix} lastPromptId`);
  assert(row.lastSummary === null || (typeof row.lastSummary === 'string' && row.lastSummary.length <= 1200), `${prefix} lastSummary cap`);
  assert(row.lastCommit === null || typeof row.lastCommit === 'string', `${prefix} lastCommit`);
  assert(row.lastTypecheckResult === null || TYPECHECK_RESULTS.has(row.lastTypecheckResult), `${prefix} lastTypecheckResult enum`);
  assert(Array.isArray(row.dirtyFiles), `${prefix} dirtyFiles array`);
  for (const f of row.dirtyFiles) assert(typeof f === 'string', `${prefix} dirtyFiles entry`);
  assert(row.nextPrompt === null || typeof row.nextPrompt === 'string', `${prefix} nextPrompt`);
}

function validateCoderLanes(payload: CoderLanes): void {
  assert(payload.schemaVersion === CONNECTOR_SCHEMA_VERSION, 'coder_lanes schemaVersion');
  assert(isIsoZ(payload.generatedAt), 'coder_lanes generatedAt');
  assert(Array.isArray(payload.lanes), 'coder_lanes lanes array');
  payload.lanes.forEach((row, i) => validateRow(row, `coder_lanes.lanes[${i}]`));
}

function validateTerminalEntry(entry: TerminalSummaryEntry, prefix: string): void {
  assert(LANE_IDS.has(entry.laneId), `${prefix} laneId enum`);
  assert(isIsoZ(entry.at), `${prefix} at`);
  assert(typeof entry.summary === 'string' && entry.summary.length <= 1200, `${prefix} summary cap`);
  assert(typeof entry.verification === 'string' && entry.verification.length <= 240, `${prefix} verification cap`);
  assert(typeof entry.nextAction === 'string' && entry.nextAction.length <= 240, `${prefix} nextAction cap`);
  assert(entry.exitCode === null || typeof entry.exitCode === 'number', `${prefix} exitCode`);
}

function validateTerminalSummary(payload: TerminalSummary): void {
  assert(payload.schemaVersion === CONNECTOR_SCHEMA_VERSION, 'terminal_summary schemaVersion');
  assert(isIsoZ(payload.generatedAt), 'terminal_summary generatedAt');
  assert(Array.isArray(payload.entries), 'terminal_summary entries array');
  assert(payload.entries.length <= 50, 'terminal_summary entry cap');
  payload.entries.forEach((e, i) => validateTerminalEntry(e, `terminal_summary.entries[${i}]`));
}

function validateHandoff(payload: Handoff): void {
  assert(payload.schemaVersion === CONNECTOR_SCHEMA_VERSION, 'handoff schemaVersion');
  assert(isIsoZ(payload.generatedAt), 'handoff generatedAt');
  assert(payload.latestClaudePrompt === null || typeof payload.latestClaudePrompt === 'string', 'handoff latestClaudePrompt');
  assert(payload.latestCodexPrompt === null || typeof payload.latestCodexPrompt === 'string', 'handoff latestCodexPrompt');
  assert(Array.isArray(payload.manualSteps), 'handoff manualSteps array');
  assert(payload.manualSteps.length <= 10, 'handoff manualSteps cap');
  for (const s of payload.manualSteps) {
    assert(typeof s === 'string' && s.length <= 200, 'handoff manualStep cap');
  }
  assert(Array.isArray(payload.doNotTouch), 'handoff doNotTouch array');
  for (const s of payload.doNotTouch) assert(typeof s === 'string', 'handoff doNotTouch entry');
  assert(typeof payload.safeToBuild === 'boolean', 'handoff safeToBuild bool');
  assert(typeof payload.safeToBuildReason === 'string' && payload.safeToBuildReason.length <= 280, 'handoff safeToBuildReason cap');
  if (payload.agentQaResult != null) {
    validateAgentQaResult(payload.agentQaResult, 'handoff.agentQaResult');
  }
}

function validateAgentQaResult(payload: AgentQaResult, prefix: string): void {
  assert(payload.schemaVersion === CONNECTOR_SCHEMA_VERSION, `${prefix} schemaVersion`);
  assert(typeof payload.qaRunId === 'string' && payload.qaRunId.length > 0 && payload.qaRunId.length <= 80, `${prefix} qaRunId`);
  assert(typeof payload.sourceAgent === 'string' && payload.sourceAgent.length > 0 && payload.sourceAgent.length <= 80, `${prefix} sourceAgent`);
  assert(isIsoZ(payload.createdAt), `${prefix} createdAt`);
  assert(isIsoZ(payload.updatedAt), `${prefix} updatedAt`);
  assert(AGENT_QA_STATUSES.has(payload.status), `${prefix} status enum`);
  assert(AGENT_QA_GATES.has(payload.gate), `${prefix} gate enum`);
  assert(AGENT_QA_PLATFORMS.has(payload.platform), `${prefix} platform enum`);
  assert(payload.deviceName == null || typeof payload.deviceName === 'string', `${prefix} deviceName`);
  assert(typeof payload.installedBuild === 'object' && payload.installedBuild !== null, `${prefix} installedBuild`);
  assert(typeof payload.repo === 'object' && payload.repo !== null, `${prefix} repo`);
  assert(typeof payload.repo.branch === 'string' && payload.repo.branch.length > 0, `${prefix} repo.branch`);
  assert(typeof payload.repo.shortHead === 'string' && /^[0-9a-f]{7,12}$/.test(payload.repo.shortHead), `${prefix} repo.shortHead`);
  assert(typeof payload.results === 'object' && payload.results !== null, `${prefix} results`);
  for (const key of ['healthManageSources', 'androidHealthConnect', 'iosAppleHealth', 'grapplingReadiness', 'adminControlCentre', 'copyTruthfulness', 'uiDensity'] as const) {
    assert(AGENT_QA_RESULT_STATUSES.has(payload.results[key]), `${prefix} results.${key}`);
  }
  assert(typeof payload.releaseGate === 'object' && payload.releaseGate !== null, `${prefix} releaseGate`);
  assert(typeof payload.releaseGate.newTestFlightAllowed === 'boolean', `${prefix} releaseGate.newTestFlightAllowed`);
  assert(typeof payload.releaseGate.newAndroidBuildAllowed === 'boolean', `${prefix} releaseGate.newAndroidBuildAllowed`);
  assert(typeof payload.releaseGate.reason === 'string' && payload.releaseGate.reason.length <= 280, `${prefix} releaseGate.reason`);
  assert(Array.isArray(payload.requiredFixes) && payload.requiredFixes.length <= 20, `${prefix} requiredFixes`);
  for (const fix of payload.requiredFixes) assert(typeof fix === 'string' && fix.length <= 200, `${prefix} requiredFix`);
  assert(typeof payload.evidence === 'object' && payload.evidence !== null, `${prefix} evidence`);
  assert(Array.isArray(payload.evidence.screenshotRefs), `${prefix} screenshotRefs`);
  for (const ref of payload.evidence.screenshotRefs) assert(typeof ref === 'string' && ref.length <= 160, `${prefix} screenshotRef`);
  assert(typeof payload.evidence.notes === 'string' && payload.evidence.notes.length <= 1000, `${prefix} evidence.notes`);
  assert(typeof payload.publicSummary === 'string' && payload.publicSummary.length <= 280, `${prefix} publicSummary`);
  assert(payload.privateDetails == null || (typeof payload.privateDetails === 'string' && payload.privateDetails.length <= 2000), `${prefix} privateDetails`);
}

function main(): void {
  const coderLanes = readJson<CoderLanes>(path.join(LANES_DIR, 'coder_lanes.json'));
  validateCoderLanes(coderLanes);
  console.log(`✓ coder_lanes: ${coderLanes.lanes.length} lane(s)`);

  const terminalSummary = readJson<TerminalSummary>(path.join(LANES_DIR, 'terminal_summary.json'));
  validateTerminalSummary(terminalSummary);
  console.log(`✓ terminal_summary: ${terminalSummary.entries.length} entry(s)`);

  const handoff = readJson<Handoff>(path.join(LANES_DIR, 'handoff.json'));
  validateHandoff(handoff);
  console.log(`✓ handoff: latestClaude=${handoff.latestClaudePrompt} latestCodex=${handoff.latestCodexPrompt} safeToBuild=${handoff.safeToBuild}`);

  for (const lane of coderLanes.lanes) {
    const perLane = readJson<CoderLaneRow>(path.join(LANES_DIR, `${lane.laneId}.json`));
    validateRow(perLane, `per-lane:${lane.laneId}`);
    console.log(`✓ per-lane: ${lane.laneId}`);
  }

  console.log('Bridge artifact schema tests passed.');
}

main();
