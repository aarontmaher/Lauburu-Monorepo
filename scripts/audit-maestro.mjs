#!/usr/bin/env node
/**
 * audit-maestro — wrapper around `maestro test apps/mobile/audit-flows/`.
 *
 * Runs the full Maestro flow suite (or a single flow when --flow is
 * passed) against the booted simulator/emulator/device, collects
 * `.maestro/test-output/<run>/screenshot-*.png` outputs into
 * artifacts/app-audit/maestro/<isoTimestamp>/, and writes a
 * manifest.json identical in shape to the simulator-driver output.
 *
 * Fail-soft when Maestro is not installed — prints the brew install
 * command and exits with code 1 cleanly. Anti-rule: never crashes
 * the user's terminal because of a missing dep.
 *
 * Flags:
 *   --flow <name>          Run a single flow file (e.g. 02-health)
 *   --suite <default|ios>  Run the default root suite or iOS simulator suite
 *   --platform <ios|android>  Force a target platform; default auto
 *   --device <id>          Forward to maestro test --device <id>
 *   --dry-run              Print the maestro command without running
 *   --keep-tmp             Don't delete the maestro test-output dir
 */

import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { dirname, join, relative, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

import {
  buildMaestroAgentAuditManifest,
  buildMaestroAgentHandoff,
  buildMaestroManifest,
  parseMaestroArgs,
} from './audit-screenshots-helpers.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..');
const FLOW_DIR = join(ROOT, 'apps', 'mobile', 'audit-flows');

const args = parseMaestroArgs(process.argv.slice(2));

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

function slugPart(value, fallback) {
  const text = value == null ? fallback : String(value);
  const slug = text
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
  return slug || fallback;
}

function maestroAvailable() {
  try {
    const r = spawnSync('maestro', ['--version'], { encoding: 'utf8' });
    return r.status === 0;
  } catch { return false; }
}

function listFlowFiles() {
  const dir = flowDirForSuite();
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((n) => n.endsWith('.yml') && n !== 'README.md')
    .sort();
}

function flowDirForSuite() {
  if (args.suite === 'ios') return join(FLOW_DIR, 'ios');
  return FLOW_DIR;
}

function flowAbsPath(flow) {
  if (flow.includes('/') || flow.includes('\\')) return join(FLOW_DIR, flow);
  return join(flowDirForSuite(), flow);
}

function findScreenshots(searchDir) {
  if (!existsSync(searchDir)) return [];
  const stack = [searchDir];
  const out = [];
  while (stack.length > 0) {
    const current = stack.pop();
    let entries;
    try { entries = readdirSync(current, { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      const abs = join(current, e.name);
      if (e.isDirectory()) { stack.push(abs); continue; }
      if (!e.isFile()) continue;
      if (!e.name.toLowerCase().endsWith('.png')) continue;
      let mtime = 0;
      try { mtime = statSync(abs).mtimeMs; } catch { /* ignore */ }
      out.push({ abs, name: e.name, mtimeMs: mtime });
    }
  }
  out.sort((a, b) => a.mtimeMs - b.mtimeMs);
  return out;
}

async function main() {
  if (!maestroAvailable()) {
    console.error('Maestro is not installed. Install via:');
    console.error('  brew tap mobile-dev-inc/tap');
    console.error('  brew install maestro');
    console.error('Then re-run npm run audit:maestro.');
    process.exit(1);
  }

  const flows = args.flow
    ? [args.flow.endsWith('.yml') ? args.flow : `${args.flow}.yml`]
    : listFlowFiles();
  if (flows.length === 0) {
    console.error(`No flows found under ${flowDirForSuite()}.`);
    process.exit(1);
  }

  const ts = new Date().toISOString();
  const tsSafe = ts.replace(/[:.]/g, '-');
  const buildIdentity = readAppConfig();
  const platformSlug = args.platform ?? 'unknown-platform';
  const buildSlug = args.platform === 'ios'
    ? `ios-build-${slugPart(buildIdentity.iosBuildNumber, 'unknown')}`
    : args.platform === 'android'
      ? `android-v${slugPart(buildIdentity.androidVersionCode, 'unknown')}`
      : `app-${slugPart(buildIdentity.appVersion, 'unknown')}`;
  const outDirAbs = join(ROOT, 'artifacts', 'app-audit', 'maestro', platformSlug, buildSlug, tsSafe);
  mkdirSync(outDirAbs, { recursive: true });

  console.log(`Maestro audit run`);
  console.log(`  suite:    ${args.suite ?? 'default'}`);
  console.log(`  flows:    ${flows.length}`);
  console.log(`  output:   ${relative(ROOT, outDirAbs)}`);
  console.log(`  build:    appVersion ${buildIdentity.appVersion ?? '—'} · android v${buildIdentity.androidVersionCode ?? '—'} · iOS Build ${buildIdentity.iosBuildNumber ?? '—'}`);
  console.log(`  repo:     ${branchName()}@${shortHead()}`);

  const captured = [];
  const failed = [];
  const tmpRoot = join(homedir(), '.maestro', 'tests');
  const beforeSet = new Set(findScreenshots(tmpRoot).map((f) => f.abs));

  for (const flow of flows) {
    const abs = flowAbsPath(flow);
    if (!existsSync(abs)) {
      console.error(`  ✗ ${flow}: file not found`);
      failed.push({ flow, reason: 'file-not-found' });
      continue;
    }
    const cmd = ['test', abs];
    if (args.device) cmd.push('--device', args.device);
    if (args.dryRun) {
      console.log(`  [dry-run] maestro ${cmd.join(' ')}`);
      continue;
    }
    const result = spawnSync('maestro', cmd, { encoding: 'utf8' });
    if (result.status !== 0) {
      console.error(`  ✗ ${flow}: maestro exit ${result.status}`);
      const stderr = (result.stderr ?? '').trim().slice(-400);
      if (stderr) console.error(`     stderr: ${stderr}`);
      failed.push({ flow, reason: `maestro-exit-${result.status}` });
      continue;
    }
    console.log(`  ✓ ${flow}`);
    const after = findScreenshots(tmpRoot).filter((f) => !beforeSet.has(f.abs));
    for (const f of after) {
      const flowSlug = basename(flow, '.yml');
      const newName = `${flowSlug}-${captured.filter((c) => c.flow === flowSlug).length + 1}.png`;
      const destAbs = join(outDirAbs, newName);
      try {
        renameSync(f.abs, destAbs);
        beforeSet.add(f.abs);
        captured.push({
          flow: flowSlug,
          file: newName,
          capturedAt: new Date().toISOString(),
        });
      } catch (err) {
        console.error(`     ✗ failed to move screenshot ${f.name}: ${err.message}`);
      }
    }
  }

  const manifest = buildMaestroManifest({
    platform: args.platform ?? 'unknown',
    auditGate: 'simulator_audit',
    device: { id: args.device ?? null, name: args.device ?? null },
    build: buildIdentity,
    repo: { branch: branchName(), shortHead: shortHead() },
    capturedAt: ts,
    flows: flows.map((f) => basename(f, '.yml')),
    captured,
    failed,
  });
  writeFileSync(join(outDirAbs, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
  const agentManifest = buildMaestroAgentAuditManifest({
    manifest,
    bundlePath: relative(ROOT, outDirAbs),
  });
  writeFileSync(join(outDirAbs, 'agent-audit-manifest.json'), `${JSON.stringify(agentManifest, null, 2)}\n`);
  const agentHandoff = buildMaestroAgentHandoff({
    manifest,
    agentManifest,
    bundlePath: relative(ROOT, outDirAbs),
  });
  writeFileSync(join(outDirAbs, 'agent-handoff.md'), agentHandoff);
  console.log(`\nDone. Captured ${captured.length} screenshot(s); ${failed.length} flow(s) failed.`);
  console.log(`  manifest: ${relative(ROOT, join(outDirAbs, 'manifest.json'))}`);
  console.log(`  agent manifest: ${relative(ROOT, join(outDirAbs, 'agent-audit-manifest.json'))}`);
  console.log(`  agent handoff: ${relative(ROOT, join(outDirAbs, 'agent-handoff.md'))}`);
  console.log('  gate: simulator/emulator capture only; cannot clear installed-device release gates');

  if (!args.keepTmp) {
    try { rmSync(join(homedir(), '.maestro', 'tests'), { recursive: true, force: true }); } catch { /* ignore */ }
  }
}

main().catch((err) => { console.error(err.stack ?? err.message ?? String(err)); process.exit(1); });
