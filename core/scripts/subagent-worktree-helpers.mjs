/**
 * Pure and system helpers for Subagent Task Dispatcher & Worktree Governor.
 *
 * Provides:
 * - Isolated Git worktree creation, listing, and cleanup.
 * - Pre-flight pytest gate execution and verification.
 * - Harvesting successful PR / commit diffs into continuous distillation memory.
 * - Task dispatch orchestration connecting background subagent sessions to worktrees.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, isAbsolute, resolve } from 'node:path';

function isObject(val) {
  return val !== null && typeof val === 'object' && !Array.isArray(val);
}

function text(val) {
  return typeof val === 'string' ? val.trim() : '';
}

function nowIso() {
  return new Date().toISOString();
}

function ensureParent(filePath) {
  mkdirSync(dirname(filePath), { recursive: true });
}

function readJson(filePath, fallback) {
  if (!existsSync(filePath)) return fallback;
  try {
    return JSON.parse(readFileSync(filePath, 'utf8'));
  } catch (_e) {
    return fallback;
  }
}

function writeJson(filePath, data) {
  ensureParent(filePath);
  writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

/**
 * Creates an isolated git worktree for a subagent session task.
 */
export function createIsolatedWorktree({
  repoRoot,
  subagentId = 'subagent',
  branchName,
  baseBranch = 'HEAD',
  worktreeDir,
} = {}) {
  if (!repoRoot || !existsSync(repoRoot)) {
    throw new Error(`Invalid repoRoot provided: ${repoRoot}`);
  }

  const safeSubagentId = text(subagentId).replace(/[^a-zA-Z0-9_-]/g, '_') || 'subagent';
  const targetBranch = branchName || `subagent/${safeSubagentId}-${Date.now()}`;
  
  const defaultDir = join(repoRoot, '.worktrees', targetBranch.replace(/\//g, '-'));
  const targetWorktreePath = worktreeDir ? (isAbsolute(worktreeDir) ? worktreeDir : resolve(repoRoot, worktreeDir)) : defaultDir;

  ensureParent(targetWorktreePath);

  // Check if target directory exists and is non-empty
  if (existsSync(targetWorktreePath)) {
    const check = spawnSync('git', ['worktree', 'remove', '--force', targetWorktreePath], {
      cwd: repoRoot,
      encoding: 'utf8',
    });
    if (existsSync(targetWorktreePath)) {
      rmSync(targetWorktreePath, { recursive: true, force: true });
    }
  }

  // Create branch and worktree
  const gitRes = spawnSync('git', ['worktree', 'add', '-b', targetBranch, targetWorktreePath, baseBranch], {
    cwd: repoRoot,
    encoding: 'utf8',
  });

  if (gitRes.status !== 0) {
    // If branch already exists, try adding without -b
    const retryRes = spawnSync('git', ['worktree', 'add', targetWorktreePath, targetBranch], {
      cwd: repoRoot,
      encoding: 'utf8',
    });
    if (retryRes.status !== 0) {
      throw new Error(`Failed to create worktree at ${targetWorktreePath}: ${gitRes.stderr || retryRes.stderr}`);
    }
  }

  return {
    subagentId: safeSubagentId,
    branchName: targetBranch,
    worktreePath: targetWorktreePath,
    createdAt: nowIso(),
  };
}

/**
 * Removes an isolated git worktree.
 */
export function removeIsolatedWorktree({ repoRoot, worktreePath, force = true } = {}) {
  if (!repoRoot || !existsSync(repoRoot)) {
    throw new Error(`Invalid repoRoot: ${repoRoot}`);
  }
  if (!worktreePath) return { success: false, reason: 'missing worktreePath' };

  const args = ['worktree', 'remove'];
  if (force) args.push('--force');
  args.push(worktreePath);

  const res = spawnSync('git', args, { cwd: repoRoot, encoding: 'utf8' });
  if (res.status !== 0 && existsSync(worktreePath)) {
    rmSync(worktreePath, { recursive: true, force: true });
  }

  // Prune worktree metadata
  spawnSync('git', ['worktree', 'prune'], { cwd: repoRoot, encoding: 'utf8' });

  return {
    success: true,
    worktreePath,
    removedAt: nowIso(),
  };
}

/**
 * Lists active git worktrees.
 */
export function listIsolatedWorktrees({ repoRoot } = {}) {
  if (!repoRoot || !existsSync(repoRoot)) {
    return [];
  }
  const res = spawnSync('git', ['worktree', 'list', '--porcelain'], { cwd: repoRoot, encoding: 'utf8' });
  if (res.status !== 0 || !res.stdout) return [];

  const worktrees = [];
  let current = {};
  for (const line of res.stdout.split('\n')) {
    if (line.startsWith('worktree ')) {
      if (current.worktree) worktrees.push(current);
      current = { worktree: line.slice(9).trim() };
    } else if (line.startsWith('HEAD ')) {
      current.head = line.slice(5).trim();
    } else if (line.startsWith('branch ')) {
      current.branch = line.slice(7).trim();
    } else if (line === 'detached') {
      current.detached = true;
    }
  }
  if (current.worktree) worktrees.push(current);
  return worktrees;
}

/**
 * Runs pre-flight pytest gates in the specified directory/worktree.
 */
export function runPreFlightPytest({ cwd, testPath, extraArgs = [] } = {}) {
  if (!cwd || !existsSync(cwd)) {
    return {
      passed: false,
      exitCode: -1,
      stdout: '',
      stderr: `Directory does not exist: ${cwd}`,
      reason: 'directory_not_found',
    };
  }

  const pyArgs = [];
  if (testPath) {
    pyArgs.push(testPath);
  }
  if (Array.isArray(extraArgs)) {
    pyArgs.push(...extraArgs);
  }

  // Use system pytest executable
  const pytestRes = spawnSync('pytest', pyArgs, {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PYTHONPATH: cwd },
  });

  const passed = pytestRes.status === 0;
  const stdout = pytestRes.stdout || '';
  const stderr = pytestRes.stderr || '';

  // Parse total tests collected/passed if possible
  let summary = 'No tests collected or executed.';
  const summaryMatch = stdout.match(/([0-9]+\s+passed|no tests ran|[0-9]+\s+failed)/i);
  if (summaryMatch) {
    summary = summaryMatch[0];
  }

  return {
    passed,
    exitCode: pytestRes.status ?? -1,
    summary,
    stdout,
    stderr,
    executedAt: nowIso(),
  };
}

/**
 * Harvests PR / commit diff from a worktree.
 */
export function harvestWorktreeDiff({
  worktreePath,
  baseRef = 'HEAD~1',
  targetRef = 'HEAD',
} = {}) {
  if (!worktreePath || !existsSync(worktreePath)) {
    throw new Error(`Invalid worktreePath: ${worktreePath}`);
  }

  // Get changed files
  const nameStatusRes = spawnSync('git', ['diff', '--name-status', baseRef, targetRef], {
    cwd: worktreePath,
    encoding: 'utf8',
  });

  // Get actual unified diff
  const diffRes = spawnSync('git', ['diff', baseRef, targetRef], {
    cwd: worktreePath,
    encoding: 'utf8',
  });

  // Get commit log summary
  const logRes = spawnSync('git', ['log', '-1', '--pretty=format:%H%n%an%n%ae%n%s%n%b', targetRef], {
    cwd: worktreePath,
    encoding: 'utf8',
  });

  const changedFiles = [];
  if (nameStatusRes.status === 0 && nameStatusRes.stdout) {
    for (const line of nameStatusRes.stdout.trim().split('\n')) {
      if (!line) continue;
      const [status, ...fileParts] = line.split(/\s+/);
      changedFiles.push({ status, file: fileParts.join(' ') });
    }
  }

  const logLines = (logRes.stdout || '').split('\n');
  const commitHash = logLines[0] || targetRef;
  const authorName = logLines[1] || '';
  const authorEmail = logLines[2] || '';
  const commitSubject = logLines[3] || '';
  const commitBody = logLines.slice(4).join('\n').trim();

  return {
    commitHash,
    author: `${authorName} <${authorEmail}>`.trim(),
    subject: commitSubject,
    body: commitBody,
    changedFiles,
    diffText: diffRes.stdout || '',
    harvestedAt: nowIso(),
  };
}

/**
 * Distills harvested PR diff into continuous distillation memory structure.
 */
export function distillHarvestIntoMemory({
  harvest,
  memoryPath,
  subagentId = 'subagent',
  taskTitle = '',
  confidence = 'provisional',
} = {}) {
  if (!harvest || !isObject(harvest)) {
    throw new Error('Invalid harvest object');
  }

  const destPath = memoryPath || resolve(process.cwd(), 'data', 'distillation-memory', 'memory_store.json');
  const store = readJson(destPath, {
    schemaVersion: 1,
    description: 'Continuous distillation memory for harvested subagent PR diffs and state updates',
    updatedAt: nowIso(),
    distillations: [],
  });

  const distillationEntry = {
    id: `distill-${harvest.commitHash ? harvest.commitHash.slice(0, 8) : Date.now()}`,
    kind: 'subagent_pr_harvest',
    subagentId,
    taskTitle: taskTitle || harvest.subject || 'Subagent Worktree Task',
    commitHash: harvest.commitHash,
    author: harvest.author,
    subject: harvest.subject,
    body: harvest.body,
    changedFiles: harvest.changedFiles,
    diffSummary: harvest.diffText ? harvest.diffText.slice(0, 1500) + (harvest.diffText.length > 1500 ? '\n...[truncated]' : '') : '',
    harvestedAt: harvest.harvestedAt || nowIso(),
    confidence,
    status: 'active',
  };

  store.updatedAt = nowIso();
  store.distillations.unshift(distillationEntry);

  writeJson(destPath, store);

  return distillationEntry;
}

/**
 * Orchestrates dispatch of subagent background session task:
 * 1. Setup worktree
 * 2. Run optional taskSetup callback (e.g. to create/modify files or commits)
 * 3. Run pre-flight pytest / gate checks
 * 4. On success, harvest diff and distill into continuous memory
 */
export function dispatchSubagentTaskAndGovern({
  repoRoot,
  subagentId = 'subagent-01',
  branchName,
  baseBranch = 'HEAD',
  testPath,
  pytestArgs = [],
  memoryPath,
  taskSetupFn,
  cleanupWorktreeOnSuccess = false,
} = {}) {
  const result = {
    subagentId,
    status: 'failed',
    worktree: null,
    preflight: null,
    harvest: null,
    memoryEntry: null,
    reason: '',
  };

  // Step 1: Create worktree
  let worktree;
  try {
    worktree = createIsolatedWorktree({
      repoRoot,
      subagentId,
      branchName,
      baseBranch,
    });
    result.worktree = worktree;
  } catch (err) {
    result.reason = `Worktree creation failed: ${err.message}`;
    return result;
  }

  // Step 2: Run optional taskSetup callback in worktree
  if (typeof taskSetupFn === 'function') {
    try {
      taskSetupFn(worktree.worktreePath);
    } catch (err) {
      result.reason = `Task setup in worktree failed: ${err.message}`;
      return result;
    }
  }

  // Step 3: Execute pre-flight pytest gates
  const preflight = runPreFlightPytest({
    cwd: worktree.worktreePath,
    testPath,
    extraArgs: pytestArgs,
  });
  result.preflight = preflight;

  if (!preflight.passed) {
    result.reason = `Pre-flight pytest gate failed with code ${preflight.exitCode}: ${preflight.summary}`;
    return result;
  }

  // Step 4: Harvest diffs and distill memory
  try {
    const harvest = harvestWorktreeDiff({
      worktreePath: worktree.worktreePath,
      baseRef: baseBranch.includes('..') ? baseBranch : `${baseBranch}`,
      targetRef: 'HEAD',
    });
    result.harvest = harvest;

    const memoryEntry = distillHarvestIntoMemory({
      harvest,
      memoryPath,
      subagentId,
      taskTitle: `Task on branch ${worktree.branchName}`,
    });
    result.memoryEntry = memoryEntry;
    result.status = 'success';
    result.reason = 'Pre-flight pytest gates passed and PR diff distilled into continuous memory.';

    if (cleanupWorktreeOnSuccess) {
      removeIsolatedWorktree({ repoRoot, worktreePath: worktree.worktreePath });
    }
  } catch (err) {
    result.reason = `Harvest / distillation failed: ${err.message}`;
  }

  return result;
}
