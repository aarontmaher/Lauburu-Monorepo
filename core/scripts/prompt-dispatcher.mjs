#!/usr/bin/env node
/**
 * prompt-dispatcher — local, opt-in bridge from approved prompt
 * queue rows to idle tmux lanes.
 *
 * Default is dry-run. Real tmux send-keys requires --dispatch.
 * This script never builds, deploys, uploads, or releases.
 */

import { spawnSync } from 'node:child_process';
import { appendFileSync, copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import {
  allKnownLanesInactive,
  buildDispatchEvent,
  classifyLocalBridgeSnapshot,
  generatePromptQueueFromActionLedger,
  markPromptDispatched,
  selectNextPrompt,
} from './prompt-dispatcher-helpers.mjs';

const REPO_ROOT = resolve(new URL('..', import.meta.url).pathname);
const DEFAULT_QUEUE = join(REPO_ROOT, 'data', 'prompt-dispatcher', 'queue.json');
const DEFAULT_LOG = join(REPO_ROOT, 'data', 'prompt-dispatcher', 'dispatch-log.jsonl');
const DEFAULT_LEDGER = join(REPO_ROOT, 'data', 'action-ledger', 'pending_actions.json');
const DEFAULT_LANES = join(REPO_ROOT, 'data', 'agent-status', 'lanes', 'coder_lanes.json');
const DEFAULT_TARGETS = Object.freeze({
  agent: 'codex-lauburu:2.0',
  codex: 'codex-lauburu:0.0',
  claude: 'lauburu:0.0',
});

function parseArgs(argv) {
  const out = {
    queuePath: DEFAULT_QUEUE,
    lanesPath: DEFAULT_LANES,
    logPath: DEFAULT_LOG,
    ledgerPath: DEFAULT_LEDGER,
    generateQueue: true,
    once: false,
    watch: false,
    intervalSec: 10,
    dispatch: false,
    bridgeSnapshot: false,
    target: { ...DEFAULT_TARGETS },
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = argv[i + 1];
    if (arg === '--queue' && next) { out.queuePath = resolve(next); i += 1; }
    else if (arg === '--ledger' && next) { out.ledgerPath = resolve(next); i += 1; }
    else if (arg === '--lanes' && next) { out.lanesPath = resolve(next); i += 1; }
    else if (arg === '--log' && next) { out.logPath = resolve(next); i += 1; }
    else if (arg === '--generate-queue') out.generateQueue = true;
    else if (arg === '--no-generate-queue') out.generateQueue = false;
    else if (arg === '--codex-target' && next) { out.target.codex = next; i += 1; }
    else if (arg === '--claude-target' && next) { out.target.claude = next; i += 1; }
    else if (arg === '--agent-target' && next) { out.target.agent = next; i += 1; }
    else if (arg === '--once') out.once = true;
    else if (arg === '--watch') out.watch = true;
    else if (arg === '--interval' && next) { out.intervalSec = Math.max(5, Math.min(600, Number(next) || 10)); i += 1; }
    else if (arg === '--dispatch') out.dispatch = true;
    else if (arg === '--bridge-snapshot') out.bridgeSnapshot = true;
    else if (arg === '--help' || arg === '-h') {
      console.log(`Usage: node scripts/prompt-dispatcher.mjs [flags]

  --once                    run one selection pass and exit
  --watch                   loop until stopped
  --interval <seconds>      loop interval for --watch (5..600, default 10)
  --dispatch                actually paste prompt into tmux (default: dry-run)
  --bridge-snapshot         after real dispatch, run npm run bridge:snapshot
  --generate-queue          regenerate queue from action ledger before selecting (default)
  --no-generate-queue       use existing queue file only
  --queue <path>            prompt queue JSON (default data/prompt-dispatcher/queue.json)
  --ledger <path>           action ledger JSON
  --lanes <path>            coder_lanes JSON (default data/agent-status/lanes/coder_lanes.json)
  --log <path>              JSONL audit log path
  --agent-target <tmux>     default codex-lauburu:2.0
  --codex-target <tmux>     default codex-lauburu:0.0
  --claude-target <tmux>    default lauburu:0.0

Queue shape:
  { "prompts": [
    {
      "id": "p0-safe-tooling",
      "targetLane": "codex",
      "priority": "P1",
      "status": "queued",
      "approved": true,
      "publicSafe": true,
      "promptText": "Public-safe repo-only prompt..."
    }
  ] }`);
      process.exit(0);
    }
  }
  return out;
}

function readJson(path, fallback) {
  if (!existsSync(path)) return fallback;
  return JSON.parse(readFileSync(path, 'utf8'));
}

function readLanes(path) {
  const raw = readJson(path, { lanes: [] });
  return Array.isArray(raw?.lanes) ? raw.lanes : [];
}

function readLaneSnapshot(path) {
  return readJson(path, null);
}

function ensureParent(path) {
  mkdirSync(dirname(path), { recursive: true });
}

function writeJson(path, value) {
  ensureParent(path);
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function archiveQueue(path) {
  if (!existsSync(path)) return null;
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  const archiveDir = join(dirname(path), 'archive');
  mkdirSync(archiveDir, { recursive: true });
  const dest = join(archiveDir, `${ts}-${basename(path)}`);
  copyFileSync(path, dest);
  return dest;
}

function writeLog(path, event) {
  ensureParent(path);
  appendFileSync(path, `${JSON.stringify(event)}\n`);
}

function tmuxSendPrompt(target, promptText) {
  const setBuffer = spawnSync('tmux', ['set-buffer', promptText], { encoding: 'utf8' });
  if (setBuffer.status !== 0) {
    throw new Error(`tmux set-buffer failed: ${(setBuffer.stderr || '').trim()}`);
  }
  const paste = spawnSync('tmux', ['paste-buffer', '-t', target], { encoding: 'utf8' });
  if (paste.status !== 0) {
    throw new Error(`tmux paste-buffer failed for ${target}: ${(paste.stderr || '').trim()}`);
  }
  const enter = spawnSync('tmux', ['send-keys', '-t', target, 'Enter'], { encoding: 'utf8' });
  if (enter.status !== 0) {
    throw new Error(`tmux send-keys failed for ${target}: ${(enter.stderr || '').trim()}`);
  }
}

function runBridgeSnapshot() {
  return spawnSync('npm', ['run', 'bridge:snapshot'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function runOnce(args) {
  const observedAt = new Date().toISOString();
  let queueInput = readJson(args.queuePath, { prompts: [] });
  const laneSnapshot = readLaneSnapshot(args.lanesPath);
  const bridgeFreshness = classifyLocalBridgeSnapshot(laneSnapshot);
  if (args.generateQueue) {
    const ledger = readJson(args.ledgerPath, { pendingActions: [] });
    const nextQueue = generatePromptQueueFromActionLedger(ledger, queueInput, { generatedAt: observedAt });
    const changed = JSON.stringify(nextQueue.prompts ?? []) !== JSON.stringify(queueInput.prompts ?? []);
    if (changed) {
      archiveQueue(args.queuePath);
      writeJson(args.queuePath, nextQueue);
    }
    queueInput = changed ? nextQueue : queueInput;
  }
  const lanes = Array.isArray(laneSnapshot?.lanes) ? laneSnapshot.lanes : [];
  const { selected, decisions } = selectNextPrompt({ queueInput, lanes });

  const dryRun = !args.dispatch;
  let dispatched = false;
  let reason = !bridgeFreshness.fresh
    ? `${bridgeFreshness.reason}; ${bridgeFreshness.recovery}`
    : selected
    ? dryRun
      ? `dry-run selected ${selected.id} for ${selected.targetLane}`
      : `dispatching ${selected.id} to ${selected.targetLane}`
    : 'no eligible prompt';

  if (bridgeFreshness.fresh && !selected && decisions.length > 0) {
    reason = `no eligible prompt: ${decisions.map((d) => `${d.item.id}=${d.reason}`).join('; ')}`;
  }
  if (bridgeFreshness.fresh && !selected && allKnownLanesInactive(lanes)) {
    const priority = queueInput?.topPriority?.title ? ` Top priority: ${queueInput.topPriority.title}.` : '';
    reason += `; all known lanes idle/blocked.${priority} Next action: review manual gates or add an approved public-safe queue item.`;
  }

  if (selected && args.dispatch && bridgeFreshness.fresh) {
    const target = args.target[selected.targetLane];
    if (!target) throw new Error(`No tmux target configured for lane ${selected.targetLane}`);
    tmuxSendPrompt(target, selected.promptText);
    dispatched = true;
    queueInput = markPromptDispatched(queueInput, selected, observedAt);
    writeJson(args.queuePath, queueInput);
    if (args.bridgeSnapshot) {
      const snap = runBridgeSnapshot();
      if (snap.status !== 0) {
        reason += `; bridge:snapshot failed exit=${snap.status}`;
      } else {
        reason += '; bridge:snapshot ok';
      }
    }
  }

  const event = buildDispatchEvent({ selected: bridgeFreshness.fresh ? selected : null, dryRun, dispatched, reason, observedAt });
  writeLog(args.logPath, event);
  console.log(JSON.stringify(event, null, 2));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.watch && args.once) {
    throw new Error('--watch and --once are mutually exclusive.');
  }

  if (!args.watch) {
    runOnce(args);
    return;
  }

  console.log(`prompt-dispatcher: every ${args.intervalSec}s · dispatch=${args.dispatch ? 'on' : 'dry-run'} · bridgeSnapshot=${args.bridgeSnapshot ? 'on' : 'off'}`);
  let stop = false;
  process.on('SIGINT', () => { stop = true; console.log('\nprompt-dispatcher: stopping...'); });
  while (!stop) {
    try {
      runOnce(args);
    } catch (err) {
      const event = buildDispatchEvent({
        selected: null,
        dryRun: !args.dispatch,
        dispatched: false,
        reason: `error: ${err instanceof Error ? err.message : String(err)}`,
        observedAt: new Date().toISOString(),
      });
      writeLog(args.logPath, event);
      console.error(JSON.stringify(event, null, 2));
    }
    if (stop) break;
    await new Promise((resolveSleep) => setTimeout(resolveSleep, args.intervalSec * 1000));
  }
}

main().catch((err) => {
  console.error(`prompt-dispatcher fatal: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
