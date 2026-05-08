#!/usr/bin/env node
/**
 * audit-agent-bundle — single Agent-ready bundle aggregator.
 *
 * Picks the most recent capture across every audit tier
 * (simulator/emulator screenshots + iPhone Mirroring + scrcpy
 * Android + Maestro), copies them under a unified
 * `artifacts/agent-bundles/<isoTimestamp>/` folder, fetches a
 * snapshot of the current MCP state (project.get_current_state +
 * project.get_work_status), and writes a top-level index
 * manifest. Aaron / Codex / Claude hand the resulting folder
 * (or zip) to Agent in one paste.
 *
 * Source artifact dirs (already produced by other audit:* scripts):
 *   artifacts/app-audit/<isoTimestamp>/                  — simulator
 *   artifacts/app-audit/iphone-mirroring/<isoTimestamp>/ — iPhone Mirroring
 *   artifacts/app-audit/android-scrcpy/<isoTimestamp>/   — scrcpy
 *   artifacts/app-audit/maestro/<isoTimestamp>/          — Maestro
 *
 * Output:
 *   artifacts/agent-bundles/<isoTimestamp>/
 *     simulator/   (copy of latest simulator capture, or omitted)
 *     iphone-mirroring/
 *     android-scrcpy/
 *     maestro/
 *     mcp-snapshot.json                  — project.get_current_state + work_status digest
 *     manifest.json                      — index referencing every sub-bundle
 *
 * Flags:
 *   --include <tiers>      Comma-separated subset (simulator, iphone, scrcpy, maestro)
 *   --exclude <tiers>      Comma-separated tiers to drop
 *   --mcp-url <url>        Override the MCP base URL (defaults to lauburu-mcp-preview.lauburu-aaron.workers.dev)
 *   --dry-run              Print what would happen without copying / writing files
 *
 * No EAS build. No production release. No autoshare — Aaron is
 * always the courier.
 */

import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  buildAgentBundleManifest,
  parseAgentBundleArgs,
} from './audit-screenshots-helpers.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..');

const DEFAULT_MCP_URL = 'https://lauburu-mcp-preview.lauburu-aaron.workers.dev/mcp/v2';
const TIER_DIRS = [
  { tier: 'simulator',        relPath: 'app-audit',                   matchTimestamp: true },
  { tier: 'iphone-mirroring', relPath: 'app-audit/iphone-mirroring',  matchTimestamp: true },
  { tier: 'android-scrcpy',   relPath: 'app-audit/android-scrcpy',    matchTimestamp: true },
  { tier: 'maestro',          relPath: 'app-audit/maestro',           matchTimestamp: true },
];

const args = parseAgentBundleArgs(process.argv.slice(2));
const includeFilter = args.include ? new Set(args.include.split(',').map((t) => t.trim())) : null;
const excludeFilter = args.exclude ? new Set(args.exclude.split(',').map((t) => t.trim())) : new Set();

function shortHead() {
  try { return execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(); }
  catch { return 'unknown'; }
}
function branchName() {
  try { return execFileSync('git', ['branch', '--show-current'], { cwd: ROOT, encoding: 'utf8' }).trim() || 'main'; }
  catch { return 'main'; }
}
function readAppConfig() {
  try {
    const raw = JSON.parse(readFileSync(join(ROOT, 'apps', 'mobile', 'app.json'), 'utf8'));
    const expo = raw?.expo ?? {};
    return {
      appVersion: expo.version ?? null,
      iosBuildNumber: expo.ios?.buildNumber == null ? null : String(expo.ios.buildNumber),
      androidVersionCode: Number.isInteger(expo.android?.versionCode) ? expo.android.versionCode : null,
      iosBundleIdentifier: expo.ios?.bundleIdentifier ?? null,
      androidPackage: expo.android?.package ?? null,
    };
  } catch { return { appVersion: null, iosBuildNumber: null, androidVersionCode: null, iosBundleIdentifier: null, androidPackage: null }; }
}

function findLatestTimestampDir(absRoot) {
  if (!existsSync(absRoot)) return null;
  let entries;
  try { entries = readdirSync(absRoot, { withFileTypes: true }); }
  catch { return null; }
  const candidates = entries
    .filter((e) => e.isDirectory())
    .map((e) => {
      const abs = join(absRoot, e.name);
      let mtime = 0;
      try { mtime = statSync(abs).mtimeMs; } catch { /* ignore */ }
      return { name: e.name, abs, mtimeMs: mtime };
    })
    .filter((c) => c.mtimeMs > 0);
  candidates.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates[0] ?? null;
}

function readManifestSummary(absDir) {
  const manifestPath = join(absDir, 'manifest.json');
  if (!existsSync(manifestPath)) return { manifestRel: null, capturedAt: null, screenCount: 0 };
  try {
    const raw = JSON.parse(readFileSync(manifestPath, 'utf8'));
    const screenCount = Array.isArray(raw?.screens)
      ? raw.screens.length
      : Array.isArray(raw?.captured)
        ? raw.captured.length
        : 0;
    return {
      manifestRel: 'manifest.json',
      capturedAt: typeof raw?.capturedAt === 'string' ? raw.capturedAt : null,
      screenCount,
    };
  } catch {
    return { manifestRel: null, capturedAt: null, screenCount: 0 };
  }
}

async function fetchMcpSnapshot(mcpUrl) {
  if (typeof fetch !== 'function') return null;
  const post = async (name) => {
    try {
      const res = await fetch(mcpUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', accept: 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: {} } }),
      });
      if (!res.ok) return null;
      const env = await res.json();
      const text = env?.result?.content?.[0]?.text;
      if (typeof text !== 'string') return null;
      return JSON.parse(text);
    } catch { return null; }
  };
  const [current, work] = await Promise.all([
    post('project.get_current_state'),
    post('project.get_work_status'),
  ]);
  return { current, work };
}

async function main() {
  const ts = new Date().toISOString();
  const tsSafe = ts.replace(/[:.]/g, '-');
  const outDirAbs = join(ROOT, 'artifacts', 'agent-bundles', tsSafe);
  if (!args.dryRun) mkdirSync(outDirAbs, { recursive: true });

  console.log(`Agent-ready bundle aggregator`);
  console.log(`  output: ${relative(ROOT, outDirAbs)}`);
  console.log(`  repo:   ${branchName()}@${shortHead()}`);

  const sources = [];
  for (const tier of TIER_DIRS) {
    if (includeFilter && !includeFilter.has(tier.tier)) continue;
    if (excludeFilter.has(tier.tier)) continue;
    const absRoot = join(ROOT, 'artifacts', tier.relPath);
    const latest = findLatestTimestampDir(absRoot);
    if (!latest) {
      console.log(`  - ${tier.tier}: no captures`);
      continue;
    }
    const summary = readManifestSummary(latest.abs);
    const tierOutAbs = join(outDirAbs, tier.tier);
    if (!args.dryRun) {
      mkdirSync(tierOutAbs, { recursive: true });
      cpSync(latest.abs, tierOutAbs, { recursive: true, force: true });
    }
    const sourceEntry = {
      tier: tier.tier,
      path: relative(ROOT, tierOutAbs),
      manifest: summary.manifestRel,
      capturedAt: summary.capturedAt,
      screenCount: summary.screenCount,
    };
    sources.push(sourceEntry);
    console.log(`  ${args.dryRun ? '[dry-run] would copy' : '✓ copied'} ${relative(ROOT, latest.abs)} → ${relative(ROOT, tierOutAbs)} (${summary.screenCount} screens)`);
  }

  const mcpUrl = args.mcpUrl ?? DEFAULT_MCP_URL;
  const mcp = await fetchMcpSnapshot(mcpUrl);
  let mcpSummary = { generatedAt: null, ageMs: null, staleReason: null, priority: null, nextAction: null };
  if (mcp?.current) {
    const fresh = mcp.current?.freshness ?? {};
    mcpSummary = {
      generatedAt: typeof mcp.current?.generatedAt === 'string' ? mcp.current.generatedAt : null,
      ageMs: typeof fresh?.ageMs === 'number' ? fresh.ageMs : null,
      staleReason: typeof fresh?.staleReason === 'string' ? fresh.staleReason : null,
      priority: typeof mcp.current?.currentPriority === 'string' ? mcp.current.currentPriority : null,
      nextAction: typeof mcp.current?.nextAction === 'string' ? mcp.current.nextAction : null,
    };
  } else if (mcp?.work) {
    mcpSummary.priority = typeof mcp.work?.currentPriority === 'string' ? mcp.work.currentPriority : null;
    mcpSummary.nextAction = typeof mcp.work?.nextAction === 'string' ? mcp.work.nextAction : null;
  }

  if (!args.dryRun) {
    writeFileSync(join(outDirAbs, 'mcp-snapshot.json'), `${JSON.stringify({
      mcpUrl,
      fetchedAt: new Date().toISOString(),
      currentState: mcp?.current ?? null,
      workStatus: mcp?.work ?? null,
    }, null, 2)}\n`);
  }

  const manifest = buildAgentBundleManifest({
    generatedAt: ts,
    repo: { branch: branchName(), shortHead: shortHead() },
    build: readAppConfig(),
    mcp: mcpSummary,
    sources,
    notes: '',
  });
  if (!args.dryRun) writeFileSync(join(outDirAbs, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);

  console.log(`\n${args.dryRun ? '[dry-run] would write' : '✓ wrote'} ${relative(ROOT, join(outDirAbs, 'manifest.json'))}`);
  console.log(`  sources: ${sources.length}`);
  console.log(`  MCP: ${mcpSummary.staleReason ?? 'unknown'}${mcpSummary.ageMs != null ? ` · ${Math.round(mcpSummary.ageMs / 1000)}s` : ''}`);
}

main().catch((err) => { console.error(err.stack ?? err.message ?? String(err)); process.exit(1); });
