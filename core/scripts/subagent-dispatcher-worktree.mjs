#!/usr/bin/env node
/**
 * subagent-dispatcher-worktree — Automates Subagent Task Dispatcher & Worktree Governor:
 * Connects Jules background sessions to isolated git worktrees, executes pre-flight pytest gates,
 * and harvests successful PR diffs directly into continuous distillation memory.
 */

import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  createIsolatedWorktree,
  dispatchSubagentTaskAndGovern,
  distillHarvestIntoMemory,
  harvestWorktreeDiff,
  listIsolatedWorktrees,
  removeIsolatedWorktree,
  runPreFlightPytest,
} from './subagent-worktree-helpers.mjs';

const REPO_ROOT = resolve(new URL('..', import.meta.url).pathname, '..');

function parseArgs(argv) {
  const out = {
    repoRoot: REPO_ROOT,
    subagentId: 'subagent-01',
    branchName: null,
    baseBranch: 'HEAD',
    testPath: null,
    pytestArgs: [],
    memoryPath: null,
    cleanup: false,
    listWorktrees: false,
    removeWorktreePath: null,
    dispatch: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];

    if (arg === '--repo-root' && next) { out.repoRoot = resolve(next); i += 1; }
    else if (arg === '--subagent' && next) { out.subagentId = next; i += 1; }
    else if (arg === '--branch' && next) { out.branchName = next; i += 1; }
    else if (arg === '--base' && next) { out.baseBranch = next; i += 1; }
    else if (arg === '--test' && next) { out.testPath = next; i += 1; }
    else if (arg === '--pytest-args' && next) { out.pytestArgs = next.split(' '); i += 1; }
    else if (arg === '--memory-path' && next) { out.memoryPath = resolve(next); i += 1; }
    else if (arg === '--cleanup') out.cleanup = true;
    else if (arg === '--list-worktrees') out.listWorktrees = true;
    else if (arg === '--remove-worktree' && next) { out.removeWorktreePath = resolve(next); i += 1; }
    else if (arg === '--dispatch') out.dispatch = true;
    else if (arg === '--help' || arg === '-h') {
      console.log(`Usage: node scripts/subagent-dispatcher-worktree.mjs [flags]

Flags:
  --subagent <id>         Subagent session identifier (default: subagent-01)
  --branch <name>         Branch name for isolated worktree
  --base <ref>            Base branch/commit ref (default: HEAD)
  --test <path>           Test file/directory for pre-flight pytest gates
  --pytest-args <args>    Extra arguments for pytest
  --memory-path <path>    Custom continuous distillation memory file path
  --cleanup               Clean up worktree upon successful dispatch/harvest
  --dispatch              Run full worktree + pre-flight pytest + harvest pipeline
  --list-worktrees        List active git worktrees and exit
  --remove-worktree <path> Remove specified git worktree and exit
  --repo-root <path>      Path to repo root (default: current workspace)
`);
      process.exit(0);
    }
  }

  return out;
}

function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.listWorktrees) {
    const worktrees = listIsolatedWorktrees({ repoRoot: args.repoRoot });
    console.log(JSON.stringify({ worktrees }, null, 2));
    return;
  }

  if (args.removeWorktreePath) {
    const res = removeIsolatedWorktree({ repoRoot: args.repoRoot, worktreePath: args.removeWorktreePath });
    console.log(JSON.stringify(res, null, 2));
    return;
  }

  if (!args.dispatch) {
    console.log(`Subagent Task Dispatcher & Worktree Governor (Dry-Run Mode)
Repo Root: ${args.repoRoot}
Subagent: ${args.subagentId}
Test Path: ${args.testPath || '(none specified)'}
Memory Path: ${args.memoryPath || '(default)'}

To execute full dispatch pipeline with pre-flight pytest gates and memory harvest, add --dispatch.`);
    return;
  }

  console.log(`Executing subagent worktree dispatch pipeline for subagent=${args.subagentId}...`);
  const result = dispatchSubagentTaskAndGovern({
    repoRoot: args.repoRoot,
    subagentId: args.subagentId,
    branchName: args.branchName,
    baseBranch: args.baseBranch,
    testPath: args.testPath,
    pytestArgs: args.pytestArgs,
    memoryPath: args.memoryPath,
    cleanupWorktreeOnSuccess: args.cleanup,
  });

  console.log(JSON.stringify(result, null, 2));
  if (result.status !== 'success') {
    process.exitCode = 1;
  }
}

main();
