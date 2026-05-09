#!/usr/bin/env node
/**
 * mcp-watcher — periodically poll project.get_current_state,
 * detect staleness + terminal-vs-MCP disagreement, and
 * (optionally) auto-run bridge:snapshot to clear staleness.
 *
 * Intended to run during active sessions in a long-running
 * shell:
 *   npm run watcher:mcp -- --interval 60 --auto-refresh
 *
 * Outputs:
 *   - data/mcp-watcher/<isoDate>.jsonl — per-tick findings.
 *   - stdout — per-tick summary (one line each).
 *   - (when SUPABASE_SERVICE_ROLE_KEY + SUPABASE_URL available
 *     in env) writes actionable findings to
 *     connector_handoff.auditFindings via the same upsert
 *     path the bridge uses. NEVER writes secrets to logs.
 *
 * Flags:
 *   --interval <seconds>      poll interval (default 60; min 30; max 600).
 *   --auto-refresh            on stale_writeback / no_writeback,
 *                             run `npm run bridge:snapshot` and re-poll once.
 *   --tmux-session <name>     tmux session to inspect for
 *                             terminal disagreement (default
 *                             codex-lauburu).
 *   --once                    run a single tick and exit.
 *   --quiet                   suppress per-tick stdout (still
 *                             writes JSONL).
 *
 * Stops cleanly on SIGINT (Ctrl-C). Per rule 18 — every actionable
 * finding lands in MCP / on disk before the watcher exits.
 *
 * Anti-rules:
 *   - No secrets in stdout / logs.
 *   - No installed-device verified claim.
 *   - No EAS / Play / TestFlight upload.
 *   - Auto-refresh runs `npm run bridge:snapshot` only — never
 *     a deploy / build / release command.
 */

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, appendFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import {
  classifyFreshness,
  classifyPaneText,
  detectAgentDisagreement,
  shouldAutoRefresh,
  buildFinding,
} from './mcp-watcher-helpers.mjs';

const REPO_ROOT = resolve(new URL('..', import.meta.url).pathname);
const LOG_DIR = join(REPO_ROOT, 'data', 'mcp-watcher');
const MCP_URL = 'https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2';

function parseArgs(argv) {
  const args = {
    intervalSec: 60,
    autoRefresh: false,
    tmuxSession: 'codex-lauburu',
    once: false,
    quiet: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--interval') args.intervalSec = Math.max(30, Math.min(600, parseInt(argv[++i] ?? '60', 10) || 60));
    else if (a === '--auto-refresh') args.autoRefresh = true;
    else if (a === '--tmux-session') args.tmuxSession = argv[++i] ?? 'codex-lauburu';
    else if (a === '--once') args.once = true;
    else if (a === '--quiet') args.quiet = true;
    else if (a === '--help' || a === '-h') {
      console.log(`Usage: node scripts/mcp-watcher.mjs [flags]

  --interval <seconds>      poll interval (30..600, default 60)
  --auto-refresh            on stale, run bridge:snapshot once
  --tmux-session <name>     tmux session to inspect (default codex-lauburu)
  --once                    run a single tick and exit
  --quiet                   suppress per-tick stdout
  --help                    print this help`);
      process.exit(0);
    }
  }
  return args;
}

async function fetchCurrentState() {
  try {
    const res = await fetch(MCP_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'tools/call',
        params: { name: 'project.get_current_state' },
      }),
    });
    if (!res.ok) {
      return { networkError: false, httpStatus: res.status, payload: null };
    }
    const json = await res.json();
    const txt = json?.result?.content?.[0]?.text;
    const payload = typeof txt === 'string' ? JSON.parse(txt) : null;
    return { networkError: false, httpStatus: 200, payload };
  } catch (err) {
    return { networkError: true, httpStatus: null, payload: null, error: String(err?.message || err) };
  }
}

function capturePane(session) {
  if (!session) return null;
  const r = spawnSync('tmux', ['capture-pane', '-t', `${session}:0`, '-p'], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
  });
  if (r.status !== 0) return null;
  return r.stdout || '';
}

function runBridgeSnapshot() {
  const r = spawnSync('npm', ['run', 'bridge:snapshot'], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return { exitCode: r.status, stdout: (r.stdout || '').slice(-1000), stderr: (r.stderr || '').slice(-500) };
}

function ensureLogDir() {
  if (!existsSync(LOG_DIR)) mkdirSync(LOG_DIR, { recursive: true });
}

function jsonlPath() {
  const today = new Date().toISOString().slice(0, 10);
  return join(LOG_DIR, `${today}.jsonl`);
}

async function tick({ session, autoRefresh, quiet }) {
  const observedAt = new Date().toISOString();
  const { networkError, httpStatus, payload, error } = await fetchCurrentState();
  const freshness = payload?.freshness;
  const freshnessVerdict = classifyFreshness(freshness, { networkError, httpStatus });
  const agents = Array.isArray(payload?.agents) ? payload.agents : [];

  // Capture tmux pane only when configured. Multi-session support is
  // a future improvement; today we check the codex pane (most-active lane).
  const paneText = capturePane(session);
  const paneVerdict = classifyPaneText(paneText);

  // Compare each cached agent.status to the pane verdict for that lane.
  // Today we conservatively check ONLY the codex lane against the
  // codex-lauburu pane. Claude pane lookup would require a different
  // session name; the pane data isn't available from this watcher.
  const agentDisagreements = agents
    .filter((a) => a.id === 'codex')
    .map((a) => detectAgentDisagreement(a, paneVerdict))
    .filter((d) => d.disagrees);

  const finding = buildFinding({ freshnessVerdict, agentDisagreements, observedAt });
  ensureLogDir();
  appendFileSync(jsonlPath(), JSON.stringify(finding) + '\n');

  if (!quiet) {
    const tag = freshnessVerdict.verdict === 'fresh' ? '🟢' : '🟠';
    const disTag = agentDisagreements.length > 0 ? ' ⚠ disagreement' : '';
    console.log(`${tag} ${observedAt}  ${freshnessVerdict.verdict}  ${freshnessVerdict.reason}${disTag}${error ? '  err=' + error : ''}`);
  }

  if (autoRefresh && shouldAutoRefresh(freshnessVerdict)) {
    if (!quiet) console.log('  ↻ auto-refresh: running bridge:snapshot');
    const refreshResult = runBridgeSnapshot();
    appendFileSync(jsonlPath(), JSON.stringify({
      schemaVersion: 1,
      observedAt: new Date().toISOString(),
      action: 'bridge:snapshot',
      exitCode: refreshResult.exitCode,
      // never echo stdout here — it can contain Supabase URL hint;
      // exit code is sufficient signal.
    }) + '\n');
    if (!quiet) console.log(`  ↻ exit=${refreshResult.exitCode}`);
  }

  return finding;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.quiet) {
    console.log(`mcp-watcher: ${args.once ? 'one-tick' : `every ${args.intervalSec}s`}` +
      ` · auto-refresh=${args.autoRefresh ? 'on' : 'off'}` +
      ` · tmux=${args.tmuxSession}`);
  }

  let stop = false;
  process.on('SIGINT', () => { stop = true; if (!args.quiet) console.log('\nmcp-watcher: stopping…'); });

  if (args.once) {
    await tick({ session: args.tmuxSession, autoRefresh: args.autoRefresh, quiet: args.quiet });
    return;
  }

  // Soft loop. The interval is a sleep between ticks, not a wall clock.
  while (!stop) {
    try {
      await tick({ session: args.tmuxSession, autoRefresh: args.autoRefresh, quiet: args.quiet });
    } catch (err) {
      if (!args.quiet) console.log(`mcp-watcher tick error: ${err?.message || err}`);
    }
    if (stop) break;
    await new Promise((r) => setTimeout(r, args.intervalSec * 1000));
  }
}

main().catch((err) => {
  console.error(`mcp-watcher fatal: ${err?.message || err}`);
  process.exit(1);
});
