/**
 * Contract tests for scripts/subagent-worktree-helpers.mjs and subagent-dispatcher-worktree.mjs.
 *
 * Run:
 *   cd core/cloudflare-worker && npx tsx test/test-subagent-worktree-dispatcher.ts
 */

import * as assert from 'node:assert/strict';
import { existsSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

// @ts-expect-error — helpers are .mjs (no .d.ts); Node loader resolves at runtime.
import {
  createIsolatedWorktree,
  dispatchSubagentTaskAndGovern,
  distillHarvestIntoMemory,
  harvestWorktreeDiff,
  listIsolatedWorktrees,
  removeIsolatedWorktree,
  runPreFlightPytest,
} from '../../scripts/subagent-worktree-helpers.mjs';

const REPO_ROOT = resolve(__dirname, '../../..');
const TEST_WORKTREE_DIR = join(REPO_ROOT, '.worktrees', 'test-subagent-unit-spec');
const TEST_MEMORY_FILE = join(REPO_ROOT, 'data', 'distillation-memory', 'test_memory_store.json');

// Clean up previous runs if any
if (existsSync(TEST_WORKTREE_DIR)) {
  removeIsolatedWorktree({ repoRoot: REPO_ROOT, worktreePath: TEST_WORKTREE_DIR, force: true });
}
if (existsSync(TEST_MEMORY_FILE)) {
  rmSync(TEST_MEMORY_FILE, { force: true });
}

console.log('Testing createIsolatedWorktree...');
const worktreeInfo = createIsolatedWorktree({
  repoRoot: REPO_ROOT,
  subagentId: 'test-agent',
  branchName: 'subagent/unit-test-spec',
  worktreeDir: TEST_WORKTREE_DIR,
});

assert.ok(worktreeInfo.worktreePath, 'worktree path returned');
assert.equal(existsSync(worktreeInfo.worktreePath), true, 'worktree directory created on disk');

console.log('Testing listIsolatedWorktrees...');
const worktrees = listIsolatedWorktrees({ repoRoot: REPO_ROOT });
assert.ok(Array.isArray(worktrees), 'listIsolatedWorktrees returns an array');
assert.ok(worktrees.some((w: any) => w.worktree && w.worktree.includes('test-subagent-unit-spec')), 'created worktree appears in list');

console.log('Testing runPreFlightPytest...');
// Create a temporary python test file in the worktree
const dummyPyTest = join(TEST_WORKTREE_DIR, 'test_dummy_gate.py');
writeFileSync(
  dummyPyTest,
  `def test_subagent_gate():\n    assert 1 + 1 == 2\n`,
  'utf8'
);

const pytestRes = runPreFlightPytest({
  cwd: TEST_WORKTREE_DIR,
  testPath: 'test_dummy_gate.py',
});

assert.equal(pytestRes.passed, true, 'pytest gate passed');
assert.equal(pytestRes.exitCode, 0, 'exit code 0');
assert.match(pytestRes.summary, /1 passed|passed/i, 'summary shows passed tests');

console.log('Testing harvestWorktreeDiff and distillHarvestIntoMemory...');
// Make a commit in the worktree so diff can be harvested
spawnSync('git', ['add', 'test_dummy_gate.py'], { cwd: TEST_WORKTREE_DIR });
spawnSync('git', ['commit', '-m', 'test: add subagent dummy pytest gate'], { cwd: TEST_WORKTREE_DIR });

const harvest = harvestWorktreeDiff({
  worktreePath: TEST_WORKTREE_DIR,
  baseRef: 'HEAD~1',
  targetRef: 'HEAD',
});

assert.ok(harvest.commitHash, 'commit hash extracted');
assert.equal(harvest.subject, 'test: add subagent dummy pytest gate', 'commit subject matched');
assert.ok(harvest.changedFiles.some((f: any) => f.file === 'test_dummy_gate.py'), 'changed file detected in diff harvest');

const memoryEntry = distillHarvestIntoMemory({
  harvest,
  memoryPath: TEST_MEMORY_FILE,
  subagentId: 'test-agent',
  taskTitle: 'Unit Test Subagent Memory Harvest',
});

assert.ok(memoryEntry.id, 'distillation memory entry ID created');
assert.equal(memoryEntry.kind, 'subagent_pr_harvest', 'entry kind is subagent_pr_harvest');
assert.equal(memoryEntry.subagentId, 'test-agent', 'subagent ID recorded');
assert.equal(existsSync(TEST_MEMORY_FILE), true, 'memory file written');

const storeData = JSON.parse(readFileSync(TEST_MEMORY_FILE, 'utf8'));
assert.equal(storeData.distillations.length, 1, 'distillations store contains 1 entry');
assert.equal(storeData.distillations[0].id, memoryEntry.id, 'store entry matches returned entry');

console.log('Testing dispatchSubagentTaskAndGovern full pipeline...');
const dispatchRes = dispatchSubagentTaskAndGovern({
  repoRoot: REPO_ROOT,
  subagentId: 'test-agent-full',
  branchName: 'subagent/unit-test-full-pipeline',
  testPath: 'test_pipeline_gate.py',
  memoryPath: TEST_MEMORY_FILE,
  taskSetupFn: (worktreePath: string) => {
    const testFile = join(worktreePath, 'test_pipeline_gate.py');
    writeFileSync(testFile, 'def test_pipeline():\n    assert True\n', 'utf8');
    spawnSync('git', ['add', 'test_pipeline_gate.py'], { cwd: worktreePath });
    spawnSync('git', ['commit', '-m', 'feat: subagent pipeline commit'], { cwd: worktreePath });
  },
  cleanupWorktreeOnSuccess: true,
});

assert.equal(dispatchRes.status, 'success', `dispatch pipeline status is success (reason: ${dispatchRes.reason})`);
assert.ok(dispatchRes.preflight.passed, 'preflight passed');
assert.ok(dispatchRes.harvest, 'harvest present');
assert.ok(dispatchRes.memoryEntry, 'memory entry present');

console.log('Cleaning up test artifacts...');
if (existsSync(TEST_WORKTREE_DIR)) {
  removeIsolatedWorktree({ repoRoot: REPO_ROOT, worktreePath: TEST_WORKTREE_DIR, force: true });
}
if (existsSync(TEST_MEMORY_FILE)) {
  rmSync(TEST_MEMORY_FILE, { force: true });
}

console.log('subagent-worktree-dispatcher contract test passed.');
