#!/usr/bin/env node
/**
 * iphone-mirroring-audit — collect macOS iPhone-Mirroring
 * screenshots from a watch dir (default ~/Desktop), move them
 * into artifacts/app-audit/iphone-mirroring/<isoTimestamp>/, and
 * write a manifest.json describing the build / device / screens.
 *
 * Companion: scripts/audit-screenshots.mjs (simulator/emulator
 * driver). Both target artifacts/app-audit/ but different
 * sub-paths.
 *
 * macOS only. Requires macOS 15+ for iPhone Mirroring; no
 * iCloud / dev cert / USB needed (that's the whole point).
 *
 * Usage:
 *   npm run audit:iphone-mirroring
 *
 * Flags:
 *   --watch-dir <path>     Source directory to scan (default ~/Desktop)
 *   --window <minutes>     How far back to scan for new PNGs (default 10)
 *   --labels a,b,c         Comma-separated screen labels (1:1 with the
 *                          captured files in mtime order). When provided
 *                          enables --non-interactive automatically.
 *   --ios-build <s>        Manifest field iosBuildNumber
 *   --app-version <s>      Manifest field appVersion
 *   --device <s>           Manifest field device
 *   --ios-version <s>      Manifest field iosVersion
 *   --macos-version <s>    Manifest field macosVersion
 *   --notes <s>            Manifest field notes
 *   --zip                  Also produce <ts>.zip for handoff
 *   --auto-launch          Open iPhone Mirroring before scanning (opt-in)
 *   --non-interactive      Skip prompts; manifest fields default to null when not flagged
 *   --dry-run              Don't move files / write manifest; print what would happen
 */

import { execFileSync, spawnSync } from 'node:child_process';
import { mkdirSync, readdirSync, statSync, renameSync, writeFileSync, existsSync, readFileSync } from 'node:fs';
import { dirname, join, relative, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { platform as osPlatform } from 'node:os';
import { createInterface } from 'node:readline/promises';

import {
  buildIphoneMirroringManifest,
  indexPrefix,
  isFilenameSuspicious,
  labelToScreenSlug,
  parseIphoneMirroringArgs,
  resolveAuditWatchDir,
} from './audit-screenshots-helpers.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = join(__dirname, '..');

function detectMacosVersion() {
  if (osPlatform() !== 'darwin') return null;
  try {
    return execFileSync('sw_vers', ['-productVersion'], { encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

function readAppVersionFromAppJson() {
  try {
    const raw = JSON.parse(readFileSync(join(ROOT, 'apps', 'mobile', 'app.json'), 'utf8'));
    const expo = raw?.expo ?? {};
    return {
      appVersion: typeof expo.version === 'string' ? expo.version : null,
      iosBuildNumber: expo.ios?.buildNumber == null ? null : String(expo.ios.buildNumber),
    };
  } catch {
    return { appVersion: null, iosBuildNumber: null };
  }
}

function listRecentPngs(watchDir, windowMs) {
  const cutoff = Date.now() - windowMs;
  let names;
  try {
    names = readdirSync(watchDir);
  } catch (err) {
    throw new Error(`Cannot read watch directory ${watchDir}: ${err.message}`);
  }
  const matches = [];
  for (const name of names) {
    if (!name.toLowerCase().endsWith('.png')) continue;
    const abs = join(watchDir, name);
    let stat;
    try { stat = statSync(abs); } catch { continue; }
    if (!stat.isFile()) continue;
    if (stat.mtimeMs < cutoff) continue;
    matches.push({ name, abs, mtimeMs: stat.mtimeMs });
  }
  matches.sort((a, b) => a.mtimeMs - b.mtimeMs);
  return matches;
}

function ensureDir(p) {
  mkdirSync(p, { recursive: true });
}

async function promptManifestFields(rl, args, defaults) {
  if (args.nonInteractive) {
    return {
      iosBuildNumber: args.iosBuild ?? defaults.iosBuildNumber ?? null,
      appVersion: args.appVersion ?? defaults.appVersion ?? null,
      device: args.device ?? null,
      iosVersion: args.iosVersion ?? null,
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
  return {
    iosBuildNumber: args.iosBuild ?? await ask('iOS buildNumber', defaults.iosBuildNumber ?? ''),
    appVersion: args.appVersion ?? await ask('appVersion', defaults.appVersion ?? ''),
    device: args.device ?? await ask('Device (e.g. iPhone 15 Pro)', ''),
    iosVersion: args.iosVersion ?? await ask('iOS version (e.g. 18.2)', ''),
    macosVersion: args.macosVersion ?? await ask('macOS version', defaults.macosVersion ?? ''),
    notes: args.notes ?? await ask('Notes (optional)', ''),
  };
}

async function promptLabels(rl, files) {
  const labels = [];
  console.log(`\nProvide a short label per captured file (e.g. "admin-dev-top", "health-sources").`);
  console.log(`Press Enter to skip a file (it stays in the watch dir, NOT moved).`);
  for (let i = 0; i < files.length; i += 1) {
    const ans = await rl.question(`  [${indexPrefix(i)}] ${files[i].name} → label: `);
    labels.push(ans.trim());
  }
  return labels;
}

function moveFileSafe(srcAbs, destAbs, dryRun) {
  if (dryRun) return;
  ensureDir(dirname(destAbs));
  renameSync(srcAbs, destAbs);
}

function makeZip(folderAbs) {
  // macOS bundles `zip` by default; we shell out to it.
  const parent = dirname(folderAbs);
  const name = basename(folderAbs);
  const zipPath = join(parent, `${name}.zip`);
  const result = spawnSync('zip', ['-r', '-q', zipPath, name], { cwd: parent });
  if (result.status !== 0) {
    return { ok: false, path: zipPath, stderr: result.stderr?.toString('utf8').trim() ?? '' };
  }
  return { ok: existsSync(zipPath), path: zipPath, stderr: '' };
}

function autoLaunchIphoneMirroring() {
  try {
    const result = spawnSync('open', ['-a', 'iPhone Mirroring'], { encoding: 'utf8' });
    if (result.status !== 0) {
      const stderr = result.stderr?.trim();
      throw new Error(stderr || `open exited ${result.status}`);
    }
    console.log('  auto-launch: opened iPhone Mirroring');
  } catch (err) {
    console.error(`--auto-launch failed to open iPhone Mirroring: ${err instanceof Error ? err.message : String(err)}`);
    console.error('Confirm macOS 15+ and that /Applications/iPhone Mirroring.app is installed.');
    process.exit(2);
  }
}

async function main() {
  if (osPlatform() !== 'darwin') {
    console.error('iphone-mirroring-audit requires macOS (iPhone Mirroring is a macOS 15+ feature). Detected:', osPlatform());
    process.exit(1);
  }

  const args = parseIphoneMirroringArgs(process.argv.slice(2));
  if (args.labels) args.nonInteractive = true;

  let watchDir;
  try {
    watchDir = resolveAuditWatchDir(args.watchDir);
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(2);
  }

  const windowMs = args.windowMinutes * 60_000;
  if (args.autoLaunch) autoLaunchIphoneMirroring();
  const recent = listRecentPngs(watchDir, windowMs);

  console.log(`iPhone-Mirroring audit run`);
  console.log(`  watch dir:    ${watchDir}`);
  console.log(`  window:       last ${args.windowMinutes} min`);
  console.log(`  found PNGs:   ${recent.length}`);
  if (recent.length === 0) {
    console.error(`No .png files modified in the last ${args.windowMinutes} minutes under ${watchDir}.`);
    console.error(`Capture screenshots first (Cmd-Shift-4 → window pick on the iPhone Mirroring app), then re-run.`);
    process.exit(1);
  }

  // Suspicious filename guard. Aaron saves screenshots himself,
  // so suspicious names indicate a screenshot of admin tokens or
  // similar. We refuse to ingest them and surface the list.
  const suspicious = recent.filter((f) => isFilenameSuspicious(f.name));
  if (suspicious.length > 0) {
    console.error('\nRefusing to ingest filenames that look like they might capture secrets:');
    for (const f of suspicious) console.error(`  - ${f.name}`);
    console.error('\nRename or delete those files (or crop the screenshot) and re-run.');
    process.exit(2);
  }

  const ts = new Date().toISOString();
  const tsSafe = ts.replace(/[:.]/g, '-');
  const destDir = join(ROOT, 'artifacts', 'app-audit', 'iphone-mirroring', tsSafe);
  if (!args.dryRun) ensureDir(destDir);

  const defaults = {
    macosVersion: detectMacosVersion(),
    ...readAppVersionFromAppJson(),
  };

  const rl = args.nonInteractive ? null : createInterface({ input: process.stdin, output: process.stdout });
  let labels;
  if (args.labels) {
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

  const manifest = buildIphoneMirroringManifest({
    iosBuildNumber: fields.iosBuildNumber,
    appVersion: fields.appVersion,
    device: fields.device,
    iosVersion: fields.iosVersion,
    macosVersion: fields.macosVersion,
    capturedAt: ts,
    screens: renamed,
    notes: fields.notes,
  });

  const manifestPath = join(destDir, 'manifest.json');
  if (!args.dryRun) writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`\n${args.dryRun ? '[dry-run] would write' : '✓ wrote'} ${relative(ROOT, manifestPath)}`);

  if (args.zip && !args.dryRun) {
    const zipResult = makeZip(destDir);
    if (zipResult.ok) console.log(`✓ zipped ${relative(ROOT, zipResult.path)}`);
    else console.error(`✗ zip failed: ${zipResult.stderr}`);
  }

  console.log(`\nDone. ${renamed.length}/${recent.length} files captured.`);
  if (renamed.length === 0) console.log('No labels supplied for any file — nothing was moved. Re-run with labels.');
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack ?? err.message : String(err));
  process.exit(1);
});
