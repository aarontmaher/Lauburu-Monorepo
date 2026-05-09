#!/usr/bin/env node
/**
 * audit-android-scrcpy — collect Mac-side screenshots of an Android
 * device mirrored via scrcpy.
 *
 * Aaron pairs the Android device, runs `scrcpy` (so the device's
 * screen mirrors into a Mac window), takes screenshots with
 * Cmd-Shift-4 → Space → click the scrcpy window, then runs this
 * script. The script collects new PNGs from a watch dir
 * (default ~/Desktop), refuses suspicious filenames, prompts for
 * labels + manifest fields, and writes the bundle to
 * artifacts/app-audit/android-scrcpy/<isoTimestamp>/.
 *
 * Companion to scripts/iphone-mirroring-audit.mjs (same idea on
 * iOS via macOS 15+ iPhone Mirroring). Reuses the same
 * audit-screenshots-helpers.mjs primitives.
 *
 * macOS-only because that's where Aaron's audit chain lives.
 *
 * Usage:
 *   npm run audit:android-scrcpy
 *
 * Flags:
 *   --watch-dir <path>            Source directory (default ~/Desktop)
 *   --window <minutes>            How far back to scan for new PNGs (default 10)
 *   --labels a,b,c                Comma-separated screen labels (1:1 with files in mtime order)
 *   --label-preset <name>         Known label set. Current: v21-health-connect
 *   --audit-gate <name>           Manifest audit gate label (e.g. release_gate)
 *   --verification-status <name>  Manifest status: captured_only/pass/partial/fail/blocked
 *   --android-version-code <int>  Manifest field
 *   --app-version <s>             Manifest field
 *   --device <s>                  Manifest field
 *   --android-version <s>         Manifest field (e.g. "Android 15")
 *   --macos-version <s>           Manifest field
 *   --notes <s>                   Manifest field
 *   --zip                         Also produce <ts>.zip for handoff
 *   --non-interactive             Skip prompts; manifest fields default to null when not flagged
 *   --dry-run                     Don't move files / write manifest; print what would happen
 */

import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, readdirSync, statSync, renameSync, writeFileSync, existsSync, readFileSync } from 'node:fs';
import { dirname, join, relative, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir, platform as osPlatform } from 'node:os';
import { createInterface } from 'node:readline/promises';

import {
  buildScrcpyAndroidManifest,
  indexPrefix,
  isFilenameSuspicious,
  labelToScreenSlug,
  parseScrcpyAndroidArgs,
  SCRCPY_ANDROID_LABEL_PRESETS,
} from './audit-screenshots-helpers.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..');

function detectMacosVersion() {
  if (osPlatform() !== 'darwin') return null;
  try { return execFileSync('sw_vers', ['-productVersion'], { encoding: 'utf8' }).trim(); } catch { return null; }
}

function readAppConfig() {
  try {
    const raw = JSON.parse(readFileSync(join(ROOT, 'apps', 'mobile', 'app.json'), 'utf8'));
    const expo = raw?.expo ?? {};
    return {
      appVersion: typeof expo.version === 'string' ? expo.version : null,
      androidVersionCode: Number.isInteger(expo.android?.versionCode) ? expo.android.versionCode : null,
    };
  } catch { return { appVersion: null, androidVersionCode: null }; }
}

function listRecentPngs(watchDir, windowMs) {
  const cutoff = Date.now() - windowMs;
  let names;
  try { names = readdirSync(watchDir); }
  catch (err) { throw new Error(`Cannot read watch directory ${watchDir}: ${err.message}`); }
  const matches = [];
  for (const name of names) {
    if (!name.toLowerCase().endsWith('.png')) continue;
    const abs = join(watchDir, name);
    let stat;
    try { stat = statSync(abs); } catch { continue; }
    if (!stat.isFile() || stat.mtimeMs < cutoff) continue;
    matches.push({ name, abs, mtimeMs: stat.mtimeMs });
  }
  matches.sort((a, b) => a.mtimeMs - b.mtimeMs);
  return matches;
}

function adbAvailable() { try { execFileSync('adb', ['version'], { stdio: 'ignore' }); return true; } catch { return false; } }
function scrcpyAvailable() { try { execFileSync('scrcpy', ['--version'], { stdio: 'ignore' }); return true; } catch { return false; } }

async function promptManifestFields(rl, args, defaults) {
  if (args.nonInteractive) {
    return {
      androidVersionCode: args.androidVersionCode ?? defaults.androidVersionCode ?? null,
      appVersion: args.appVersion ?? defaults.appVersion ?? null,
      device: args.device ?? null,
      androidVersion: args.androidVersion ?? null,
      macosVersion: args.macosVersion ?? defaults.macosVersion ?? null,
      notes: args.notes ?? null,
    };
  }
  const ask = async (label, fallback) => {
    if (fallback != null && fallback !== '') {
      const a = await rl.question(`${label} [${fallback}]: `);
      return a.trim() === '' ? fallback : a.trim();
    }
    const a = await rl.question(`${label}: `);
    return a.trim() === '' ? null : a.trim();
  };
  const askInt = async (label, fallback) => {
    const a = await ask(label, fallback);
    if (a == null) return null;
    const n = Number(a);
    return Number.isInteger(n) ? n : null;
  };
  return {
    androidVersionCode: args.androidVersionCode ?? await askInt('Android versionCode', defaults.androidVersionCode ?? ''),
    appVersion: args.appVersion ?? await ask('appVersion', defaults.appVersion ?? ''),
    device: args.device ?? await ask('Device (e.g. Pixel 8a)', ''),
    androidVersion: args.androidVersion ?? await ask('Android version (e.g. 15)', ''),
    macosVersion: args.macosVersion ?? await ask('macOS version', defaults.macosVersion ?? ''),
    notes: args.notes ?? await ask('Notes (optional)', ''),
  };
}

async function promptLabels(rl, files) {
  console.log(`\nProvide a short label per captured file (e.g. "admin-dev-top", "health-sources").`);
  console.log(`Press Enter to skip a file (it stays in the watch dir, NOT moved).`);
  const labels = [];
  for (let i = 0; i < files.length; i += 1) {
    const ans = await rl.question(`  [${indexPrefix(i)}] ${files[i].name} → label: `);
    labels.push(ans.trim());
  }
  return labels;
}

function moveFileSafe(src, dest, dryRun) {
  if (dryRun) return;
  mkdirSync(dirname(dest), { recursive: true });
  renameSync(src, dest);
}

function makeZip(folderAbs) {
  const parent = dirname(folderAbs);
  const name = basename(folderAbs);
  const zipPath = join(parent, `${name}.zip`);
  const result = spawnSync('zip', ['-r', '-q', zipPath, name], { cwd: parent });
  if (result.status !== 0) return { ok: false, path: zipPath, stderr: result.stderr?.toString('utf8').trim() ?? '' };
  return { ok: existsSync(zipPath), path: zipPath, stderr: '' };
}

async function main() {
  if (osPlatform() !== 'darwin') {
    console.error('audit-android-scrcpy expects macOS (Aaron\'s audit chain). Detected:', osPlatform());
    process.exit(1);
  }
  const args = parseScrcpyAndroidArgs(process.argv.slice(2));
  if (args.labels || args.labelPreset) args.nonInteractive = true;

  const watchDir = args.watchDir
    ? (args.watchDir.startsWith('~') ? join(homedir(), args.watchDir.slice(1)) : args.watchDir)
    : join(homedir(), 'Desktop');
  const windowMs = args.windowMinutes * 60_000;
  const recent = listRecentPngs(watchDir, windowMs);

  console.log(`scrcpy Android audit run`);
  console.log(`  watch dir:  ${watchDir}`);
  console.log(`  window:     last ${args.windowMinutes} min`);
  console.log(`  found PNGs: ${recent.length}`);
  console.log(`  scrcpy:     ${scrcpyAvailable() ? 'installed' : 'NOT installed (mirror manually or `brew install scrcpy`)'}`);
  console.log(`  adb:        ${adbAvailable() ? 'installed' : 'NOT installed (install Android Platform Tools)'}`);
  if (recent.length === 0) {
    console.error(`No .png files modified in the last ${args.windowMinutes} minutes under ${watchDir}.`);
    console.error(`Mirror the device first (run 'scrcpy' in another terminal), capture screenshots with`);
    console.error(`Cmd-Shift-4 → Space → click the scrcpy window, then re-run.`);
    process.exit(1);
  }

  const suspicious = recent.filter((f) => isFilenameSuspicious(f.name));
  if (suspicious.length > 0) {
    console.error('\nRefusing to ingest filenames that look like they might capture secrets:');
    for (const f of suspicious) console.error(`  - ${f.name}`);
    console.error('\nRename or delete those files (or crop the screenshot) and re-run.');
    process.exit(2);
  }

  const ts = new Date().toISOString();
  const tsSafe = ts.replace(/[:.]/g, '-');
  const destDir = join(ROOT, 'artifacts', 'app-audit', 'android-scrcpy', tsSafe);
  if (!args.dryRun) mkdirSync(destDir, { recursive: true });

  const defaults = { macosVersion: detectMacosVersion(), ...readAppConfig() };
  const rl = args.nonInteractive ? null : createInterface({ input: process.stdin, output: process.stdout });

  let labels;
  if (args.labels && args.labelPreset) {
    console.error('--labels and --label-preset are mutually exclusive.');
    process.exit(2);
  }

  if (args.labelPreset) {
    labels = SCRCPY_ANDROID_LABEL_PRESETS[args.labelPreset];
    if (!labels) {
      console.error(`Unknown --label-preset ${JSON.stringify(args.labelPreset)}.`);
      console.error(`Known presets: ${Object.keys(SCRCPY_ANDROID_LABEL_PRESETS).join(', ')}`);
      process.exit(2);
    }
    if (labels.length !== recent.length) {
      console.error(`Preset ${args.labelPreset} expects ${labels.length} captures but found ${recent.length}.`);
      console.error('For v21 Health Connect, capture exactly the 10 screenshots from docs/V21_HEALTH_CONNECT_SCREENSHOT_QA.md, or use --labels manually.');
      process.exit(2);
    }
  } else if (args.labels) {
    labels = args.labels.split(',').map((s) => s.trim());
    if (labels.length !== recent.length) {
      console.error(`--labels count (${labels.length}) must match captured files (${recent.length}).`);
      process.exit(2);
    }
  } else if (rl) {
    labels = await promptLabels(rl, recent);
  } else {
    labels = recent.map((_, i) => `screen-${indexPrefix(i)}`);
  }

  const renamed = [];
  for (let i = 0; i < recent.length; i += 1) {
    const file = recent[i];
    const label = labels[i] ?? '';
    if (!label) {
      console.log(`  - ${file.name}: skipped (no label)`);
      continue;
    }
    const slug = labelToScreenSlug(label);
    const newName = `${indexPrefix(i)}-${slug}.png`;
    const destAbs = join(destDir, newName);
    moveFileSafe(file.abs, destAbs, args.dryRun);
    renamed.push({ filename: newName, screen: slug, notes: '' });
    console.log(`  ${args.dryRun ? '[dry-run] would move' : '✓ moved'} ${file.name} → ${relative(ROOT, destAbs)}`);
  }

  const fields = rl ? await promptManifestFields(rl, args, defaults) : await promptManifestFields(null, { ...args, nonInteractive: true }, defaults);
  rl?.close();

  const manifest = buildScrcpyAndroidManifest({
    auditGate: args.auditGate,
    verificationStatus: args.verificationStatus,
    androidVersionCode: fields.androidVersionCode,
    appVersion: fields.appVersion,
    device: fields.device,
    androidVersion: fields.androidVersion,
    macosVersion: fields.macosVersion,
    capturedAt: ts,
    screens: renamed,
    notes: fields.notes,
  });
  const manifestPath = join(destDir, 'manifest.json');
  if (!args.dryRun) writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`\n${args.dryRun ? '[dry-run] would write' : '✓ wrote'} ${relative(ROOT, manifestPath)}`);

  if (args.zip && !args.dryRun) {
    const zip = makeZip(destDir);
    if (zip.ok) console.log(`✓ zipped ${relative(ROOT, zip.path)}`);
    else console.error(`✗ zip failed: ${zip.stderr}`);
  }

  console.log(`\nDone. ${renamed.length}/${recent.length} files captured.`);
  if (renamed.length === 0) console.log('No labels supplied for any file — nothing was moved. Re-run with labels.');
}

main().catch((err) => { console.error(err.stack ?? err.message ?? String(err)); process.exit(1); });
