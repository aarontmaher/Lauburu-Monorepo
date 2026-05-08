#!/usr/bin/env node
/**
 * audit-screenshots — capture per-screen PNGs + manifest from a
 * booted iOS Simulator or Android emulator.
 *
 * Aaron drives the navigation; the script handles platform
 * detection, build identity, screenshot capture, and the
 * manifest. Reuses the same `xcrun simctl io booted screenshot`
 * tool path as scripts/mobile-simulator-audit.mjs (which is the
 * project's existing canonical screenshot helper).
 *
 * No new app dependencies. No EAS build. No real Apple Health /
 * Health Connect required — the simulator gracefully renders
 * whatever the app shows when permissions are not granted.
 *
 * Outputs:
 *   artifacts/app-audit/<isoTimestamp>/
 *     home.png
 *     health.png
 *     manage-sources.png
 *     readiness.png
 *     journal.png
 *     train.png
 *     map.png
 *     settings.png
 *     admin-dev.png
 *     manifest.json
 *
 * Run:
 *   npm run audit:screenshots
 *
 * Flags:
 *   --platform ios|android   Force platform (default: auto-detect)
 *   --skip <ids>             Comma-separated screen ids to skip
 *   --non-interactive        Take whatever is currently on screen
 *                            for the FIRST listed screen and exit;
 *                            useful for CI smoke without prompts.
 *   --device <id>            Force device id (overrides detection).
 */

import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createInterface } from 'node:readline/promises';

import {
  AUDIT_SCREENS,
  buildManifest,
  parseArgs,
} from './audit-screenshots-helpers.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..');

const args = parseArgs(process.argv.slice(2));

function shortHead() {
  try {
    return execFileSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim();
  } catch {
    return 'unknown';
  }
}

function branchName() {
  try {
    return execFileSync('git', ['branch', '--show-current'], { cwd: ROOT, encoding: 'utf8' }).trim() || 'main';
  } catch {
    return 'main';
  }
}

function readAppConfig() {
  try {
    const raw = JSON.parse(readFileSync(join(ROOT, 'apps', 'mobile', 'app.json'), 'utf8'));
    const app = raw?.expo ?? {};
    return {
      appVersion: app.version ?? null,
      iosBuildNumber: app.ios?.buildNumber == null ? null : String(app.ios.buildNumber),
      androidVersionCode: Number.isInteger(app.android?.versionCode) ? app.android.versionCode : null,
      iosBundleIdentifier: app.ios?.bundleIdentifier ?? null,
      androidPackage: app.android?.package ?? null,
    };
  } catch {
    return {
      appVersion: null,
      iosBuildNumber: null,
      androidVersionCode: null,
      iosBundleIdentifier: null,
      androidPackage: null,
    };
  }
}

function detectIosSimulator(forceDevice) {
  try {
    if (forceDevice) {
      return { kind: 'ios', deviceId: forceDevice, name: forceDevice };
    }
    const out = execFileSync('xcrun', ['simctl', 'list', 'devices', 'booted', '--json'], { encoding: 'utf8' });
    const devices = JSON.parse(out)?.devices ?? {};
    for (const runtimeDevices of Object.values(devices)) {
      const booted = (runtimeDevices ?? []).find((d) => d?.state === 'Booted');
      if (booted) {
        return { kind: 'ios', deviceId: booted.udid, name: booted.name ?? booted.udid };
      }
    }
  } catch {
    // xcrun not present (non-Mac) or no booted simulator.
  }
  return null;
}

function detectAndroidEmulator(forceDevice) {
  try {
    const out = execFileSync('adb', ['devices'], { encoding: 'utf8' });
    const lines = out.trim().split('\n').slice(1).map((l) => l.trim()).filter(Boolean);
    if (forceDevice) {
      const found = lines.find((l) => l.startsWith(forceDevice + '\t'));
      if (!found) return null;
      return { kind: 'android', deviceId: forceDevice, name: forceDevice };
    }
    const dev = lines.find((l) => /\bdevice$/.test(l));
    if (dev) {
      const id = dev.split(/\s+/)[0];
      return { kind: 'android', deviceId: id, name: id };
    }
  } catch {
    // adb not installed.
  }
  return null;
}

function captureIos(deviceId, outPath) {
  const result = spawnSync('xcrun', ['simctl', 'io', deviceId, 'screenshot', outPath], { encoding: 'utf8' });
  return { ok: result.status === 0 && existsSync(outPath), stderr: (result.stderr ?? '').trim() };
}

function captureAndroid(deviceId, outPath) {
  // adb exec-out screencap -p emits a binary PNG to stdout. Capture to a Buffer and write it.
  const result = spawnSync('adb', ['-s', deviceId, 'exec-out', 'screencap', '-p'], { encoding: 'buffer' });
  if (result.status !== 0) return { ok: false, stderr: result.stderr?.toString('utf8').trim() ?? '' };
  try {
    writeFileSync(outPath, result.stdout);
    return { ok: existsSync(outPath), stderr: '' };
  } catch (err) {
    return { ok: false, stderr: err instanceof Error ? err.message : String(err) };
  }
}

async function main() {
  const requested = args.platform;
  const forceDevice = args.device ?? null;

  let target = null;
  if (!requested || requested === 'ios') {
    target = detectIosSimulator(forceDevice);
  }
  if (!target && (!requested || requested === 'android')) {
    target = detectAndroidEmulator(forceDevice);
  }
  if (!target) {
    console.error(
      'No booted iOS Simulator or Android emulator detected.\n\n' +
      'Boot one and re-run, e.g.:\n' +
      '  iOS:     open -a Simulator   (then in Xcode pick a device → Boot)\n' +
      '  Android: emulator -list-avds && emulator -avd <name>\n',
    );
    process.exit(1);
  }

  const buildIdentity = readAppConfig();
  const skip = new Set((args.skip ?? '').split(',').map((s) => s.trim()).filter(Boolean));
  const screens = AUDIT_SCREENS.filter((s) => !skip.has(s.id));

  const ts = new Date().toISOString();
  const tsSafe = ts.replace(/[:.]/g, '-');
  const outDirAbs = join(ROOT, 'artifacts', 'app-audit', tsSafe);
  mkdirSync(outDirAbs, { recursive: true });
  const outDirRel = relative(ROOT, outDirAbs);

  console.log(`Audit screenshot run starting`);
  console.log(`  platform: ${target.kind} (${target.name})`);
  console.log(`  build:    appVersion ${buildIdentity.appVersion ?? '—'} · android v${buildIdentity.androidVersionCode ?? '—'} · iOS Build ${buildIdentity.iosBuildNumber ?? '—'}`);
  console.log(`  repo:     ${branchName()}@${shortHead()}`);
  console.log(`  output:   ${outDirRel}`);
  console.log('');

  const captured = [];
  const skipped = [];

  if (args.nonInteractive) {
    // Capture only the first listed screen with whatever is currently on-screen.
    const first = screens[0];
    if (!first) {
      console.error('No screens to capture (all skipped).');
      process.exit(1);
    }
    const file = join(outDirAbs, `${first.id}.png`);
    const cap = target.kind === 'ios' ? captureIos(target.deviceId, file) : captureAndroid(target.deviceId, file);
    if (!cap.ok) {
      console.error(`✗ capture failed for ${first.id}: ${cap.stderr || 'unknown error'}`);
      process.exit(2);
    }
    captured.push({ id: first.id, label: first.label, route: first.route, file: `${first.id}.png`, capturedAt: new Date().toISOString() });
    console.log(`✓ ${first.id} → ${relative(ROOT, file)}`);
  } else {
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    try {
      for (const screen of screens) {
        const answer = await rl.question(
          `\nNavigate to ${screen.label} (route: ${screen.route}).\n  Press Enter to capture, type 's' + Enter to skip, 'q' + Enter to quit: `,
        );
        const key = answer.trim().toLowerCase();
        if (key === 'q') break;
        if (key === 's') {
          skipped.push({ id: screen.id, reason: 'user-skipped' });
          continue;
        }
        const file = join(outDirAbs, `${screen.id}.png`);
        const cap = target.kind === 'ios' ? captureIos(target.deviceId, file) : captureAndroid(target.deviceId, file);
        if (!cap.ok) {
          console.error(`  ✗ capture failed: ${cap.stderr || 'unknown error'}`);
          skipped.push({ id: screen.id, reason: `capture-failed: ${cap.stderr || 'unknown'}` });
          continue;
        }
        captured.push({ id: screen.id, label: screen.label, route: screen.route, file: `${screen.id}.png`, capturedAt: new Date().toISOString() });
        console.log(`  ✓ ${screen.id} → ${relative(ROOT, file)}`);
      }
    } finally {
      rl.close();
    }
  }

  const manifest = buildManifest({
    platform: target.kind,
    device: { id: target.deviceId, name: target.name },
    build: buildIdentity,
    repo: { branch: branchName(), shortHead: shortHead() },
    capturedAt: ts,
    screens: captured,
    skipped,
  });
  writeFileSync(join(outDirAbs, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);

  console.log(`\nDone. Captured ${captured.length}/${screens.length} screen(s).`);
  console.log(`  manifest: ${relative(ROOT, join(outDirAbs, 'manifest.json'))}`);
  if (skipped.length > 0) {
    console.log(`  skipped:  ${skipped.map((s) => `${s.id} (${s.reason})`).join(', ')}`);
  }
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack ?? err.message : String(err));
  process.exit(1);
});
